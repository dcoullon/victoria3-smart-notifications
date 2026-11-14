"""Generate the Research Queue probe build (research_queue/).

The engine has no "move a tech to position N" command (Technology exposes
only AddToQueue, AddToQueueWithUnlocks, RemoveFromQueue, Research,
ResearchWithUnlocks; see reference/data_types). So moving tech X from
position x to final position f is emulated by sending a chosen set of techs
to the back of the queue (remove, then re-add), in queue order:

    up   (f < x): every queued tech at position >= f except X
    down (f > x): X, then every queued tech at position > f
    end         : X only (it lands after the last shown tech)

Every tech beyond the shown ones (the overflow pop-up) is always re-queued
too, or it would end up in front. They live in a hidden copy of the overflow
list so they exist as widgets even while the pop-up is closed.

Drop zones (run 1 showed a drop has to land on the middle of a tech icon):
each shown tech has a gap on its left meaning "insert before me", its icon
keeps the run 1 meaning (moving left lands before it, moving right after
it), and a zone right of the row means "after the last shown tech".

Prerequisite check, before any command runs: the GUI builds a set of
"prerequisite>dependent" name pairs from the game's tech files, every shown
tech records its name by position, and every tech the move would cross
checks itself against the dragged one. A conflict blocks the drop and shows
"X needs Y first". Crossing is enough: in a chain Y -> A -> X with Y queued,
A has to sit between them, so a move of X past Y also crosses A.

The GUI cannot pass a number into script, so every (x, f) pair gets its own
animation names and its own literal member set, generated here. The same goes
for the queue-dump log lines, one scripted GUI per position.

This is a PROBE: it logs (RQ_PROBE|) what it fires and dumps the queue
before and after, read back by tools/rq_probe_report.py
(docs/research-queue-investigation.md).

Usage:
    python tools/gen_research_queue_probe.py           write the files
    python tools/gen_research_queue_probe.py --check   exit 1 if stale
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_references import VANILLA_ROOT  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
MOD = REPO / "research_queue"
OUT_GUI = MOD / "gui" / "00_research_queue_tech_tree_panel.gui"
OUT_SGUI = MOD / "common" / "scripted_guis" / "research_queue_probe_sgui.txt"

VANILLA_GUI = VANILLA_ROOT / "gui" / "tech_tree.gui"
DEFINES = VANILLA_ROOT / "common" / "defines" / "00_interfaces.txt"
TECH_DIR = VANILLA_ROOT / "common" / "technology" / "technologies"

DUMP_MAX = 40  # queue positions the dump can name; beyond this it logs "over"
GAP = 14       # px of drop gap left of each shown tech
ICON = 80      # vanilla queued_technology size
END_W = 60     # px of the "after the last shown tech" zone

PLAYER = "GetPlayer.Self"
POS = f"Technology.GetResearchQueuePosition({PLAYER})"
DRAGGED_POS = f"GetDraggedDatacontext('Technology').GetResearchQueuePosition({PLAYER})"
NAME = "Technology.GetNameNoFormatting"
XNAME = "GetVariableSystem.Get('rq_xname')"
ROOT_ONLY = "GuiScope.SetRoot(GetPlayer.MakeScope).End"
ROOT_TECH = "GuiScope.SetRoot(GetPlayer.MakeScope).AddScope('t', Technology.MakeScope).End"
BOM = "﻿"


def top_count() -> int:
    m = re.search(r"TECH_TREE_RESEARCH_QUEUE_DISPLAY_COUNT\s*=\s*(\d+)", DEFINES.read_text(encoding="utf-8-sig"))
    if not m:
        sys.exit(f"FAIL: TECH_TREE_RESEARCH_QUEUE_DISPLAY_COUNT not found in {DEFINES}")
    # +1: still unknown whether the shown list counts the tech being
    # researched (run 1 had too few techs queued to tell). One slot more is
    # harmless if it does and required if it does not.
    return int(m.group(1)) + 1


def block_at(text: str, start: int) -> int:
    """Index just past the brace block whose opening `{` is the first one at or after start."""
    i = text.index("{", start)
    depth = 0
    for j in range(i, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return j + 1
    sys.exit("FAIL: unbalanced braces while reading vanilla files")


def prereq_edges() -> list[tuple[str, str]]:
    """(prerequisite, dependent) for every unlocking_technologies entry."""
    edges = []
    for f in sorted(TECH_DIR.glob("*.txt")):
        text = re.sub(r"#[^\n]*", "", f.read_text(encoding="utf-8-sig"))
        for m in re.finditer(r"^(\w+)\s*=\s*\{", text, re.M):
            body = text[m.start():block_at(text, m.start())]
            u = re.search(r"unlocking_technologies\s*=\s*\{([^}]*)\}", body)
            if u:
                edges += [(p, m.group(1)) for p in u.group(1).split()]
    if not edges:
        sys.exit(f"FAIL: no unlocking_technologies found under {TECH_DIR}")
    return edges


def targets(x: int, n: int) -> list:
    return [f for f in range(1, n + 1) if f != x] + ["end"]


def members(x: int, f, n: int) -> list[int]:
    if f == "end":
        return [x]
    if x > f:
        return [p for p in range(f, n + 1) if p != x]
    return [x] + list(range(f + 1, n + 1))


def gap_target(x: int, k: int):
    """Final position when the tech at x is dropped in the gap before slot k."""
    if x in (k, k - 1):
        return None
    return k - 1 if x < k else k


def i32(n: int) -> str:
    return f"'(int32){n}'"


def ladder(cases: list[tuple[str, str]], default: str) -> str:
    expr = f"'{default}'"
    for cond, name in reversed(cases):
        expr = f"Select_CString({cond}, '{name}', {expr})"
    return expr


def any_of(terms: list[str]) -> str:
    cond = terms[-1]
    for t in reversed(terms[:-1]):  # Or() is binary in this engine
        cond = f"Or({t}, {cond})"
    return cond


def crossed(x: int, f) -> str:
    """True on the shown tech that a move of x to f passes over."""
    if f == "end":
        return f"GreaterThan_int32({POS}, {i32(x)})"
    if f < x:
        return f"And(GreaterThan_int32({POS}, {i32(f - 1)}), LessThan_int32({POS}, {i32(x)}))"
    return f"And(GreaterThan_int32({POS}, {i32(x)}), LessThan_int32({POS}, {i32(f + 1)}))"


def dump_parts(ind: str, tag: str) -> str:
    """rq_dump state plus its gate: logs this tech's queue position and name."""
    pos_ladder = ladder([(f"EqualTo_int32({POS}, {i32(p)})", f"rq_p_{p}") for p in range(1, DUMP_MAX + 1)], "rq_p_over")
    states = [f"{ind}\tstate = {{ name = rq_p_over  duration = 0  alpha = 1\n"
              f"{ind}\t\ton_start = \"[GetScriptedGui('rq_probe_{tag}_over').Execute({ROOT_TECH})]\"\n{ind}\t}}\n"]
    for p in range(1, DUMP_MAX + 1):
        states.append(f"{ind}\tstate = {{ name = rq_p_{p}  duration = 0  alpha = 1\n"
                      f"{ind}\t\ton_start = \"[GetScriptedGui('rq_probe_{tag}_{p}').Execute({ROOT_TECH})]\"\n{ind}\t}}\n")
    return (f"{ind}state = {{ name = rq_dump  duration = 0  alpha = 1\n"
            f"{ind}\ton_start = \"[PdxGuiWidget.FindChild('rq_dumpgate').TriggerAnimation({pos_ladder})]\"\n"
            f"{ind}}}\n"
            f"{ind}widget = {{\n{ind}\tname = \"rq_dumpgate\"\n{ind}\tsize = {{ 1 1 }}\n"
            + "".join(states) + f"{ind}}}\n")


