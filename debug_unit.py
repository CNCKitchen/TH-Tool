"""Read META, then write with write[20]=1 vs write[11]=1, see which actually
flips the displayed unit."""
import sys, time
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, r"c:\Users\stefa\Desktop\TH-Tool")
from trh import (open_dev, request, read_until_idle, RID, get_meta, parse_meta,
                 write_settings, get_name, write_name, encode_time)
import datetime

h = open_dev()
read_until_idle(h, idle_ms=80, max_ms=200)

raw = get_meta(h)
print("META payload (31B):")
for i, b in enumerate(raw):
    print(f"  [{i:2d}] 0x{b:02x}  ({b})")
print(f"\nparse_meta says unit byte = read[13] = 0x{raw[13]:02x}")
print(f"alt candidate read[22] = 0x{raw[22]:02x}")
