"""Generate the Research Queue probe build (research_queue/).

The engine has no "move a tech to position N" command (Technology exposes
only AddToQueue, AddToQueueWithUnlocks, RemoveFromQueue, Research,
ResearchWithUnlocks; see reference/data_types). A move is emulated by
sending a chosen set of techs to the back of the queue (remove, then
re-add), in queue order. Moving tech X to slot f, with its queued
prerequisites or dependents travelling with it:

    up to f   : X and its prerequisites (direct or indirect) stay; every
                other tech at position >= f goes to the back
    down to f : X, every tech at position > f, and every dependent of X go
                to the back; the rest stays

Removing a tech also removes its queued dependents (run 2), so a sent-back
tech must never leave a dependent behind: every dependent of a sent-back
tech is itself in the set, later in queue order, and comes back with it.

Ordering (run 2): triggered GUI states run when the walk of the widget tree
reaches them, not in call order. So nothing here waits on another state's
result. The dragged tech's name is recorded when the drag starts; the drop
handler refuses the move if it does not match the dropped tech. The
controller sits before the queue row in the tree and the hidden overflow
list after it, so one pass sends the shown techs back before the overflow.

Drop zones: each shown tech has a gap on its left ("insert before me"), its
icon means "before it" when moving left and "after it" when moving right,
and a zone right of the row means "after the last shown tech". The drag
itself lives in the vanilla type queued_technology (redefined here), so the
techs in the "+N" pop-up can be dragged onto the row too.

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
DRAGGED = "GetDraggedDatacontext('Technology')"
DRAGGED_POS = f"{DRAGGED}.GetResearchQueuePosition({PLAYER})"
NAME = "Technology.GetNameNoFormatting"
XNAME = "GetVariableSystem.Get('rq_xname')"
IS_X = f"GetVariableSystem.Exists(Concatenate('rq_isx_', {NAME}))"
PRE_OF_X = f"GetVariableSystem.Exists(Concatenate3({NAME}, '>', {XNAME}))"
DEP_OF_X = f"GetVariableSystem.Exists(Concatenate3({XNAME}, '>', {NAME}))"
ROOT_ONLY = "GuiScope.SetRoot(GetPlayer.MakeScope).End"
ROOT_TECH = "GuiScope.SetRoot(GetPlayer.MakeScope).AddScope('t', Technology.MakeScope).End"
BOM = "﻿"


def shown_count() -> int:
    """Queued techs the row shows. Run 2 confirmed it is the define itself:
    5 `pos` lines with 6+ techs queued; the current research is not one."""
    m = re.search(r"TECH_TREE_RESEARCH_QUEUE_DISPLAY_COUNT\s*=\s*(\d+)", DEFINES.read_text(encoding="utf-8-sig"))
    if not m:
        sys.exit(f"FAIL: TECH_TREE_RESEARCH_QUEUE_DISPLAY_COUNT not found in {DEFINES}")
    return int(m.group(1))


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


def ancestor_pairs() -> list[tuple[str, str]]:
    """(prerequisite, dependent) for every direct or indirect prerequisite."""
    direct: dict[str, set[str]] = {}
    for p, t in prereq_edges():
        direct.setdefault(t, set()).add(p)
    memo: dict[str, set[str]] = {}

    def anc(t: str) -> set[str]:
        if t not in memo:
            memo[t] = set()
            for p in direct.get(t, ()):
                memo[t] |= {p} | anc(p)
        return memo[t]

    return sorted((p, t) for t in direct for p in anc(t))


def i32(n: int) -> str:
    return f"'(int32){n}'"


def ladder(cases: list[tuple[str, str]], default: str) -> str:
    expr = f"'{default}'"
    for cond, name in reversed(cases):
        expr = f"Select_CString({cond}, '{name}', {expr})"
    return expr


def moves(n: int) -> list[tuple[str, int]]:
    return [("up", f) for f in range(1, n + 1)] + [("down", f) for f in range(2, n + 1)]


def guarded(cases: list[tuple[str, str]]) -> str:
    """A drop expression: refuse unless the name recorded at drag start is the dropped tech's."""
    match = f"EqualTo_string({DRAGGED}.GetNameNoFormatting, {XNAME})"
    return f"Select_CString({match}, {ladder(cases, 'rq_noop')}, 'rq_badx')"