def send_back(ind: str, log: str) -> str:
    return (f"{ind}on_start = \"[GetScriptedGui('{log}').Execute({ROOT_TECH})]\"\n"
            f"{ind}on_start = \"[Execute(Technology.RemoveFromQueue({PLAYER}))]\"\n"
            f"{ind}on_start = \"[Execute(Technology.AddToQueueWithUnlocks({PLAYER}))]\"\n")


def drop_target(ind: str, expr: str) -> str:
    return (f"{ind}drop_target = {{\n"
            f"{ind}\taccept_draggable_id = \"rq_tech\"\n"
            f"{ind}\ton_receive_drop = \"[PdxGuiTriggerAllAnimations({expr})]\"\n"
            f"{ind}}}\n")


def blk_state(ind: str, name: str, msg: str) -> str:
    return (f"{ind}state = {{ name = {name}  duration = 0  alpha = 1\n"
            f"{ind}\ton_start = \"[GetScriptedGui('rq_probe_blocked').Execute({ROOT_TECH})]\"\n"
            f"{ind}\ton_start = \"[GetVariableSystem.Set('rq_block', 'y')]\"\n"
            f"{ind}\ton_start = \"[GetVariableSystem.Set('rq_msg', {msg})]\"\n"
            f"{ind}}}\n")


