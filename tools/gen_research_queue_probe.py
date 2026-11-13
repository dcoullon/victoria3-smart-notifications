"""Generate the Research Queue probe build (research_queue/).

The engine has no "move a tech to position N" command (Technology exposes
only AddToQueue, AddToQueueWithUnlocks, RemoveFromQueue, Research,
ResearchWithUnlocks; see reference/data_types). So a drop of tech X onto
tech Y is emulated by sending a chosen set of techs to the back of the queue
(remove, then re-add), in queue order. For X at old position x dropped on
the slot k:

    up   (x > k): every queued tech at position >= k except X
    down (x < k): X, then every queued tech at position > k

Only the first TECH_TREE_RESEARCH_QUEUE_DISPLAY_COUNT positions are drag
targets (the user's scope: the techs shown, not the overflow pop-up). Every
tech beyond them is always in the set, because sending anything to the back
puts it behind them otherwise. They live in a hidden copy of the overflow
list so they exist as widgets even while the pop-up is closed.

The GUI cannot pass a number into script, so every (x, k) pair gets its own
animation name and its own literal member set, generated here. The same goes
for the queue-dump log lines, one scripted GUI per position.

This is a PROBE: it logs (RQ_PROBE|) what it fires and dumps the queue
before and after, so one playtest answers every open question in
docs/research-queue-investigation.md. It does not yet check prerequisites.

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

DUMP_MAX = 40  # queue positions the dump can name; beyond this it logs "over"

PLAYER = "GetPlayer.Self"
POS = f"Technology.GetResearchQueuePosition({PLAYER})"
DRAGGED_POS = f"GetDraggedDatacontext('Technology').GetResearchQueuePosition({PLAYER})"
ROOT_ONLY = "GuiScope.SetRoot(GetPlayer.MakeScope).End"
ROOT_TECH = "GuiScope.SetRoot(GetPlayer.MakeScope).AddScope('t', Technology.MakeScope).End"
BOM = "﻿"


def top_count() -> int:
    m = re.search(r"TECH_TREE_RESEARCH_QUEUE_DISPLAY_COUNT\s*=\s*(\d+)", DEFINES.read_text(encoding="utf-8-sig"))
    if not m:
        sys.exit(f"FAIL: TECH_TREE_RESEARCH_QUEUE_DISPLAY_COUNT not found in {DEFINES}")
    # +1: unknown whether the shown list counts the tech being researched.
    # One slot more is harmless if it does (a shown-tech gate naming N+1 never
    # matches; that tech sits in the overflow list and is re-queued as tail)
    # and required if it does not.
    return int(m.group(1)) + 1


def members(x: int, k: int, n: int) -> list[int]:
    if x > k:
        return [p for p in range(k, n + 1) if p != x]
    return [x] + list(range(k + 1, n + 1))


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
    sys.exit("FAIL: unbalanced braces in vanilla tech_tree.gui")


def i32(n: int) -> str:
    return f"'(int32){n}'"


def ladder(cases: list[tuple[str, str]], default: str) -> str:
    expr = f"'{default}'"
    for cond, name in reversed(cases):
        expr = f"Select_CString({cond}, '{name}', {expr})"
    return expr


def pos_ladder() -> str:
    return ladder([(f"EqualTo_int32({POS}, {i32(p)})", f"rq_p_{p}") for p in range(1, DUMP_MAX + 1)], "rq_p_over")


def dump_parts(ind: str) -> str:
    """rq_dump state plus its gate: logs this tech's queue position and name."""
    states = [f"{ind}\tstate = {{ name = rq_p_over  duration = 0  alpha = 1\n"
              f"{ind}\t\ton_start = \"[GetScriptedGui('rq_probe_pos_over').Execute({ROOT_TECH})]\"\n{ind}\t}}\n"]
    for p in range(1, DUMP_MAX + 1):
        states.append(f"{ind}\tstate = {{ name = rq_p_{p}  duration = 0  alpha = 1\n"
                      f"{ind}\t\ton_start = \"[GetScriptedGui('rq_probe_pos_{p}').Execute({ROOT_TECH})]\"\n{ind}\t}}\n")
    return (f"{ind}state = {{ name = rq_dump  duration = 0  alpha = 1\n"
            f"{ind}\ton_start = \"[PdxGuiWidget.FindChild('rq_dumpgate').TriggerAnimation({pos_ladder()})]\"\n"
            f"{ind}}}\n"
            f"{ind}widget = {{\n{ind}\tname = \"rq_dumpgate\"\n{ind}\tsize = {{ 1 1 }}\n"
            + "".join(states) + f"{ind}}}\n")


def send_back(ind: str, log: str) -> str:
    return (f"{ind}on_start = \"[GetScriptedGui('{log}').Execute({ROOT_TECH})]\"\n"
            f"{ind}on_start = \"[Execute(Technology.RemoveFromQueue({PLAYER}))]\"\n"
            f"{ind}on_start = \"[Execute(Technology.AddToQueueWithUnlocks({PLAYER}))]\"\n")


