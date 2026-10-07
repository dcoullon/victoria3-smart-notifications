Beta 1.14.5 ("Ice Tea") snapshot, captured 2026-10-07
====================================================

Damien switched to the open beta, launched with -debug_mode and ran
`dump_data_types` and `script_docs`, with all three mods (Workshop copies)
enabled. Captured here: the two dumps (data_types/, script_docs/) and the
session's error.log and debug.log. The beta's text folders (common, events,
gui, localization; 159 MB) are outside the repo, at
C:/Users/damie/v3_snapshots/1.14.5/game, for running our checks against.

Findings from this session:
- Smart Treaties: no errors; card figures, treaty net, outliner and treasury
  line all showed (Damien's screenshots 2026-10-07 10:03-10:07).
- Build All: no errors.
- Smart Notifications: breaks on 1.14. Its full override of
  common/messages/00_messages.txt is forked from 1.13 (187 messages); 1.14's
  has 192. Vanilla on_actions then post messages that no longer exist:
  diplo_play_overlord_protects_subject_notification,
  diplo_play_subject_backstab_overlord_notification, wargoal_enforced
  (00_code_on_actions.txt:4331, 4385, 6275), plus "Failed to cache an item
  for Message Type" for strait_restricted and strait_eased. Those
  notifications silently stop firing for SN users on 1.14. Re-fork
  00_messages.txt from 1.14 on patch day.
- Not ours: missing texture gfx/interface/icons/alert_icons/repairing.dds
  is referenced by vanilla's own gui/texticons.gui.