def top_item(n: int) -> str:
    ind = "\t\t\t\t\t\t\t\t\t"
    pairs = [(x, f) for x in range(1, n + 1) for f in targets(x, n)]
    icon_drop = ladder([(f"And(EqualTo_int32({DRAGGED_POS}, {i32(x)}), EqualTo_int32({POS}, {i32(k)}))", f"rq_go_{x}_{k}")
                        for x in range(1, n + 1) for k in range(1, n + 1) if x != k], "rq_noop")
    gap_cases = []
    for x in range(1, n + 1):
        for k in range(1, n + 1):
            f = gap_target(x, k)
            if f is not None:
                gap_cases.append((f"And(EqualTo_int32({DRAGGED_POS}, {i32(x)}), EqualTo_int32({POS}, {i32(k)}))",
                                  f"rq_go_{x}_{f}"))
    gap_drop = ladder(gap_cases, "rq_noop")
    names = ladder([(f"EqualTo_int32({POS}, {i32(p)})", f"rq_n_{p}") for p in range(1, n + 1)], "rq_n_x")

    chain = []
    for x, f in pairs:
        cond = any_of([f"EqualTo_int32({POS}, {i32(p)})" for p in members(x, f, n)])
        chain.append(f"{ind}state = {{ name = rq_top_{x}_{f}  duration = 0  alpha = 1\n"
                     f"{ind}\ton_start = \"[PdxGuiWidget.FindChild('rq_gate').TriggerAnimation("
                     f"Select_CString({cond}, 'rq_do', 'rq_skip'))]\"\n{ind}}}\n")
        up = f != "end" and f < x
        key = f"Concatenate3({NAME}, '>', {XNAME})" if up else f"Concatenate3({XNAME}, '>', {NAME})"
        chain.append(f"{ind}state = {{ name = rq_chk_{x}_{f}  duration = 0  alpha = 1\n"
                     f"{ind}\ton_start = \"[PdxGuiWidget.FindChild('rq_chkgate').TriggerAnimation("
                     f"Select_CString(And({crossed(x, f)}, GetVariableSystem.Exists({key})), "
                     f"'{'rq_blk_up' if up else 'rq_blk_down'}', 'rq_skip'))]\"\n{ind}}}\n")
    chain.append(f"{ind}state = {{ name = rq_names  duration = 0  alpha = 1\n"
                 f"{ind}\ton_start = \"[GetVariableSystem.Set({names}, {NAME})]\"\n{ind}}}\n")

    return (
        "hbox = {\n"
        "\t\t\t\t\t\tdatamodel = \"[AccessPlayer.GetResearchQueueTop]\"\n"
        f"\t\t\t\t\t\tmargin_left = {20 - GAP}\n\n"
        "\t\t\t\t\t\titem = {\n"
        "\t\t\t\t\t\t\twidget = {\n"
        "\t\t\t\t\t\t\t\tvisible = \"[Not(Technology.IsResearching(GetPlayer.Self))]\"\n"
        f"\t\t\t\t\t\t\t\tsize = {{ {GAP + ICON} {ICON} }}\n\n"
        "\t\t\t\t\t\t\t\t# RQ: the gap left of this tech means \"insert before it\".\n"
        "\t\t\t\t\t\t\t\twidget = {\n"
        f"\t\t\t\t\t\t\t\t\tsize = {{ {GAP} {ICON} }}\n"
        "\t\t\t\t\t\t\t\t\talwaystransparent = no\n"
        + drop_target("\t\t\t\t\t\t\t\t\t", gap_drop) +
        "\t\t\t\t\t\t\t\t}\n\n"
        "\t\t\t\t\t\t\t\tqueued_technology = {\n"
        f"\t\t\t\t\t\t\t\t\tposition = {{ {GAP} 0 }}\n"
        "\t\t\t\t\t\t\t\t\talwaystransparent = no\n\n"
        "\t\t\t\t\t\t\t\t\t# RQ: drag a shown tech (vanilla pattern: construction_queue.gui:354).\n"
        "\t\t\t\t\t\t\t\t\t# Dropped on this icon: moving left lands before it, moving right after it.\n"
        "\t\t\t\t\t\t\t\t\tdraggable_behavior = {\n"
        "\t\t\t\t\t\t\t\t\t\tdraggable_id = \"rq_tech\"\n"
        "\t\t\t\t\t\t\t\t\t\tdrag_widget = {\n"
        "\t\t\t\t\t\t\t\t\t\t\twidget = {\n"
        "\t\t\t\t\t\t\t\t\t\t\t\tsize = { 1 1 }\n"
        "\t\t\t\t\t\t\t\t\t\t\t\tqueued_technology = {\n"
        "\t\t\t\t\t\t\t\t\t\t\t\t\tposition = \"[GuiCurrentDrag.CurrentPosition]\"\n"
        "\t\t\t\t\t\t\t\t\t\t\t\t\twidgetanchor = center\n"
        "\t\t\t\t\t\t\t\t\t\t\t\t\talpha = 0.7\n"
        "\t\t\t\t\t\t\t\t\t\t\t\t}\n"
        "\t\t\t\t\t\t\t\t\t\t\t}\n"
        "\t\t\t\t\t\t\t\t\t\t}\n"
        "\t\t\t\t\t\t\t\t\t}\n"
        + drop_target(ind, icon_drop) + "\n"
        + "".join(chain) +
        f"{ind}widget = {{\n{ind}\tname = \"rq_gate\"\n{ind}\tsize = {{ 1 1 }}\n"
        f"{ind}\tstate = {{ name = rq_skip  duration = 0  alpha = 1 }}\n"
        f"{ind}\tstate = {{ name = rq_do  duration = 0  alpha = 1\n"
        + send_back(ind + "\t\t", "rq_probe_fire_top") +
        f"{ind}\t}}\n{ind}}}\n"
        f"{ind}widget = {{\n{ind}\tname = \"rq_chkgate\"\n{ind}\tsize = {{ 1 1 }}\n"
        f"{ind}\tstate = {{ name = rq_skip  duration = 0  alpha = 1 }}\n"
        + blk_state(ind + "\t", "rq_blk_up", f"Concatenate4({XNAME}, ' needs ', {NAME}, ' first')")
        + blk_state(ind + "\t", "rq_blk_down", f"Concatenate4({NAME}, ' needs ', {XNAME}, ' first')") +
        f"{ind}}}\n\n"
        + dump_parts(ind, "pos") +
        "\n"
        f"{ind}# Probe readout: research progress, so a move that loses it shows.\n"
        f"{ind}textbox = {{\n{ind}\tparentanchor = bottom|left\n{ind}\tautoresize = yes\n"
        f"{ind}\talign = nobaseline\n"
        f"{ind}\traw_text = \"#v [Technology.GetProgress(GetPlayer.Self)|0]#!\"\n{ind}}}\n"
        "\t\t\t\t\t\t\t\t}\n"
        "\t\t\t\t\t\t\t}\n"
        "\t\t\t\t\t\t}\n"
        "\t\t\t\t\t}\n\n"
        + controller_and_tail(n)
    )


