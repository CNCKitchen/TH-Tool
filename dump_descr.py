"""Dump the raw HID report descriptor and parse top-level item types."""
import ctypes, sys
from ctypes import wintypes
sys.stdout.reconfigure(line_buffering=True)

VID, PID = 0x2047, 0x0301

hid_dll = ctypes.WinDLL("hid")
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

CreateFileW = kernel32.CreateFileW
CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                        ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD,
                        wintypes.HANDLE]
CreateFileW.restype = wintypes.HANDLE
CloseHandle = kernel32.CloseHandle

GENERIC_RW = 0xC0000000
SHARE_RW = 3
OPEN_EXISTING = 3
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

import hid as hidlib
path = None
for d in hidlib.enumerate(VID, PID):
    path = d["path"].decode() if isinstance(d["path"], bytes) else d["path"]

h = CreateFileW(path, GENERIC_RW, SHARE_RW, None, OPEN_EXISTING, 0, None)
if h == INVALID_HANDLE_VALUE or not h:
    sys.exit(f"CreateFileW: {ctypes.get_last_error()}")

# Cython-hidapi exposes get_report_descriptor
hdev = hidlib.device()
hdev.open_path(path.encode() if isinstance(path, str) else path)
descr2 = bytes(hdev.get_report_descriptor())
hdev.close()
print(f"hidapi descr length: {len(descr2)}")
print(f"hidapi descr bytes:  {descr2.hex(' ')}")

CloseHandle(h)

# Parse the report descriptor
USAGE_PAGE = {0x01: "Generic Desktop", 0x07: "Keyboard", 0x09: "Button",
              0xff00: "Vendor 0xFF00"}
ITEM_TYPE = {0: "Main", 1: "Global", 2: "Local", 3: "Reserved"}
MAIN_TAGS = {8: "Input", 9: "Output", 10: "Collection", 11: "Feature",
             12: "End Collection"}
GLOBAL_TAGS = {0: "Usage Page", 1: "Logical Min", 2: "Logical Max",
               3: "Physical Min", 4: "Physical Max", 5: "Unit Exp",
               6: "Unit", 7: "Report Size", 8: "Report ID",
               9: "Report Count", 10: "Push", 11: "Pop"}
LOCAL_TAGS = {0: "Usage", 1: "Usage Min", 2: "Usage Max"}

print("\n--- parsed report descriptor ---")
d = descr2
i = 0
indent = 0
while i < len(d):
    b = d[i]
    if b == 0xFE:  # long item, rare
        size = d[i+1]; i += 3 + size; continue
    short_size = b & 0x03
    if short_size == 3: short_size = 4
    typ = (b >> 2) & 0x03
    tag = (b >> 4) & 0x0F
    data = d[i+1:i+1+short_size]
    val = int.from_bytes(data, "little") if short_size else 0
    name = "?"
    if typ == 0: name = MAIN_TAGS.get(tag, f"Main {tag}")
    elif typ == 1: name = GLOBAL_TAGS.get(tag, f"Global {tag}")
    elif typ == 2: name = LOCAL_TAGS.get(tag, f"Local {tag}")
    if name == "End Collection":
        indent = max(0, indent - 1)
    extra = ""
    if typ == 1 and tag == 0:
        extra = f"  ({USAGE_PAGE.get(val, hex(val))})"
    print(f"  {'  '*indent}{name:<14} = 0x{val:x}{extra}")
    if name == "Collection":
        indent += 1
    i += 1 + short_size
