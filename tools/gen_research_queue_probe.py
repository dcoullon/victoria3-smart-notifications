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
result. The dragged tech's name is recorded when the drag starts (each drag
overwrites it, nothing clears it); the drop handler refuses the move if it
does not match the dropped tech, so a stale name can only cancel a move. The
controller sits before the queue row in the tree and the hidden overflow
list after it, so one pass sends the shown techs back before the overflow.

Drop zones: each shown tech has a gap on its left ("insert before me"), its
icon means "before it" when moving left and "after it" when moving right,
and a zone right of the row means "after the last shown tech". A drag out
of the "+N" pop-up never reaches a drop target (run 3), so the pop-up's
techs get a button instead (in the vanilla type queued_technology,
redefined here) that moves them to the front of the queue.

Dropping on the current research's icon is the move "up to slot 0": the
current research is the queue's head (vanilla's X on it is RemoveFromQueue),
so the dragged tech and its queued prerequisites stay and everything else,
the old current research first, goes to the back. The drop target is the
current research's icon, but the old current research is sent back from a
widget inside the controller (whose datacontext is the current research,
like the whole hbox): the icon sits BEFORE the controller in the tree, where
a triggered state would run on the next pass, after the row's commands.

A drop that will not land the dragged tech on the slot it was dropped on
shows a short message at once (run 4: the user expected a word when a tech
dropped on its own prerequisite lands just behind it, and found a check
after the move too slow). It is known at drop time, from the queue before
the move: up to f, a prerequisite of the tech at position >= f stays ahead
of it; down to f, a dependent (or another mod's tech) between the two slots
travels with it. Each such tech, in its own rq_mv_ state, fires the message.
Drops are refused for CHECK_AFTER seconds after one (run 4's two drops less
than a second apart left a tech ahead of its own prerequisite).

Two builds. The default is the release build: no logging, nothing extra on
screen, and no scripted GUI file at all (packaging strips debug_log lines,
which would leave empty scripted GUIs wired to every drop). --probe adds the
instrumentation: RQ_PROBE| lines for every drop, a queue dump before and
after, a progress readout under each tech, read back by
tools/rq_probe_report.py (docs/research-queue-investigation.md). The
committed files are always the release build; --check compares against it.

Usage:
    python tools/gen_research_queue_probe.py            write the release build
    python tools/gen_research_queue_probe.py --probe    write the probe build (dev only)
    python tools/gen_research_queue_probe.py --check    exit 1 unless the release build is current
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
IS_X = f"EqualTo_string({NAME}, {XNAME})"
PRE_OF_X = f"GetVariableSystem.Exists(Concatenate3({NAME}, '>', {XNAME}))"
DEP_OF_X = f"GetVariableSystem.Exists(Concatenate3({XNAME}, '>', {NAME}))"
# In the prerequisite table, i.e. a tech of the game's own files at generation
# time. Techs added by other mods are not, and are handled conservatively.
KNOWN = f"GetVariableSystem.Exists(Concatenate('rq_known_', {NAME}))"
KNOWN_DRAGGED = f"GetVariableSystem.Exists(Concatenate('rq_known_', {DRAGGED}.GetNameNoFormatting))"
BUSY = "GetVariableSystem.Exists('rq_busy')"
CHECK_AFTER = 0.4  # s during which further drops are refused after one
ROOT_ONLY = "GuiScope.SetRoot(GetPlayer.MakeScope).End"
ROOT_TECH = "GuiScope.SetRoot(GetPlayer.MakeScope).AddScope('t', Technology.MakeScope).End"
BOM = "﻿"
PROBE = False  # set by --probe in main()


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
        for m in re.finditer(r"^([\w\-]+)\s*=\s*\{", text, re.M):  # vanilla has pan-nationalism
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


def known_techs() -> list[str]:
    """Every tech the game's own files define, with or without prerequisites."""
    keys = set()
    for f in sorted(TECH_DIR.glob("*.txt")):
        text = re.sub(r"#[^\n]*", "", f.read_text(encoding="utf-8-sig"))
        keys |= set(re.findall(r"^([\w\-]+)\s*=\s*\{", text, re.M))
    return sorted(keys)


def i32(n: int) -> str:
    return f"'(int32){n}'"


def ladder(cases: list[tuple[str, str]], default: str) -> str:
    expr = f"'{default}'"
    for cond, name in reversed(cases):
        expr = f"Select_CString({cond}, '{name}', {expr})"
    return expr


def moves(n: int) -> list[tuple[str, int | None, int]]:
    """Every move as (direction, from, to). An up move does not depend on
    where the tech came from, so `from` is None; a down move does (unknown
    techs between the two slots travel with it)."""
    return ([("up", None, f) for f in range(0, n + 1)]
            + [("down", x, f) for f in range(2, n + 1) for x in range(1, f)])


def mkey(d: str, x: int | None, f: int) -> str:
    return f"up_{f}" if d == "up" else f"down_{x}_{f}"


def guarded(cases: list[tuple[str, str]]) -> str:
    """A drop expression: refuse while the previous move is settling, and
    unless the name recorded at drag start is the dropped tech's."""
    match = f"EqualTo_string({DRAGGED}.GetNameNoFormatting, {XNAME})"
    return f"Select_CString({BUSY}, 'rq_busyx', Select_CString({match}, {ladder(cases, 'rq_noop')}, 'rq_badx'))"


def at(k: int, cond: str) -> str:
    return f"And(EqualTo_int32({POS}, {i32(k)}), {cond})"


def up_to(k: int) -> str:
    """Moving up needs the dragged tech in the prerequisite table: an unknown
    tech's prerequisites would be sent behind it, and the cascade on removal
    would take the tech out of the queue (simulated with modded techs)."""
    return f"And(GreaterThan_int32({DRAGGED_POS}, {i32(k)}), {KNOWN_DRAGGED})"


def down_from(x: int) -> str:
    return f"EqualTo_int32({DRAGGED_POS}, {i32(x)})"


def icon_drop(n: int) -> str:
    cases = []
    for k in range(1, n + 1):
        cases.append((at(k, up_to(k)), f"rq_go_up_{k}"))
        cases += [(at(k, down_from(x)), f"rq_go_down_{x}_{k}") for x in range(1, k)]
    return guarded(cases)


def gap_drop(n: int) -> str:
    cases = []
    for k in range(1, n + 1):
        cases.append((at(k, up_to(k)), f"rq_go_up_{k}"))
        cases += [(at(k, down_from(x)), f"rq_go_down_{x}_{k - 1}") for x in range(1, k - 1)]
    return guarded(cases)


def end_drop(n: int) -> str:
    return guarded([(down_from(x), f"rq_go_down_{x}_{n}") for x in range(1, n)])


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


def log_line(ind: str, sgui_name: str, root: str = ROOT_TECH, event: str = "on_start") -> str:
    """A probe logging call; nothing in a release build."""
    return f"{ind}{event} = \"[GetScriptedGui('{sgui_name}').Execute({root})]\"\n" if PROBE else ""


def mover_parts(ind: str, log: str, member: dict, blocker: dict | None = None) -> str:
    """One rq_mv_<move> state per move, each gating this tech into the
    send-back set, plus the gates. `member` maps a move key (mkey) to a
    condition, or to None for "always". `blocker` maps a move key to the
    condition under which this tech keeps the dragged one off its slot, which
    shows the message."""
    states = []
    for key, cond in member.items():
        bc = (blocker or {}).get(key)
        warn = (f"{ind}\ton_start = \"[PdxGuiTriggerAllAnimations(Select_CString({bc}, "
                f"'rq_nomove_show', 'rq_none'))]\"\n") if bc else ""
        pick = "'rq_do'" if cond is None else f"Select_CString({cond}, 'rq_do', 'rq_skip')"
        xlog = (f"{ind}\ton_start = \"[PdxGuiWidget.FindChild('rq_xgate').TriggerAnimation("
                f"Select_CString({IS_X}, 'rq_xlog', 'rq_skip'))]\"\n") if PROBE else ""
        states.append(f"{ind}state = {{ name = rq_mv_{key}  duration = 0  alpha = 1\n"
                      + xlog + warn +
                      f"{ind}\ton_start = \"[PdxGuiWidget.FindChild('rq_gate').TriggerAnimation({pick})]\"\n"
                      f"{ind}}}\n")
    xgate = (f"{ind}widget = {{\n{ind}\tname = \"rq_xgate\"\n{ind}\tsize = {{ 1 1 }}\n"
             f"{ind}\tstate = {{ name = rq_skip  duration = 0  alpha = 1 }}\n"
             f"{ind}\tstate = {{ name = rq_xlog  duration = 0  alpha = 1\n"
             + log_line(ind + "\t\t", "rq_probe_x") +
             f"{ind}\t}}\n{ind}}}\n") if PROBE else ""
    return ("".join(states) +
            f"{ind}widget = {{\n{ind}\tname = \"rq_gate\"\n{ind}\tsize = {{ 1 1 }}\n"
            f"{ind}\tstate = {{ name = rq_skip  duration = 0  alpha = 1 }}\n"
            f"{ind}\tstate = {{ name = rq_do  duration = 0  alpha = 1\n"
            + log_line(ind + "\t\t", log) +
            f"{ind}\t\ton_start = \"[Execute(Technology.RemoveFromQueue({PLAYER}))]\"\n"
            f"{ind}\t\ton_start = \"[Execute(Technology.AddToQueueWithUnlocks({PLAYER}))]\"\n"
            f"{ind}\t}}\n{ind}}}\n"
            + xgate)


def row_member(d: str, x: int | None, f: int):
    if d == "up":
        # Slot 0 is the current research, whose row item vanilla hides; the
        # current research's own icon sends it back (current_research_parts).
        return f"And(GreaterThan_int32({POS}, {i32(max(f, 1) - 1)}), Not(Or({IS_X}, {PRE_OF_X})))"
    # Down: a tech between the two slots goes with X if it depends on X, or if
    # the table does not know it (another mod's tech, possibly requiring X;
    # left behind, the cascade on X's removal would take it out of the queue).
    between = f"And(GreaterThan_int32({POS}, {i32(x)}), Or({DEP_OF_X}, Not({KNOWN})))"
    return f"Or({IS_X}, Or(GreaterThan_int32({POS}, {i32(f)}), {between}))"


def row_blocker(d: str, x: int | None, f: int):
    """This tech keeps the dragged one off slot f: up, a prerequisite of it at
    position >= f stays ahead of it; down, a tech between the two slots that
    travels with it (row_member's `between`) lands behind it."""
    if d == "up":
        return f"And(GreaterThan_int32({POS}, {i32(f - 1)}), {PRE_OF_X})"
    return (f"And(And(GreaterThan_int32({POS}, {i32(x)}), Not(GreaterThan_int32({POS}, {i32(f)}))), "
            f"Or({DEP_OF_X}, Not({KNOWN})))")


def tail_member(d: str, x: int | None, f: int):
    # Overflow techs sit beyond every slot f; on a down move all of them go.
    return f"Not(Or({IS_X}, {PRE_OF_X}))" if d == "up" else None


def drop_target(ind: str, expr: str) -> str:
    return (f"{ind}drop_target = {{\n"
            f"{ind}\taccept_draggable_id = \"rq_tech\"\n"
            f"{ind}\ton_receive_drop = \"[PdxGuiTriggerAllAnimations({expr})]\"\n"
            f"{ind}}}\n")


def drag_block(ind: str) -> str:
    """The drag (vanilla pattern: construction_queue.gui:354). The drag widget
    records the dragged tech's name when it is created (run 3: one line per
    drag); the drop refuses the move unless the name matches the dropped tech."""
    lines = [
        "draggable_behavior = {",
        "\tdraggable_id = \"rq_tech\"",
        "\tdrag_widget = {",
        "\t\twidget = {",
        "\t\t\tsize = { 1 1 }",
        "\t\t\twidget = {",
        "\t\t\t\tposition = \"[GuiCurrentDrag.CurrentPosition]\"",
        "\t\t\t\twidgetanchor = center",
        f"\t\t\t\tsize = {{ {ICON} {ICON} }}",
        "\t\t\t\talpha = 0.7",
        "\t\t\t\tstate = { name = rq_dragstart  trigger_on_create = yes  duration = 0  alpha = 0.7",
        f"\t\t\t\t\ton_start = \"[GetVariableSystem.Set('rq_xname', {NAME})]\"",
    ] + ([f"\t\t\t\t\ton_start = \"[GetScriptedGui('rq_probe_dragstart').Execute({ROOT_TECH})]\""]
         if PROBE else []) + [
        "\t\t\t\t}",
        "\t\t\t\ticon = {",
        "\t\t\t\t\ttexture = \"gfx/interface/backgrounds/round_frame_dec.dds\"",
        "\t\t\t\t\tparentanchor = center",
        f"\t\t\t\t\tsize = {{ {ICON} {ICON} }}",
        "\t\t\t\t}",
        "\t\t\t\ticon = {",
        "\t\t\t\t\tparentanchor = center",
        "\t\t\t\t\tsize = { 60 60 }",
        "\t\t\t\t\ttexture = \"[Technology.GetTexture]\"",
        "\t\t\t\t}",
        "\t\t\t}",
        "\t\t}",
        "\t}",
        "}",
    ]
    return "".join(f"{ind}{line}\n" for line in lines)


def queued_technology_type(n: int) -> str:
    """Vanilla's type queued_technology plus a button shown only in the "+N"
    pop-up (position > n). Run 3: a drag out of the pop-up never reached a
    drop target (three drag starts, no drop line, nothing in error.log), so a
    click moves the tech to the front of the queue instead, its queued
    prerequisites just ahead of it. Clicks work in the pop-up: vanilla's X
    does. Not "to the row's last slot": a move up keeps the tech's queued
    prerequisites in front of it, so with one of them also in the pop-up the
    prerequisite took the slot and the tech stayed hidden (review,
    2026-11-15)."""
    text = VANILLA_GUI.read_text(encoding="utf-8-sig")
    start = text.index("\ttype queued_technology = ")
    body = text[start:block_at(text, start)]
    if not body.startswith("\ttype queued_technology = widget {") or not body.endswith("\n\t}"):
        sys.exit("FAIL: vanilla type queued_technology changed shape; re-read tech_tree.gui")
    button = (
        "\n\t\t# RQ: in the \"+N\" pop-up only, move this tech to the front of the queue.\n"
        "\t\tbutton_icon_move_left = {\n"
        f"\t\t\tvisible = \"[GreaterThan_int32({POS}, {i32(n)})]\"\n"
        "\t\t\tparentanchor = bottom|left\n"
        "\t\t\tsize = { 25 25 }\n"
        "\t\t\ttooltip = \"RQ_MOVE_TO_ROW_TOOLTIP\"\n"
        f"\t\t\tonclick = \"[GetVariableSystem.Set('rq_xname', {NAME})]\"\n"
        # Refused for a tech the prerequisite table does not know (see up_to).
        f"\t\t\tonclick = \"[PdxGuiTriggerAllAnimations(Select_CString({BUSY}, 'rq_busyx', "
        f"Select_CString({KNOWN}, 'rq_go_up_1', 'rq_noop')))]\"\n"
        "\t\t}\n"
    )
    return body[:-2] + button + "\t}"


def controller_current() -> str:
    """Inside the controller, so after it in the tree and before the row: the
    current research (the hbox's datacontext) is sent back on a drop on it,
    unless the dragged tech needs it. Probe: dumps it as queue position 0."""
    ind = "\t\t\t\t\t\t"
    dump = (f"{ind}\tstate = {{ name = rq_dump  duration = 0  alpha = 1\n"
            + log_line(ind + "\t\t", "rq_probe_pos_0") + f"{ind}\t}}\n") if PROBE else ""
    return (f"{ind}# The current research, sent back first on a drop on it.\n"
            f"{ind}widget = {{\n{ind}\tsize = {{ 1 1 }}\n"
            + mover_parts(ind + "\t", "rq_probe_fire_top", {"up_0": f"Not({PRE_OF_X})"}, {"up_0": PRE_OF_X})
            + dump + f"{ind}}}\n")


def controller(n: int) -> str:
    ind = "\t\t\t\t\t\t"
    gos = []
    for d, x, f in moves(n):
        key = mkey(d, x, f)
        gos.append(f"{ind}state = {{ name = rq_go_{key}  duration = 0  alpha = 1\n"
                   + log_line(ind + "\t", f"rq_probe_drop_{key}", ROOT_ONLY)
                   + f"{ind}\ton_start = \"[GetVariableSystem.Set('rq_busy', 'y')]\"\n"

                   + (f"{ind}\ton_start = \"[PdxGuiTriggerAllAnimations('rq_dump')]\"\n" if PROBE else "") +
                   f"{ind}\ton_start = \"[PdxGuiTriggerAllAnimations('rq_edges')]\"\n"
                   f"{ind}\ton_start = \"[PdxGuiTriggerAllAnimations('rq_mv_{key}')]\"\n"
                   + f"{ind}\tnext = rq_check\n" + f"{ind}}}\n")
    if PROBE:  # a drop that changes nothing, or a refused one, only needs a log line
        for name in ("noop", "badx", "busyx"):
            gos.append(f"{ind}state = {{ name = rq_{name}  duration = 0  alpha = 1\n"
                       + log_line(ind + "\t", f"rq_probe_drop_{name}", ROOT_ONLY) + f"{ind}}}\n")
    lines = [f"{ind}\t\ton_start = \"[GetVariableSystem.Set(Concatenate3(GetTechnology('{p}').GetNameNoFormatting, '>', "
             f"GetTechnology('{t}').GetNameNoFormatting), 'y')]\"\n" for p, t in ancestor_pairs()]
    lines += [f"{ind}\t\ton_start = \"[GetVariableSystem.Set(Concatenate('rq_known_', "
              f"GetTechnology('{k}').GetNameNoFormatting), 'y')]\"\n" for k in known_techs()]
    after = (f"{ind}# Once the commands ran: accept drops again.\n"
             f"{ind}state = {{ name = rq_check  duration = {CHECK_AFTER}  alpha = 1\n"
             f"{ind}\ton_finish = \"[GetVariableSystem.Clear('rq_busy')]\"\n"
             + (f"{ind}\tnext = rq_after\n" if PROBE else "") +
             f"{ind}}}\n"
             f"{ind}# Panel (re)opened: a move cut short by closing it must not block drops.\n"
             f"{ind}state = {{ name = rq_init  trigger_on_create = yes  duration = 0  alpha = 1\n"
             f"{ind}\ton_start = \"[GetVariableSystem.Clear('rq_busy')]\"\n"
             f"{ind}}}\n\n"
             + ((f"{ind}# Probe: a second after the drop, dump the queue again.\n"
                 f"{ind}state = {{ name = rq_after  duration = {round(1 - CHECK_AFTER, 2)}  alpha = 1\n"
                 + log_line(ind + "\t", "rq_probe_after", ROOT_ONLY, "on_finish") +
                 f"{ind}\ton_finish = \"[PdxGuiTriggerAllAnimations('rq_dump')]\"\n"
                 f"{ind}}}\n\n") if PROBE else ""))
    return (
        "# RQ: the controller, BEFORE the queue row in the widget tree, so the\n"
        "\t\t\t\t\t# states it triggers on the row and on the overflow list (after the\n"
        "\t\t\t\t\t# row) run in that order. Outside every datamodel, so it fires once.\n"
        "\t\t\t\t\twidget = {\n"
        "\t\t\t\t\t\tname = \"rq_controller\"\n"
        "\t\t\t\t\t\tsize = { 1 1 }\n"
        + "".join(gos) + after + controller_current() +
        f"{ind}# Every direct or indirect prerequisite pair, \"prerequisite>dependent\"\n"
        f"{ind}# by tech name, from the game's common/technology/technologies at\n"
        f"{ind}# generation time. Built when the panel is created and on every drop.\n"
        f"{ind}widget = {{\n{ind}\tsize = {{ 1 1 }}\n"
        f"{ind}\tstate = {{ name = rq_edges  trigger_on_create = yes  duration = 0  alpha = 1\n"
        + "".join(lines) +
        f"{ind}\t}}\n{ind}}}\n"
        "\t\t\t\t\t}\n\n\t\t\t\t\t"
    )


def probe_row_extras(ind: str) -> str:
    """Probe only: the queue dump, and the research progress readout, shown
    only above 0 (the case that tells whether a move keeps it)."""
    return ("\n" + dump_parts(ind, "pos") + "\n"
            f"{ind}textbox = {{\n"
            f"{ind}\tvisible = \"[GreaterThan_CFixedPoint(Technology.GetProgress(GetPlayer.Self), '(CFixedPoint)0')]\"\n"
            f"{ind}\tparentanchor = bottom|left\n{ind}\tautoresize = yes\n"
            f"{ind}\talign = nobaseline\n"
            f"{ind}\traw_text = \"#v [Technology.GetProgress(GetPlayer.Self)|0]#!\"\n{ind}}}\n")


def row(n: int) -> str:
    ind = "\t\t\t\t\t\t\t\t\t"
    member = {mkey(d, x, f): row_member(d, x, f) for d, x, f in moves(n)}
    return (
        "hbox = {\n"
        "\t\t\t\t\t\tdatamodel = \"[AccessPlayer.GetResearchQueueTop]\"\n"
        # Vanilla: margin 20, then the first icon. The controller before the row
        # adds 1px plus the parent hbox's spacing of 10 (tech_tree.gui:90), and
        # the gap 14, so 0 here puts the first icon 5px right of vanilla's.
        "\t\t\t\t\t\tmargin_left = 0\n\n"
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
        + drag_block(ind) +
        "\t\t\t\t\t\t\t\t\t# RQ: dropped on this icon, moving left lands before it, moving right after it.\n"
        + drop_target(ind, icon_drop(n)) + "\n"
        + mover_parts(ind, "rq_probe_fire_top", member,
                      {mkey(d, x, f): row_blocker(d, x, f) for d, x, f in moves(n)})
        + (probe_row_extras(ind) if PROBE else "") +
        "\t\t\t\t\t\t\t\t}\n"
        "\t\t\t\t\t\t\t}\n"
        "\t\t\t\t\t\t}\n"
        "\t\t\t\t\t}\n\n"
    )


def end_zone_and_tail(n: int) -> str:
    ind = "\t\t\t\t\t\t"
    tail_ind = ind + "\t\t\t"
    member = {mkey(d, x, f): tail_member(d, x, f) for d, x, f in moves(n)}
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
        + mover_parts(tail_ind, "rq_probe_fire_tail", member,
                      {mkey(d, x, f): PRE_OF_X for d, x, f in moves(n) if d == "up"})
        + (dump_parts(tail_ind, "tpos") if PROBE else "") +
        f"{ind}\t\t}}\n{ind}\t}}\n{ind}}}\n"
        "\t\t\t\t\t}"
    )