def edges_state(ind: str) -> str:
    lines = [f"{ind}\ton_start = \"[GetVariableSystem.Set(Concatenate3(GetTechnology('{p}').GetNameNoFormatting, '>', "
             f"GetTechnology('{t}').GetNameNoFormatting), 'y')]\"\n" for p, t in prereq_edges()]
    return (f"{ind}# Prerequisite pairs, \"prerequisite>dependent\" by tech name, from the\n"
            f"{ind}# game's common/technology/technologies at generation time.\n"
            f"{ind}state = {{ name = rq_edges  duration = 0  alpha = 1\n" + "".join(lines) + f"{ind}}}\n")


def controller_and_tail(n: int) -> str:
    ind = "\t\t\t\t\t\t"
    gos, execs = [], []
    for x in range(1, n + 1):
        for f in targets(x, n):
            gos.append(f"{ind}\tstate = {{ name = rq_go_{x}_{f}  duration = 0  alpha = 1\n"
                       f"{ind}\t\ton_start = \"[GetScriptedGui('rq_probe_drop_{x}_{f}').Execute({ROOT_ONLY})]\"\n"
                       f"{ind}\t\ton_start = \"[PdxGuiTriggerAllAnimations('rq_dump')]\"\n"
                       f"{ind}\t\ton_start = \"[GetVariableSystem.Clear('rq_block')]\"\n"
                       f"{ind}\t\ton_start = \"[GetVariableSystem.Clear('rq_msg')]\"\n"
                       f"{ind}\t\ton_start = \"[PdxGuiTriggerAllAnimations('rq_edges')]\"\n"
                       f"{ind}\t\ton_start = \"[PdxGuiTriggerAllAnimations('rq_names')]\"\n"
                       f"{ind}\t\ton_start = \"[GetVariableSystem.Set('rq_xname', GetVariableSystem.Get('rq_n_{x}'))]\"\n"
                       f"{ind}\t\ton_start = \"[PdxGuiTriggerAllAnimations('rq_chk_{x}_{f}')]\"\n"
                       f"{ind}\t\ton_start = \"[PdxGuiWidget.FindChild('rq_execgate').TriggerAnimation("
                       f"Select_CString(GetVariableSystem.Exists('rq_block'), 'rq_blocked', 'rq_exec_{x}_{f}'))]\"\n"
                       f"{ind}\t\tnext = rq_after\n{ind}\t}}\n")
            execs.append(f"{ind}\t\tstate = {{ name = rq_exec_{x}_{f}  duration = 0  alpha = 1\n"
                         f"{ind}\t\t\ton_start = \"[PdxGuiTriggerAllAnimations('rq_top_{x}_{f}')]\"\n"
                         f"{ind}\t\t\ton_start = \"[PdxGuiTriggerAllAnimations('rq_tail')]\"\n"
                         f"{ind}\t\t}}\n")
    end_drop = ladder([(f"EqualTo_int32({DRAGGED_POS}, {i32(x)})", f"rq_go_{x}_end") for x in range(1, n + 1)], "rq_noop")
    tail_ind = ind + "\t\t\t\t"
    return (
        "\t\t\t\t\t# RQ: the zone right of the last shown tech (\"after the last shown\"),\n"
        "\t\t\t\t\t# the controller (outside every datamodel, so it fires once), the\n"
        "\t\t\t\t\t# blocked-move message, and a hidden copy of the overflow list so\n"
        "\t\t\t\t\t# the techs beyond the shown ones exist as widgets and can be re-queued.\n"
        "\t\t\t\t\twidget = {\n"
        f"\t\t\t\t\t\tsize = {{ {END_W} {ICON} }}\n"
        "\t\t\t\t\t\talwaystransparent = no\n"
        + drop_target(ind, end_drop) + "\n"
        f"{ind}textbox = {{\n"
        f"{ind}\tvisible = \"[GetVariableSystem.Exists('rq_msg')]\"\n"
        f"{ind}\tposition = {{ {END_W + 90} 0 }}\n"
        f"{ind}\tsize = {{ 220 {ICON} }}\n"
        f"{ind}\tmultiline = yes\n"
        f"{ind}\talign = vcenter|nobaseline\n"
        f"{ind}\traw_text = \"#R [GetVariableSystem.Get('rq_msg')]#!\"\n"
        f"{ind}}}\n\n"
        f"{ind}widget = {{\n{ind}\tname = \"rq_controller\"\n{ind}\tsize = {{ 1 1 }}\n"
        f"{ind}\tstate = {{ name = rq_noop  duration = 0  alpha = 1\n"
        f"{ind}\t\ton_start = \"[GetScriptedGui('rq_probe_drop_noop').Execute({ROOT_ONLY})]\"\n{ind}\t}}\n"
        + "".join(gos) +
        f"{ind}\t# A second later, after the commands ran: dump the queue again.\n"
        f"{ind}\tstate = {{ name = rq_after  duration = 1  alpha = 1\n"
        f"{ind}\t\ton_finish = \"[GetScriptedGui('rq_probe_after').Execute({ROOT_ONLY})]\"\n"
        f"{ind}\t\ton_finish = \"[PdxGuiTriggerAllAnimations('rq_dump')]\"\n"
        f"{ind}\t\tnext = rq_msgclear\n{ind}\t}}\n"
        f"{ind}\tstate = {{ name = rq_msgclear  duration = 5  alpha = 1\n"
        f"{ind}\t\ton_finish = \"[GetVariableSystem.Clear('rq_msg')]\"\n{ind}\t}}\n\n"
        f"{ind}\twidget = {{\n{ind}\t\tname = \"rq_execgate\"\n{ind}\t\tsize = {{ 1 1 }}\n"
        f"{ind}\t\tstate = {{ name = rq_blocked  duration = 0  alpha = 1 }}\n"
        + "".join(execs) +
        f"{ind}\t}}\n\n"
        f"{ind}\twidget = {{\n{ind}\t\tsize = {{ 1 1 }}\n"
        + edges_state(ind + "\t\t") +
        f"{ind}\t}}\n"
        f"{ind}}}\n\n"
        f"{ind}flowcontainer = {{\n{ind}\tdirection = vertical\n"
        f"{ind}\tdatamodel = \"[AccessPlayer.GetResearchQueueBottom]\"\n\n"
        f"{ind}\titem = {{\n{ind}\t\twidget = {{\n{ind}\t\t\tsize = {{ 1 1 }}\n"
        f"{tail_ind}state = {{ name = rq_tail  duration = 0  alpha = 1\n"
        + send_back(tail_ind + "\t", "rq_probe_fire_tail") +
        f"{tail_ind}}}\n"
        + dump_parts(tail_ind, "tpos") +
        f"{ind}\t\t}}\n{ind}\t}}\n{ind}}}\n"
        "\t\t\t\t\t}"
    )