def top_item(n: int) -> str:
    ind = "\t\t\t\t\t\t\t\t\t"
    pairs = [(x, k) for x in range(1, n + 1) for k in range(1, n + 1) if x != k]
    drop = ladder([(f"And(EqualTo_int32({DRAGGED_POS}, {i32(x)}), EqualTo_int32({POS}, {i32(k)}))", f"rq_go_{x}_{k}")
                   for x, k in pairs], "rq_noop")
    chain = []
    for x, k in pairs:
        terms = [f"EqualTo_int32({POS}, {i32(p)})" for p in members(x, k, n)]
        cond = terms[-1]
        for t in reversed(terms[:-1]):  # Or() is binary in this engine
            cond = f"Or({t}, {cond})"
        chain.append(f"{ind}state = {{ name = rq_top_{x}_{k}  duration = 0  alpha = 1\n"
                     f"{ind}\ton_start = \"[PdxGuiWidget.FindChild('rq_gate').TriggerAnimation("
                     f"Select_CString({cond}, 'rq_do', 'rq_skip'))]\"\n{ind}}}\n")
    return (
        "hbox = {\n"
        "\t\t\t\t\t\tdatamodel = \"[AccessPlayer.GetResearchQueueTop]\"\n"
        "\t\t\t\t\t\tmargin_left = 20\n"
        "\t\t\t\t\t\tspacing = 5\n\n"
        "\t\t\t\t\t\titem = {\n"
        "\t\t\t\t\t\t\tqueued_technology = {\n"
        "\t\t\t\t\t\t\t\tvisible = \"[Not(Technology.IsResearching(GetPlayer.Self))]\"\n"
        "\t\t\t\t\t\t\t\talwaystransparent = no\n\n"
        "\t\t\t\t\t\t\t\t# RQ probe: drag one shown tech onto another (vanilla pattern:\n"
        "\t\t\t\t\t\t\t\t# construction_queue.gui:354). The drop names the (x, k) pair.\n"
        "\t\t\t\t\t\t\t\tdraggable_behavior = {\n"
        "\t\t\t\t\t\t\t\t\tdraggable_id = \"rq_tech\"\n"
        "\t\t\t\t\t\t\t\t\tdrag_widget = {\n"
        "\t\t\t\t\t\t\t\t\t\twidget = {\n"
        "\t\t\t\t\t\t\t\t\t\t\tsize = { 1 1 }\n"
        "\t\t\t\t\t\t\t\t\t\t\tqueued_technology = {\n"
        "\t\t\t\t\t\t\t\t\t\t\t\tposition = \"[GuiCurrentDrag.CurrentPosition]\"\n"
        "\t\t\t\t\t\t\t\t\t\t\t\twidgetanchor = center\n"
        "\t\t\t\t\t\t\t\t\t\t\t}\n"
        "\t\t\t\t\t\t\t\t\t\t}\n"
        "\t\t\t\t\t\t\t\t\t}\n"
        "\t\t\t\t\t\t\t\t}\n"
        "\t\t\t\t\t\t\t\tdrop_target = {\n"
        "\t\t\t\t\t\t\t\t\taccept_draggable_id = \"rq_tech\"\n"
        f"\t\t\t\t\t\t\t\t\ton_receive_drop = \"[PdxGuiTriggerAllAnimations({drop})]\"\n"
        "\t\t\t\t\t\t\t\t}\n\n"
        + "".join(chain) +
        f"{ind}widget = {{\n{ind}\tname = \"rq_gate\"\n{ind}\tsize = {{ 1 1 }}\n"
        f"{ind}\tstate = {{ name = rq_skip  duration = 0  alpha = 1 }}\n"
        f"{ind}\tstate = {{ name = rq_do  duration = 0  alpha = 1\n"
        + send_back(ind + "\t\t", "rq_probe_fire_top") +
        f"{ind}\t}}\n{ind}}}\n\n"
        + dump_parts(ind) +
        "\n"
        f"{ind}# Probe readout: research progress, so a move that loses it shows.\n"
        f"{ind}textbox = {{\n{ind}\tparentanchor = bottom|left\n{ind}\tautoresize = yes\n"
        f"{ind}\talign = nobaseline\n"
        f"{ind}\traw_text = \"#v [Technology.GetProgress(GetPlayer.Self)|0]#!\"\n{ind}}}\n\n"
        f"{ind}# Probe buttons. N = ResearchWithUnlocks (vanilla's plain click).\n"
        f"{ind}# B = remove then re-add in ONE click: tests command ordering.\n"
        f"{ind}button_icon_round = {{\n{ind}\tparentanchor = bottom|right\n{ind}\tsize = {{ 26 26 }}\n"
        f"{ind}\tposition = {{ -28 0 }}\n"
        f"{ind}\tonclick = \"[GetScriptedGui('rq_probe_now').Execute({ROOT_TECH})]\"\n"
        f"{ind}\tonclick = \"[PdxGuiTriggerAllAnimations('rq_dump')]\"\n"
        f"{ind}\tonclick = \"[Execute(Technology.ResearchWithUnlocks(GetPlayer.Self))]\"\n"
        f"{ind}\tonclick = \"[PdxGuiTriggerAllAnimations('rq_after')]\"\n"
        f"{ind}\ttextbox = {{ parentanchor = center  autoresize = yes  align = nobaseline  raw_text = \"N\" }}\n{ind}}}\n"
        f"{ind}button_icon_round = {{\n{ind}\tparentanchor = bottom|right\n{ind}\tsize = {{ 26 26 }}\n"
        f"{ind}\tonclick = \"[GetScriptedGui('rq_probe_back').Execute({ROOT_TECH})]\"\n"
        f"{ind}\tonclick = \"[PdxGuiTriggerAllAnimations('rq_dump')]\"\n"
        f"{ind}\tonclick = \"[Execute(Technology.RemoveFromQueue(GetPlayer.Self))]\"\n"
        f"{ind}\tonclick = \"[Execute(Technology.AddToQueueWithUnlocks(GetPlayer.Self))]\"\n"
        f"{ind}\tonclick = \"[PdxGuiTriggerAllAnimations('rq_after')]\"\n"
        f"{ind}\ttextbox = {{ parentanchor = center  autoresize = yes  align = nobaseline  raw_text = \"B\" }}\n{ind}}}\n"
        "\t\t\t\t\t\t\t}\n"
        "\t\t\t\t\t\t}\n"
        "\t\t\t\t\t}\n\n"
        + controller_and_tail(n)
    )


