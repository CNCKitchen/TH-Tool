"""Enumerate HID devices and locate the LOG_TRH vendor interface."""
import hid

VID, PID = 0x2047, 0x0301

print(f"Looking for VID=0x{VID:04x} PID=0x{PID:04x}\n")
matches = []
for d in hid.enumerate():
    if d["vendor_id"] == VID and d["product_id"] == PID:
        matches.append(d)
        for k, v in d.items():
            print(f"  {k}: {v!r}")
        print("-" * 60)

if not matches:
    print("No matches in hid.enumerate(). Trying full dump for diagnostic:")
    for d in hid.enumerate():
        print(f"  {d['vendor_id']:04x}:{d['product_id']:04x}  "
              f"usage_page=0x{d['usage_page']:04x} usage=0x{d['usage']:04x}  "
              f"path={d['path']!r}")