CUR_ANCHOR = "\t\t\t\t\twidget = {\n\t\t\t\t\t\tsize = { 80 80 }\n"


def current_research_parts() -> str:
    """Inside the current research's icon widget (vanilla's 80x80 one): a
    drop here is the move up to slot 0 (controller_current sends the old
    current research back). Also holds the "not moved" message, under the
    icon and running right under the progress bar."""
    ind = "\t\t\t\t\t\t"
    drop = guarded([(KNOWN_DRAGGED, "rq_go_up_0")])
    return (
        f"{ind}# RQ: dropping a queued tech on the current research makes it the current\n"
        f"{ind}# research (its queued prerequisites first); the old one comes right after.\n"
        f"{ind}alwaystransparent = no\n"
        + drop_target(ind, drop) +
        f"{ind}# RQ: shown for a few seconds when a tech did not land where it was dropped.\n"
        f"{ind}textbox = {{\n"
        f"{ind}\tname = \"rq_nomove\"\n"
        f"{ind}\tposition = {{ 0 82 }}\n"
        f"{ind}\tautoresize = yes\n"
        f"{ind}\talign = left|nobaseline\n"
        f"{ind}\talpha = 0\n"
        f"{ind}\talwaystransparent = yes\n"
        f"{ind}\ttext = \"RQ_PREREQUISITES_FIRST\"\n"
        f"{ind}\tstate = {{ name = rq_nomove_show  duration = 0.15  alpha = 1  next = rq_nomove_hold\n"
        + log_line(ind + "\t\t", "rq_probe_nomove", ROOT_ONLY) +
        f"{ind}\t}}\n"
        f"{ind}\tstate = {{ name = rq_nomove_hold  duration = 4  alpha = 1  next = rq_nomove_hide }}\n"
        f"{ind}\tstate = {{ name = rq_nomove_hide  duration = 0.5  alpha = 0 }}\n"
        f"{ind}}}\n\n"
    )


