"""Probe 7 (READ-ONLY) — try the two read-only Elitech commands using
both interrupt OUT (WriteFile via hidapi) and control SET_REPORT
(HidD_SetOutputReport). Listen for 3 seconds after each."""
import ctypes, hid, time, sys
from ctypes import wintypes
sys.stdout.reconfigure(line_buffering=True)

VID, PID = 0x2047, 0x0301
RID = 0x3F

# Two well-known read-only Elitech commands
CMDS = {
    "INIT     [CC 00 0A 00 D6]": bytes([0xCC, 0x00, 0x0A, 0x00, 0xD6]),
    "DEV_INFO [CC 00 06 00 D2]": bytes([0xCC, 0x00, 0x06, 0x00, 0xD2]),
}

# Win32 setup for HidD_SetOutputReport
hid_dll = ctypes.WinDLL("hid")
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
CreateFileW = kernel32.CreateFileW
CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                        ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD,
                        wintypes.HANDLE]
CreateFileW.restype = wintypes.HANDLE
CloseHandle = kernel32.CloseHandle
HidD_SetOutputReport = hid_dll.HidD_SetOutputReport
HidD_SetOutputReport.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.ULONG]
HidD_SetOutputReport.restype = wintypes.BOOL

GENERIC_RW = 0xC0000000; SHARE_RW = 3; OPEN_EXISTING = 3
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

path = None
for d in hid.enumerate(VID, PID):
    path = d["path"].decode() if isinstance(d["path"], bytes) else d["path"]

def make_report(payload):
    body = payload + b"\x00" * (63 - len(payload))
    return bytes([RID]) + body  # 64 total

def listen_for(hdev, sec):
    hdev.set_nonblocking(True)
    end = time.time() + sec
    out = []
    while time.time() < end:
        r = hdev.read(64, timeout_ms=100)
        if r:
            out.append(bytes(r))
    return out

# We open hidapi for reading throughout. Writing via two paths.
hdev = hid.device()
hdev.open_path(path.encode() if isinstance(path, str) else path)
listen_for(hdev, 0.1)  # flush

for label, cmd in CMDS.items():
    print(f"\n=== {label} ===")

    # Path 1: interrupt OUT (hidapi.write)
    rep = make_report(cmd)
    n = hdev.write(rep)
    err = hdev.error() if n < 0 else ''
    print(f"  [interrupt-OUT]  write={n}  err={err!r}")
    replies = listen_for(hdev, 2.0)
    print(f"  [interrupt-OUT]  replies: {len(replies)}")
    for i, r in enumerate(replies):
        print(f"    [{i}] {len(r)}B: {r.hex(' ')}")

    # Path 2: control SET_REPORT
    h = CreateFileW(path, GENERIC_RW, SHARE_RW, None, OPEN_EXISTING, 0, None)
    buf = (ctypes.c_ubyte * 64).from_buffer_copy(rep)
    ok = HidD_SetOutputReport(h, buf, 64)
    e = ctypes.get_last_error()
    print(f"  [SET_REPORT]     ok={ok}  err=0x{e:x}")
    CloseHandle(h)
    replies = listen_for(hdev, 2.0)
    print(f"  [SET_REPORT]     replies: {len(replies)}")
    for i, r in enumerate(replies):
        print(f"    [{i}] {len(r)}B: {r.hex(' ')}")

hdev.close()