def build_gui() -> str:
    text = VANILLA_GUI.read_text(encoding="utf-8-sig")
    start = text.index("\ttype tech_tree_panel = ")
    panel = text[start:block_at(text, start)]
    anchor = 'datamodel = "[AccessPlayer.GetResearchQueueTop]"'
    if panel.count(anchor) != 1:
        sys.exit(f"FAIL: expected exactly one research queue hbox in tech_tree_panel, found {panel.count(anchor)}")
    a = panel.index(anchor)
    hb = panel.rindex("hbox = {", 0, a)
    end = block_at(panel, hb)
    vanilla_item = panel[hb:end]
    if "queued_technology" not in vanilla_item:
        sys.exit("FAIL: the research queue hbox no longer instantiates queued_technology; re-read vanilla")
    panel = panel[:hb] + top_item(top_count()) + panel[end:]
    return (BOM +
            "# GENERATED by tools/gen_research_queue_probe.py from the installed game's\n"
            "# gui/tech_tree.gui and common/technology/technologies. Do not edit by hand:\n"
            "# change the generator and re-run.\n"
            "# Redefines the single vanilla type tech_tree_panel; the 00_ prefix makes\n"
            "# this file load before tech_tree.gui, so this definition wins\n"
            "# (docs/engine-notes.md, \"A partial .gui override works\").\n"
            "types research_queue_types\n{\n" + panel + "\n}\n")