def at(k: int, cond: str) -> str:
    return f"And(EqualTo_int32({POS}, {i32(k)}), {cond})"


def icon_drop(n: int) -> str:
    cases = []
    for k in range(1, n + 1):
        cases.append((at(k, f"GreaterThan_int32({DRAGGED_POS}, {i32(k)})"), f"rq_go_up_{k}"))
        if k >= 2:
            cases.append((at(k, f"LessThan_int32({DRAGGED_POS}, {i32(k)})"), f"rq_go_down_{k}"))
    return guarded(cases)


def gap_drop(n: int) -> str:
    cases = []
    for k in range(1, n + 1):
        cases.append((at(k, f"GreaterThan_int32({DRAGGED_POS}, {i32(k)})"), f"rq_go_up_{k}"))
        if k >= 3:
            cases.append((at(k, f"LessThan_int32({DRAGGED_POS}, {i32(k - 1)})"), f"rq_go_down_{k - 1}"))
    return guarded(cases)


def end_drop(n: int) -> str:
    return guarded([(f"LessThan_int32({DRAGGED_POS}, {i32(n)})", f"rq_go_down_{n}")])


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


def mover_parts(ind: str, log: str, member: dict) -> str:
    """One rq_mv_<dir>_<f> state per move, each gating this tech into the
    send-back set, plus the gates. `member` maps (dir, f) to a condition, or
    to None for "always"."""
    states = []
    for (d, f), cond in member.items():
        pick = "'rq_do'" if cond is None else f"Select_CString({cond}, 'rq_do', 'rq_skip')"
        states.append(f"{ind}state = {{ name = rq_mv_{d}_{f}  duration = 0  alpha = 1\n"
                      f"{ind}\ton_start = \"[PdxGuiWidget.FindChild('rq_xgate').TriggerAnimation("
                      f"Select_CString({IS_X}, 'rq_xlog', 'rq_skip'))]\"\n"
                      f"{ind}\ton_start = \"[PdxGuiWidget.FindChild('rq_gate').TriggerAnimation({pick})]\"\n"
                      f"{ind}}}\n")
    return ("".join(states) +
            f"{ind}widget = {{\n{ind}\tname = \"rq_gate\"\n{ind}\tsize = {{ 1 1 }}\n"
            f"{ind}\tstate = {{ name = rq_skip  duration = 0  alpha = 1 }}\n"
            f"{ind}\tstate = {{ name = rq_do  duration = 0  alpha = 1\n"
            f"{ind}\t\ton_start = \"[GetScriptedGui('{log}').Execute({ROOT_TECH})]\"\n"
            f"{ind}\t\ton_start = \"[Execute(Technology.RemoveFromQueue({PLAYER}))]\"\n"
            f"{ind}\t\ton_start = \"[Execute(Technology.AddToQueueWithUnlocks({PLAYER}))]\"\n"
            f"{ind}\t}}\n{ind}}}\n"
            f"{ind}widget = {{\n{ind}\tname = \"rq_xgate\"\n{ind}\tsize = {{ 1 1 }}\n"
            f"{ind}\tstate = {{ name = rq_skip  duration = 0  alpha = 1 }}\n"
            f"{ind}\tstate = {{ name = rq_xlog  duration = 0  alpha = 1\n"
            f"{ind}\t\ton_start = \"[GetScriptedGui('rq_probe_x').Execute({ROOT_TECH})]\"\n"
            f"{ind}\t}}\n{ind}}}\n")