def controller_and_tail(n: int) -> str:
    ind = "\t\t\t\t\t\t\t"
    gos = []
    for x in range(1, n + 1):
        for k in range(1, n + 1):
            if x == k:
                continue
            gos.append(f"{ind}\tstate = {{ name = rq_go_{x}_{k}  duration = 0  alpha = 1\n"
                       f"{ind}\t\ton_start = \"[GetScriptedGui('rq_probe_drop_{x}_{k}').Execute({ROOT_ONLY})]\"\n"
                       f"{ind}\t\ton_start = \"[PdxGuiTriggerAllAnimations('rq_dump')]\"\n"
                       f"{ind}\t\ton_start = \"[PdxGuiTriggerAllAnimations('rq_top_{x}_{k}')]\"\n"
                       f"{ind}\t\ton_start = \"[PdxGuiTriggerAllAnimations('rq_tail')]\"\n"
                       f"{ind}\t\tnext = rq_after\n{ind}\t}}\n")
    tail_ind = ind + "\t\t\t\t"
    return (
        "\t\t\t\t\t# RQ probe: one controller (outside every datamodel, so it fires\n"
        "\t\t\t\t\t# once) and a hidden copy of the overflow list, so the techs\n"
        "\t\t\t\t\t# beyond the shown ones exist as widgets and can be re-queued.\n"
        "\t\t\t\t\twidget = {\n"
        "\t\t\t\t\t\tsize = { 1 1 }\n\n"
        f"{ind}widget = {{\n{ind}\tname = \"rq_controller\"\n{ind}\tsize = {{ 1 1 }}\n"
        f"{ind}\tstate = {{ name = rq_noop  duration = 0  alpha = 1\n"
        f"{ind}\t\ton_start = \"[GetScriptedGui('rq_probe_drop_noop').Execute({ROOT_ONLY})]\"\n{ind}\t}}\n"
        + "".join(gos) +
        f"{ind}\t# A second later, after the commands ran: dump the queue again.\n"
        f"{ind}\tstate = {{ name = rq_after  duration = 1  alpha = 1\n"
        f"{ind}\t\ton_finish = \"[GetScriptedGui('rq_probe_after').Execute({ROOT_ONLY})]\"\n"
        f"{ind}\t\ton_finish = \"[PdxGuiTriggerAllAnimations('rq_dump')]\"\n{ind}\t}}\n"
        f"{ind}}}\n\n"
        f"{ind}flowcontainer = {{\n{ind}\tdirection = vertical\n"
        f"{ind}\tdatamodel = \"[AccessPlayer.GetResearchQueueBottom]\"\n\n"
        f"{ind}\titem = {{\n{ind}\t\twidget = {{\n{ind}\t\t\tsize = {{ 1 1 }}\n"
        f"{tail_ind}state = {{ name = rq_tail  duration = 0  alpha = 1\n"
        + send_back(tail_ind + "\t", "rq_probe_fire_tail") +
        f"{tail_ind}}}\n"
        + dump_parts(tail_ind) +
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
            "# gui/tech_tree.gui. Do not edit by hand: change the generator and re-run.\n"
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
    for p in range(1, DUMP_MAX + 1):
        out.append(sgui(f"rq_probe_pos_{p}", f"RQ_PROBE|pos|{p}|{name}", True))
    out.append(sgui("rq_probe_pos_over", f"RQ_PROBE|pos|over|{name}", True))
    for x in range(1, n + 1):
        for k in range(1, n + 1):
            if x != k:
                out.append(sgui(f"rq_probe_drop_{x}_{k}", f"RQ_PROBE|drop|{x}|{k}", False))
    out.append(sgui("rq_probe_drop_noop", "RQ_PROBE|drop|noop", False))
    out.append(sgui("rq_probe_after", "RQ_PROBE|after", False))
    for ev in ("fire_top", "fire_tail", "now", "back"):
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
