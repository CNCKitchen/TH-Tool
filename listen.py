"""Passive HID listen: open the LOG_TRH HID interface and read input reports
for 5 seconds. We do NOT write anything. Goal: see if the device sends data
spontaneously on connect, and learn the input report size."""
import hid, time, sys

VID, PID = 0x2047, 0x0301
PATH = None
for d in hid.enumerate(VID, PID):
    PATH = d["path"]
    print(f"Found {d['manufacturer_string']} / {d['product_string']}  "
          f"usage_page=0x{d['usage_page']:04x}")
    break
if PATH is None:
    sys.exit("Device not found")

dev = hid.device()
dev.open_path(PATH)
print("Opened. Listening passively for 5 s...")
dev.set_nonblocking(True)
end = time.time() + 5.0
got = 0
while time.time() < end:
    data = dev.read(64, timeout_ms=200)
    if data:
        got += 1
        print(f"  [{got}] {len(data):3d} bytes: {bytes(data).hex(' ')}")
print(f"Done. {got} report(s) received passively.")
dev.close()