def row_member(d: str, f: int):
    if d == "up":
        return f"And(GreaterThan_int32({POS}, {i32(f - 1)}), Not(Or({IS_X}, {PRE_OF_X})))"
    return f"Or({IS_X}, Or(GreaterThan_int32({POS}, {i32(f)}), {DEP_OF_X}))"


def tail_member(d: str, f: int):
    # Overflow techs sit beyond every slot f; on a down move all of them go.
    return f"Not(Or({IS_X}, {PRE_OF_X}))" if d == "up" else None


def drop_target(ind: str, expr: str) -> str:
    return (f"{ind}drop_target = {{\n"
            f"{ind}\taccept_draggable_id = \"rq_tech\"\n"
            f"{ind}\ton_receive_drop = \"[PdxGuiTriggerAllAnimations({expr})]\"\n"
            f"{ind}}}\n")


def queued_technology_type() -> str:
    """Vanilla's type queued_technology plus the drag. The row and the "+N"
    pop-up both instantiate it, so both become draggable."""
    text = VANILLA_GUI.read_text(encoding="utf-8-sig")
    start = text.index("\ttype queued_technology = ")
    body = text[start:block_at(text, start)]
    anchor = "\t\tsize = { 80 80 }\n"
    if body.count(anchor) < 1 or not body.startswith("\ttype queued_technology = widget {"):
        sys.exit("FAIL: vanilla type queued_technology changed shape; re-read tech_tree.gui")
    drag = (
        "\n\t\t# RQ: drag this tech (vanilla pattern: construction_queue.gui:354). The\n"
        "\t\t# drag widget records the dragged tech's name when it is created; the\n"
        "\t\t# drop refuses the move unless the name matches the dropped tech.\n"
        "\t\tdraggable_behavior = {\n"
        "\t\t\tdraggable_id = \"rq_tech\"\n"
        "\t\t\tdrag_widget = {\n"
        "\t\t\t\twidget = {\n"
        "\t\t\t\t\tsize = { 1 1 }\n"
        "\t\t\t\t\twidget = {\n"
        "\t\t\t\t\t\tposition = \"[GuiCurrentDrag.CurrentPosition]\"\n"
        "\t\t\t\t\t\twidgetanchor = center\n"
        f"\t\t\t\t\t\tsize = {{ {ICON} {ICON} }}\n"
        "\t\t\t\t\t\talpha = 0.7\n"
        "\t\t\t\t\t\tstate = { name = rq_dragstart  trigger_on_create = yes  duration = 0  alpha = 0.7\n"
        f"\t\t\t\t\t\t\ton_start = \"[GetVariableSystem.Set('rq_xname', {NAME})]\"\n"
        "\t\t\t\t\t\t}\n"
        "\t\t\t\t\t\ticon = {\n"
        "\t\t\t\t\t\t\ttexture = \"gfx/interface/backgrounds/round_frame_dec.dds\"\n"
        "\t\t\t\t\t\t\tparentanchor = center\n"
        f"\t\t\t\t\t\t\tsize = {{ {ICON} {ICON} }}\n"
        "\t\t\t\t\t\t}\n"
        "\t\t\t\t\t\ticon = {\n"
        "\t\t\t\t\t\t\tparentanchor = center\n"
        "\t\t\t\t\t\t\tsize = { 60 60 }\n"
        "\t\t\t\t\t\t\ttexture = \"[Technology.GetTexture]\"\n"
        "\t\t\t\t\t\t}\n"
        "\t\t\t\t\t}\n"
        "\t\t\t\t}\n"
        "\t\t\t}\n"
        "\t\t}\n"
    )
    return body.replace(anchor, anchor + drag, 1)


