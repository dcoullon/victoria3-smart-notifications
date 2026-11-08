"""Where Victoria 3 keeps its per-user folder (logs, mod/, settings).

The game writes to the Windows *Documents* known folder, which is not always
``~/Documents``: OneDrive's "back up Documents" redirects it to
``~/OneDrive/Documents`` (it did exactly that on the 2026-11 clean Windows
install). Hardcoding ``Path.home() / "Documents"`` then points every tool at an
empty folder -- scan_logs reports no errors, package_release writes somewhere
the launcher never looks -- without failing. So ask Windows instead.

Override with the ``VIC3_USER_DIR`` environment variable if ever needed.
"""

import os
import sys
from pathlib import Path

# FOLDERID_Documents
_DOCUMENTS_GUID = "{FDD39AD0-238F-46AF-ADB4-6C85480369C7}"


def documents_dir() -> Path:
    """The real Documents folder, as Windows resolves it (OneDrive-aware)."""
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes
            import uuid

            class GUID(ctypes.Structure):
                _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD),
                            ("Data3", wintypes.WORD), ("Data4", ctypes.c_ubyte * 8)]

            u = uuid.UUID(_DOCUMENTS_GUID)
            guid = GUID(u.time_low, u.time_mid, u.time_hi_version,
                        (ctypes.c_ubyte * 8)(*u.bytes[8:]))
            out = ctypes.c_wchar_p()
            shell32 = ctypes.windll.shell32
            if shell32.SHGetKnownFolderPath(ctypes.byref(guid), 0, None,
                                            ctypes.byref(out)) == 0:
                try:
                    return Path(out.value)
                finally:
                    ctypes.windll.ole32.CoTaskMemFree(out)
        except Exception:
            pass
    return Path.home() / "Documents"


def vic3_user_dir() -> Path:
    override = os.environ.get("VIC3_USER_DIR")
    if override:
        return Path(override)
    return documents_dir() / "Paradox Interactive" / "Victoria 3"


VIC3_USER_DIR = vic3_user_dir()

if __name__ == "__main__":
    print(VIC3_USER_DIR)
