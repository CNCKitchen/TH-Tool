"""Read the HID report descriptor and Windows preparsed sizes for the logger."""
import hid, ctypes, sys
from ctypes import wintypes

VID, PID = 0x2047, 0x0301

# 1) Try cython-hidapi's get_report_descriptor if available
def via_hidapi():
    for d in hid.enumerate(VID, PID):
        h = hid.device()
        h.open_path(d["path"])
        for fn in ("get_report_descriptor", "get_input_report_byte_length",
                   "get_output_report_byte_length", "get_feature_report_byte_length"):
            f = getattr(h, fn, None)
            if f:
                try:
                    print(f"hidapi.{fn}() ->", f() if "byte_length" in fn else f().hex(' '))
                except Exception as e:
                    print(f"hidapi.{fn}() ERROR: {e}")
            else:
                print(f"hidapi.{fn}: not exposed")
        h.close()
        return d["path"]
    return None

path = via_hidapi()
if not path:
    sys.exit("device not found")

# 2) Use Win32 hid.dll directly to query HIDP_CAPS (authoritative report sizes)
hid_dll = ctypes.WinDLL("hid")
setupapi = ctypes.WinDLL("setupapi")  # not strictly needed
kernel32 = ctypes.WinDLL("kernel32")

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

CloseHandle = kernel32.CloseHandle

class HIDP_CAPS(ctypes.Structure):
    _fields_ = [
        ("Usage", ctypes.c_ushort),
        ("UsagePage", ctypes.c_ushort),
        ("InputReportByteLength", ctypes.c_ushort),
        ("OutputReportByteLength", ctypes.c_ushort),
        ("FeatureReportByteLength", ctypes.c_ushort),
        ("Reserved", ctypes.c_ushort * 17),
        ("NumberLinkCollectionNodes", ctypes.c_ushort),
        ("NumberInputButtonCaps", ctypes.c_ushort),
        ("NumberInputValueCaps", ctypes.c_ushort),
        ("NumberInputDataIndices", ctypes.c_ushort),
        ("NumberOutputButtonCaps", ctypes.c_ushort),
        ("NumberOutputValueCaps", ctypes.c_ushort),
        ("NumberOutputDataIndices", ctypes.c_ushort),
        ("NumberFeatureButtonCaps", ctypes.c_ushort),
        ("NumberFeatureValueCaps", ctypes.c_ushort),
        ("NumberFeatureDataIndices", ctypes.c_ushort),
    ]

# Open handle to the HID device
dev_path = path.decode() if isinstance(path, bytes) else path
print(f"\nOpening {dev_path}")
h = CreateFileW(dev_path, GENERIC_READ | GENERIC_WRITE,
                FILE_SHARE_READ | FILE_SHARE_WRITE, None, OPEN_EXISTING, 0, None)
if h == INVALID_HANDLE_VALUE or h == 0:
    sys.exit(f"CreateFileW failed: {ctypes.get_last_error()}")

PHIDP_PREPARSED_DATA = ctypes.c_void_p
prep = PHIDP_PREPARSED_DATA()
ok = hid_dll.HidD_GetPreparsedData(h, ctypes.byref(prep))
print(f"HidD_GetPreparsedData: {ok}, prep={prep.value}")

caps = HIDP_CAPS()
res = hid_dll.HidP_GetCaps(prep, ctypes.byref(caps))
print(f"HidP_GetCaps: 0x{res & 0xFFFFFFFF:08x}")
print(f"  UsagePage:               0x{caps.UsagePage:04x}")
print(f"  Usage:                   0x{caps.Usage:04x}")
print(f"  InputReportByteLength:   {caps.InputReportByteLength}")
print(f"  OutputReportByteLength:  {caps.OutputReportByteLength}")
print(f"  FeatureReportByteLength: {caps.FeatureReportByteLength}")
print(f"  NumberInputValueCaps:    {caps.NumberInputValueCaps}")
print(f"  NumberOutputValueCaps:   {caps.NumberOutputValueCaps}")
print(f"  NumberFeatureValueCaps:  {caps.NumberFeatureValueCaps}")

# Get raw report descriptor too
buf = (ctypes.c_ubyte * 4096)()
descr_len = ctypes.c_ulong(0)
# HidD_GetReportDescriptor only available on Win11+; older systems use _HidD_GetReportDescriptor via undocumented
fn = getattr(hid_dll, "HidD_GetReportDescriptor", None)
if fn:
    fn.argtypes = [wintypes.HANDLE, ctypes.POINTER(ctypes.c_ubyte), wintypes.ULONG]
    fn.restype = wintypes.BOOL
    ok = fn(h, buf, 4096)
    print(f"\nHidD_GetReportDescriptor: {ok}")
    # We don't know exact length from the API; print first 256 bytes
    raw = bytes(buf)[:256]
    print(f"  first 256B: {raw.hex(' ')}")

hid_dll.HidD_FreePreparsedData(prep)
CloseHandle(h)