def controller(n: int) -> str:
    ind = "\t\t\t\t\t\t"
    gos = []
    for d, f in moves(n):
        gos.append(f"{ind}state = {{ name = rq_go_{d}_{f}  duration = 0  alpha = 1\n"
                   f"{ind}\ton_start = \"[GetScriptedGui('rq_probe_drop_{d}_{f}').Execute({ROOT_ONLY})]\"\n"
                   f"{ind}\ton_start = \"[GetVariableSystem.Set(Concatenate('rq_isx_', {XNAME}), 'y')]\"\n"
                   f"{ind}\ton_start = \"[PdxGuiTriggerAllAnimations('rq_dump')]\"\n"
                   f"{ind}\ton_start = \"[PdxGuiTriggerAllAnimations('rq_edges')]\"\n"
                   f"{ind}\ton_start = \"[PdxGuiTriggerAllAnimations('rq_mv_{d}_{f}')]\"\n"
                   f"{ind}\tnext = rq_after\n{ind}}}\n")
    for name in ("noop", "badx"):
        gos.append(f"{ind}state = {{ name = rq_{name}  duration = 0  alpha = 1\n"
                   f"{ind}\ton_start = \"[GetScriptedGui('rq_probe_drop_{name}').Execute({ROOT_ONLY})]\"\n{ind}}}\n")
    lines = [f"{ind}\t\ton_start = \"[GetVariableSystem.Set(Concatenate3(GetTechnology('{p}').GetNameNoFormatting, '>', "
             f"GetTechnology('{t}').GetNameNoFormatting), 'y')]\"\n" for p, t in ancestor_pairs()]
    return (
        "# RQ: the controller, BEFORE the queue row in the widget tree, so the\n"
        "\t\t\t\t\t# states it triggers on the row and on the overflow list (after the\n"
        "\t\t\t\t\t# row) run in that order. Outside every datamodel, so it fires once.\n"
        "\t\t\t\t\twidget = {\n"
        "\t\t\t\t\t\tname = \"rq_controller\"\n"
        "\t\t\t\t\t\tsize = { 1 1 }\n"
        + "".join(gos) +
        f"{ind}# A second later, after the commands ran: dump the queue again.\n"
        f"{ind}state = {{ name = rq_after  duration = 1  alpha = 1\n"
        f"{ind}\ton_finish = \"[GetScriptedGui('rq_probe_after').Execute({ROOT_ONLY})]\"\n"
        f"{ind}\ton_finish = \"[PdxGuiTriggerAllAnimations('rq_dump')]\"\n"
        f"{ind}\ton_finish = \"[GetVariableSystem.Clear(Concatenate('rq_isx_', {XNAME}))]\"\n"
        f"{ind}\ton_finish = \"[GetVariableSystem.Clear('rq_xname')]\"\n"
        f"{ind}}}\n\n"
        f"{ind}# Every direct or indirect prerequisite pair, \"prerequisite>dependent\"\n"
        f"{ind}# by tech name, from the game's common/technology/technologies at\n"
        f"{ind}# generation time. Built when the panel is created and on every drop.\n"
        f"{ind}widget = {{\n{ind}\tsize = {{ 1 1 }}\n"
        f"{ind}\tstate = {{ name = rq_edges  trigger_on_create = yes  duration = 0  alpha = 1\n"
        + "".join(lines) +
        f"{ind}\t}}\n{ind}}}\n"
        "\t\t\t\t\t}\n\n\t\t\t\t\t"
    )


def row(n: int) -> str:
    ind = "\t\t\t\t\t\t\t\t\t"
    member = {(d, f): row_member(d, f) for d, f in moves(n)}
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
        + drop_target("\t\t\t\t\t\t\t\t\t", gap_drop(n)) +
        "\t\t\t\t\t\t\t\t}\n\n"
        "\t\t\t\t\t\t\t\tqueued_technology = {\n"
        f"\t\t\t\t\t\t\t\t\tposition = {{ {GAP} 0 }}\n"
        "\t\t\t\t\t\t\t\t\talwaystransparent = no\n\n"
        "\t\t\t\t\t\t\t\t\t# RQ: dropped on this icon, moving left lands before it, moving right after it.\n"
        + drop_target(ind, icon_drop(n)) + "\n"
        + mover_parts(ind, "rq_probe_fire_top", member) + "\n"
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
    )