VANILLA_OVERFLOW_CLICK = "[RightClickMenuManager.ToggleResearchQueue(PdxGuiWidget.AccessSelf)]"


def overflow_row() -> str:
    """The "+N" techs as a second row under the queue, inside the panel, in
    place of vanilla's right-click menu. Runs 3 and 4: a drag out of that menu
    never reached a drop target (drag starts logged, no drop line, nothing in
    error.log). Hypothesis: the menu is its own window on layer
    layer_rightclickmenu (right_click_menu.gui), and a drop target in the
    panel's window cannot receive a drag that started in another window. This
    row is in the panel's window and in the layout flow (fixed_top stacks its
    children vertically), so nothing draws over it. Its techs only carry the
    drag; every move is done by the existing row and overflow-copy members,
    and the row's drops already handle a dragged tech beyond the row (up to f
    is any position above f)."""
    ind = "\t\t\t\t\t\t\t\t\t"
    return (
        "\t\t\t# RQ: the techs beyond the row, shown by \"+N\" here instead of in vanilla's\n"
        "\t\t\t# right-click menu, so they can be dragged onto the row.\n"
        "\t\t\thbox = {\n"
        "\t\t\t\tvisible = \"[And(GetVariableSystem.Exists('rq_ovf'), "
        "Not(IsDataModelEmpty(AccessPlayer.GetResearchQueueBottom)))]\"\n"
        "\t\t\t\tlayoutpolicy_horizontal = growing\n"
        "\t\t\t\tmargin = { 28 0 }\n"
        "\t\t\t\tmargin_bottom = 10\n\n"
        "\t\t\t\tdynamicgridbox = {\n"
        "\t\t\t\t\tdatamodel = \"[AccessPlayer.GetResearchQueueBottom]\"\n"
        "\t\t\t\t\tdatamodel_wrap = 14\n"
        "\t\t\t\t\tflipdirection = yes\n\n"
        "\t\t\t\t\titem = {\n"
        "\t\t\t\t\t\twidget = {\n"
        "\t\t\t\t\t\t\tsize = { 90 90 }\n"
        "\t\t\t\t\t\t\tqueued_technology = {\n"
        "\t\t\t\t\t\t\t\tparentanchor = center\n"
        "\t\t\t\t\t\t\t\talwaystransparent = no\n"
        + drag_block(ind[:-1]) +
        "\t\t\t\t\t\t\t}\n"
        "\t\t\t\t\t\t}\n"
        "\t\t\t\t\t}\n"
        "\t\t\t\t}\n\n"
        "\t\t\t\texpand = {}\n"
        "\t\t\t}\n"
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
    cur = panel.index("### CURRENT RESEARCH")
    if panel.count(CUR_ANCHOR, cur, panel.index("rq_controller")) != 1:
        sys.exit("FAIL: the current research's 80x80 icon widget changed shape; re-read tech_tree.gui")
    c = panel.index(CUR_ANCHOR, cur) + len(CUR_ANCHOR)
    panel = panel[:c] + current_research_parts() + panel[c:]
    # "+N" opens our own overflow row inside the panel instead of vanilla's
    # right-click menu (see overflow_row).
    if panel.count(VANILLA_OVERFLOW_CLICK) != 1:
        sys.exit("FAIL: the \"+N\" button's onclick changed; re-read tech_tree.gui")
    panel = panel.replace(VANILLA_OVERFLOW_CLICK, "[GetVariableSystem.Toggle('rq_ovf')]")
    ft = panel.index('blockoverride "fixed_top" {')
    fh = panel.index("hbox = {", ft)
    fe = block_at(panel, fh)
    panel = panel[:fe] + "\n\n" + overflow_row() + panel[fe:]
    return (BOM +
            "# GENERATED by tools/gen_research_queue_probe.py from the installed game's\n"
            "# gui/tech_tree.gui and common/technology/technologies. Do not edit by hand:\n"
            "# change the generator and re-run.\n"
            + ("# PROBE BUILD: logs RQ_PROBE| lines and shows a progress readout. Never ship;\n"
               "# rerun the generator without --probe for the release build.\n"
               if PROBE else "# Release build (no logging); --probe writes the instrumented one.\n") +
            "# Redefines the vanilla types tech_tree_panel and queued_technology; the 00_\n"
            "# prefix makes this file load before tech_tree.gui, so these definitions win\n"
            "# (docs/engine-notes.md, \"A partial .gui override works\").\n"
            "types research_queue_types\n{\n" + panel + "\n\n" + queued_technology_type(n) + "\n}\n")


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
        for p in range(0 if tag == "pos" else 1, DUMP_MAX + 1):  # pos 0: the current research
            out.append(sgui(f"rq_probe_{tag}_{p}", f"RQ_PROBE|{tag}|{p}|{name}", True))
        out.append(sgui(f"rq_probe_{tag}_over", f"RQ_PROBE|{tag}|over|{name}", True))
    for d, x, f in moves(shown_count()):
        out.append(sgui(f"rq_probe_drop_{mkey(d, x, f)}", f"RQ_PROBE|drop|{d}|{f}", False))
    for ev in ("noop", "badx", "busyx"):
        out.append(sgui(f"rq_probe_drop_{ev}", f"RQ_PROBE|drop|{ev}", False))
    out.append(sgui("rq_probe_after", "RQ_PROBE|after", False))
    out.append(sgui("rq_probe_nomove", "RQ_PROBE|nomove", False))
    for ev in ("fire_top", "fire_tail", "x", "dragstart"):
        out.append(sgui(f"rq_probe_{ev}", f"RQ_PROBE|{ev}|{name}", True))
    return "".join(out)


def main() -> int:
    global PROBE
    check = "--check" in sys.argv[1:]
    PROBE = "--probe" in sys.argv[1:] and not check
    if not VANILLA_GUI.is_file():
        print(f"FAIL: {VANILLA_GUI} not found (game not installed?)")
        return 1
    stale = []
    if not PROBE and OUT_SGUI.exists():
        # The release build has no logging file; a leftover one from a probe
        # build would ship as scripted GUIs nothing calls, or worse.
        if check:
            stale.append(OUT_SGUI)
        else:
            OUT_SGUI.unlink()
            print(f"removed {OUT_SGUI.relative_to(REPO)} (probe only)")
    outputs = [(OUT_GUI, build_gui())] + ([(OUT_SGUI, build_sgui())] if PROBE else [])
    for path, content in outputs:
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
