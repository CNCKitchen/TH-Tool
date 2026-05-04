"""Inspect the raw op=0x22 response and try a few op=0x12 variants
to understand why the name isn't being persisted."""
import hid, time, sys
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, r"c:\Users\stefa\Desktop\TH-Tool")
from trh import open_dev, make_req, request, read_until_idle, RID

h = open_dev()
read_until_idle(h, idle_ms=100, max_ms=200)

# 1) Read current name response, raw
print("=== op=0x22 read ===")
rs = request(h, bytes([0x22]))
for r in rs:
    print(f"  {len(r)}B: {r.hex(' ')}")

# 2) Try variant A: just op=0x12 + name at offset 11 (current behaviour, 53 bytes)
print("\n=== variant A: op=0x12, 53B, name@11 ===")
p = bytearray(53)
p[0] = 0x12
p[11:15] = b"AAAA"
print(f"  send: {p.hex(' ')}")
rs = request(h, bytes(p))
for r in rs:
    print(f"  ack: {r[:r[1]+2].hex(' ')}")
time.sleep(0.2)
rs = request(h, bytes([0x22]))
for r in rs:
    print(f"  read-back: {r[:30].hex(' ')}")

# 3) Try variant B: op=0x05 handshake, then op=0x03 with current settings,
#    then op=0x12 with name
print("\n=== variant B: full sequence (mirror vendor) ===")
# Read meta first
rs = request(h, bytes([0x04]))
meta = None
for r in rs:
    if r[1] == 0x1F and r[2:5] == b"\x00\x00\x04":
        meta = r[2:2+r[1]]
        break
print(f"  meta: {meta.hex(' ')}")

# Build op=0x03 payload preserving everything
payload = bytearray(29)
payload[0]    = 0x03
payload[1:3]  = meta[3:5]
payload[3:5]  = b"\x00\x00"
payload[5]    = meta[7]
payload[6:9]  = b"\x00\x00\x00"
payload[9]    = meta[11]
payload[10]   = meta[12]
payload[11]   = 0x00
payload[12:16] = meta[14:18]
payload[16:18] = b"\x00\x00"
payload[18:20] = meta[20:22]
payload[20]   = meta[13]
import datetime
now = datetime.datetime.now()
payload[21:28] = now.year.to_bytes(2, "little") + bytes([now.month, now.day, now.hour, now.minute, now.second])
payload[28]   = 0x00
print(f"  op=0x03 send: {bytes(payload).hex(' ')}")

request(h, bytes([0x05]))
rs = request(h, bytes(payload))
for r in rs:
    print(f"  op=0x03 ack: {r[:r[1]+2].hex(' ')}")

# Now name write
p = bytearray(53)
p[0] = 0x12
p[11:15] = b"BBBB"
print(f"  op=0x12 send: {bytes(p).hex(' ')}")
rs = request(h, bytes(p))
for r in rs:
    print(f"  op=0x12 ack: {r[:r[1]+2].hex(' ')}")

time.sleep(0.3)
rs = request(h, bytes([0x22]))
for r in rs:
    print(f"  read-back: {r[:30].hex(' ')}")

h.close()
