"""Probe 5 — sweep output buffer sizes 1..72 to find which size the kernel
will actually accept for this HID device. Strictly READ-ONLY at app level:
the only command bytes ever sent are CC 00 06 00 D2 (Elitech device-info)."""
import ctypes, sys, time
from ctypes import wintypes
sys.stdout.reconfigure(line_buffering=True)

VID, PID = 0x2047, 0x0301
APP = bytes([0xCC, 0x00, 0x06, 0x00, 0xD2])

hid_dll = ctypes.WinDLL("hid")
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

CreateFileW = kernel32.CreateFileW
CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                        ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD,
                        wintypes.HANDLE]
CreateFileW.restype = wintypes.HANDLE
CloseHandle = kernel32.CloseHandle

WriteFile = kernel32.WriteFile
WriteFile.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD,
                      ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
WriteFile.restype = wintypes.BOOL

HidD_SetOutputReport = hid_dll.HidD_SetOutputReport
HidD_SetOutputReport.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.ULONG]
HidD_SetOutputReport.restype = wintypes.BOOL

GENERIC_RW = 0xC0000000
SHARE_RW = 3
OPEN_EXISTING = 3
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

import hid as hidlib
path = None
for d in hidlib.enumerate(VID, PID):
    path = d["path"].decode() if isinstance(d["path"], bytes) else d["path"]

def open_h():
    h = CreateFileW(path, GENERIC_RW, SHARE_RW, None, OPEN_EXISTING, 0, None)
    if h == INVALID_HANDLE_VALUE or not h:
        sys.exit(f"CreateFileW: {ctypes.get_last_error()}")
    return h

def make_buf(size, leading_zero=True):
    """Build a buffer of `size` bytes: optional report-id 0, then APP, zero pad."""
    if leading_zero:
        body = b"\x00" + APP + b"\x00" * max(0, size - 1 - len(APP))
    else:
        body = APP + b"\x00" * max(0, size - len(APP))
    body = body[:size]
    return (ctypes.c_ubyte * size).from_buffer_copy(body)

print(f"{'size':>4} {'lead0':>5}  {'WriteFile':>20}  {'HidD_SetOutputReport':>22}")
for size in range(1, 73):
    for leading in (True, False):
        buf = make_buf(size, leading)
        h = open_h()
        wr = wintypes.DWORD(0)
        ok1 = WriteFile(h, buf, size, ctypes.byref(wr), None)
        e1 = ctypes.get_last_error()
        CloseHandle(h)

        h = open_h()
        ok2 = HidD_SetOutputReport(h, buf, size)
        e2 = ctypes.get_last_error()
        CloseHandle(h)

        wf = "OK" if ok1 else f"err 0x{e1:x}"
        sr = "OK" if ok2 else f"err 0x{e2:x}"
        if ok1 or ok2:
            print(f"{size:>4} {str(leading):>5}  {wf:>20}  {sr:>22}  <-- ACCEPTED")
        # only print the OK rows to keep it readable