def end_zone_and_tail(n: int) -> str:
    ind = "\t\t\t\t\t\t"
    tail_ind = ind + "\t\t\t"
    member = {(d, f): tail_member(d, f) for d, f in moves(n)}
    return (
        "\t\t\t\t\t# RQ: the zone right of the last shown tech (\"after the last shown\"),\n"
        "\t\t\t\t\t# holding a hidden copy of the overflow list, AFTER the row in the\n"
        "\t\t\t\t\t# tree, so the techs beyond the shown ones exist as widgets and are\n"
        "\t\t\t\t\t# re-queued after the shown ones.\n"
        "\t\t\t\t\twidget = {\n"
        f"\t\t\t\t\t\tsize = {{ {END_W} {ICON} }}\n"
        "\t\t\t\t\t\talwaystransparent = no\n"
        + drop_target(ind, end_drop(n)) + "\n"
        f"{ind}flowcontainer = {{\n{ind}\tdirection = vertical\n"
        f"{ind}\tdatamodel = \"[AccessPlayer.GetResearchQueueBottom]\"\n\n"
        f"{ind}\titem = {{\n{ind}\t\twidget = {{\n{ind}\t\t\tsize = {{ 1 1 }}\n"
        + mover_parts(tail_ind, "rq_probe_fire_tail", member)
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
    if "queued_technology" not in panel[hb:end]:
        sys.exit("FAIL: the research queue hbox no longer instantiates queued_technology; re-read vanilla")
    n = shown_count()
    panel = panel[:hb] + controller(n) + row(n) + end_zone_and_tail(n) + panel[end:]
    return (BOM +
            "# GENERATED by tools/gen_research_queue_probe.py from the installed game's\n"
            "# gui/tech_tree.gui and common/technology/technologies. Do not edit by hand:\n"
            "# change the generator and re-run.\n"
            "# Redefines the vanilla types tech_tree_panel and queued_technology; the 00_\n"
            "# prefix makes this file load before tech_tree.gui, so these definitions win\n"
            "# (docs/engine-notes.md, \"A partial .gui override works\").\n"
            "types research_queue_types\n{\n" + panel + "\n\n" + queued_technology_type() + "\n}\n")


def sgui(name: str, line: str, saved: bool) -> str:
    return (f"{name} = {{\n\tscope = country\n"
            + ("\tsaved_scopes = { t }\n" if saved else "")
            + f"\teffect = {{\n\t\tdebug_log = \"{line}\"\n\t}}\n"
            "\tai_is_valid = { always = no }\n\tai_chance = { base = 0 }\n}\n\n")


def build_sgui() -> str:
    out = [BOM, "# GENERATED by tools/gen_research_queue_probe.py. Probe logging only:\n"
                "# every entry writes one RQ_PROBE| line to debug.log and changes nothing.\n\n"]
    name = "[SCOPE.sT('t').GetName]"
    for tag in ("pos", "tpos"):  # pos = a shown tech, tpos = one in the overflow pop-up
        for p in range(1, DUMP_MAX + 1):
            out.append(sgui(f"rq_probe_{tag}_{p}", f"RQ_PROBE|{tag}|{p}|{name}", True))
        out.append(sgui(f"rq_probe_{tag}_over", f"RQ_PROBE|{tag}|over|{name}", True))
    for d, f in moves(shown_count()):
        out.append(sgui(f"rq_probe_drop_{d}_{f}", f"RQ_PROBE|drop|{d}|{f}", False))
    for ev in ("noop", "badx"):
        out.append(sgui(f"rq_probe_drop_{ev}", f"RQ_PROBE|drop|{ev}", False))
    out.append(sgui("rq_probe_after", "RQ_PROBE|after", False))
    for ev in ("fire_top", "fire_tail", "x"):
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
