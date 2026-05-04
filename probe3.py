"""Probe 4 (READ-ONLY) — bypass hidapi, use Win32 directly to send the
Elitech 'device info' query and read responses. Tries both WriteFile
and HidD_SetOutputReport with a 64-byte buffer (report id 0 + 63 payload)."""
import ctypes, sys, time
from ctypes import wintypes
sys.stdout.reconfigure(line_buffering=True)

VID, PID = 0x2047, 0x0301
APP = bytes([0xCC, 0x00, 0x06, 0x00, 0xD2])

# --- Win32 prototypes ---
hid_dll = ctypes.WinDLL("hid")
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

GENERIC_READ  = 0x80000000
GENERIC_WRITE = 0x40000000
FILE_SHARE_READ  = 1
FILE_SHARE_WRITE = 2
OPEN_EXISTING = 3
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

CreateFileW = kernel32.CreateFileW
CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                        ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD,
                        wintypes.HANDLE]
CreateFileW.restype = wintypes.HANDLE

WriteFile = kernel32.WriteFile
WriteFile.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD,
                      ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
WriteFile.restype = wintypes.BOOL

ReadFile = kernel32.ReadFile
ReadFile.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD,
                     ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
ReadFile.restype = wintypes.BOOL

CloseHandle = kernel32.CloseHandle

HidD_SetOutputReport = hid_dll.HidD_SetOutputReport
HidD_SetOutputReport.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.ULONG]
HidD_SetOutputReport.restype = wintypes.BOOL

import hid as hidlib
path = None
for d in hidlib.enumerate(VID, PID):
    path = d["path"].decode() if isinstance(d["path"], bytes) else d["path"]
print(f"Path: {path}")

h = CreateFileW(path, GENERIC_READ | GENERIC_WRITE,
                FILE_SHARE_READ | FILE_SHARE_WRITE, None, OPEN_EXISTING, 0, None)
if h == INVALID_HANDLE_VALUE or not h:
    sys.exit(f"CreateFileW failed: {ctypes.get_last_error()}")
print(f"Handle: {h}")

# Build 64-byte report: report id 0 + payload + zero pad
report = bytes([0]) + APP + b"\x00" * (64 - 1 - len(APP))
assert len(report) == 64
buf = (ctypes.c_ubyte * 64).from_buffer_copy(report)

# Try 1: WriteFile
written = wintypes.DWORD(0)
ok = WriteFile(h, buf, 64, ctypes.byref(written), None)
err = ctypes.get_last_error()
print(f"\nWriteFile -> ok={ok} written={written.value} GetLastError=0x{err:x}")

# Try 2: HidD_SetOutputReport
ok = HidD_SetOutputReport(h, buf, 64)
err = ctypes.get_last_error()
print(f"HidD_SetOutputReport -> ok={ok} GetLastError=0x{err:x}")

# If both writes failed, there's no point waiting for a reply.
# Use hidapi for the read part since it has timeouts; reopen via hidlib.
CloseHandle(h)
print("\nReopening with hidapi for non-blocking read...")
hdev = hidlib.device()
hdev.open_path(path.encode() if isinstance(path, str) else path)
hdev.set_nonblocking(True)
end = time.time() + 1.5
got = 0
while time.time() < end:
    r = hdev.read(64, timeout_ms=100)
    if r:
        got += 1
        b = bytes(r)
        print(f"  reply[{got}] {len(b)}B: {b.hex(' ')}")
        txt = ''.join(chr(c) if 32 <= c < 127 else '.' for c in b)
        print(f"             ascii: {txt}")
print(f"  total replies: {got}")
hdev.close()
