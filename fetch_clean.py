"""Clean fetch on a freshly plugged device:
  1. Send op=0x04 first  -> metadata (start time + interval + ...)
  2. Then op=0x06        -> live reading
  3. Then op=0x01        -> full data dump

Prints all responses raw so we can see the metadata bytes uncontaminated."""
import hid, time, struct, sys
sys.stdout.reconfigure(line_buffering=True)

VID, PID = 0x2047, 0x0301
RID = 0x3F

def open_dev():
    for d in hid.enumerate(VID, PID):
        h = hid.device()
        h.open_path(d["path"])
        return h
    sys.exit("device not found")

def make_req(payload: bytes) -> bytes:
    body = bytes([len(payload)]) + payload
    body = body + b"\x00" * (63 - len(body))
    return bytes([RID]) + body

def read_until_idle(h, idle_ms=300, max_ms=5000):
    h.set_nonblocking(True)
    out = []
    last = time.time(); start = last
    while True:
        if (time.time() - last) * 1000 >= idle_ms: break
        if (time.time() - start) * 1000 >= max_ms: break
        r = h.read(64, timeout_ms=50)
        if r:
            out.append(bytes(r)); last = time.time()
    return out

def cmd(h, payload, label, max_ms=5000):
    print(f"\n>>> {label}: send {payload.hex(' ')}")
    h.write(make_req(payload))
    rs = read_until_idle(h, idle_ms=400, max_ms=max_ms)
    print(f"    {len(rs)} report(s):")
    for r in rs:
        rid, length = r[0], r[1]
        app = r[2:2 + length]
        print(f"      [id=0x{rid:02x} len={length:2d}]  {app.hex(' ')}")
        # show ASCII for any printable runs
        ascii_view = ''.join(chr(b) if 32 <= b < 127 else '.' for b in app)
        if any(32 <= b < 127 for b in app):
            print(f"        ascii: {ascii_view}")
    return rs

h = open_dev()
read_until_idle(h, idle_ms=80, max_ms=200)  # flush

# 1) Metadata first (clean buffer)
meta = cmd(h, bytes([0x04]), "META op=0x04")

# 2) Live reading
live = cmd(h, bytes([0x06]), "LIVE op=0x06")

# 3) Full data dump
print("\n>>> DUMP op=0x01: send 01")
h.write(make_req(bytes([0x01])))
dump = read_until_idle(h, idle_ms=400, max_ms=8000)
print(f"    {len(dump)} report(s) total")

# Concatenate data pages
pages = {}
trailers = []
for r in dump:
    rid, length = r[0], r[1]
    app = r[2:2 + length]
    if length == 3:
        trailers.append(app)
        print(f"      trailer: {app.hex(' ')}")
        continue
    seq = (app[0] << 8) | app[1]
    pages[seq] = app[2:]

raw = b"".join(d for _, d in sorted(pages.items()))
print(f"\nTotal raw record bytes: {len(raw)}  ({len(raw)//4} records)")

records = [struct.unpack_from("<hh", raw, i) for i in range(0, len(raw), 4)]
records = [(t/100.0, rh/100.0) for t, rh in records]
if records:
    temps = [t for t, _ in records]
    hums  = [r for _, r in records]
    print(f"  T  min/max: {min(temps):.2f} / {max(temps):.2f}")
    print(f"  RH min/max: {min(hums):.2f} / {max(hums):.2f}")

# Re-display the meta payload with byte annotations
if meta:
    app = meta[0][2:2 + meta[0][1]]
    print(f"\nMETA payload ({len(app)} bytes):")
    for i, b in enumerate(app):
        print(f"  [{i:2d}] 0x{b:02x}  ({b})")

h.close()