def sgui(name: str, line: str, saved: bool) -> str:
    return (f"{name} = {{\n\tscope = country\n"
            + ("\tsaved_scopes = { t }\n" if saved else "")
            + f"\teffect = {{\n\t\tdebug_log = \"{line}\"\n\t}}\n"
            "\tai_is_valid = { always = no }\n\tai_chance = { base = 0 }\n}\n\n")


def build_sgui() -> str:
    n = top_count()
    out = [BOM, "# GENERATED by tools/gen_research_queue_probe.py. Probe logging only:\n"
                "# every entry writes one RQ_PROBE| line to debug.log and changes nothing.\n\n"]
    name = "[SCOPE.sT('t').GetName]"
    for tag in ("pos", "tpos"):  # pos = a shown tech, tpos = one in the overflow pop-up
        for p in range(1, DUMP_MAX + 1):
            out.append(sgui(f"rq_probe_{tag}_{p}", f"RQ_PROBE|{tag}|{p}|{name}", True))
        out.append(sgui(f"rq_probe_{tag}_over", f"RQ_PROBE|{tag}|over|{name}", True))
    for x in range(1, n + 1):
        for f in targets(x, n):
            out.append(sgui(f"rq_probe_drop_{x}_{f}", f"RQ_PROBE|drop|{x}|{f}", False))
    out.append(sgui("rq_probe_drop_noop", "RQ_PROBE|drop|noop", False))
    out.append(sgui("rq_probe_after", "RQ_PROBE|after", False))
    for ev in ("fire_top", "fire_tail", "blocked"):
        out.append(sgui(f"rq_probe_{ev}", f"RQ_PROBE|{ev}|{name}", True))
    return "".join(out)


def main() -> int:
    check = "--check" in sys.argv[1:]
    if not VANILLA_GUI.is_file():
        print(f"FAIL: {VANILLA_GUI} not found (game not installed?)")
        return 1
    stale = []
    for path, content in ((OUT_GUI, build_gui()), (OUT_SGUI, build_sgui())):
        # Normalise line endings: git's autocrlf rewrites these files to CRLF
        # on checkout, which must not read as a stale generation.
        current = path.read_text(encoding="utf-8").replace("\r\n", "\n") if path.exists() else None
        if current == content:
            continue
        if check:
            stale.append(path)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="\n")
            print(f"wrote {path.relative_to(REPO)}")
    if stale:
        for p in stale:
            print(f"STALE: {p.relative_to(REPO)} (re-run tools/gen_research_queue_probe.py)")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
