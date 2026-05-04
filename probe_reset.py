"""Test whether [01][00] resets the read pointer so [01][01] yields data again."""
import hid, time, sys
sys.stdout.reconfigure(line_buffering=True)

VID, PID = 0x2047, 0x0301
RID = 0x3F

def open_dev():
    for d in hid.enumerate(VID, PID):
        h = hid.device()
        h.open_path(d["path"])
        return h
    sys.exit("device not found")

def make_req(payload):
    return bytes([RID]) + payload + b"\x00" * (64 - 1 - len(payload))

def listen(h, idle_ms=300, max_ms=5000):
    h.set_nonblocking(True)
    out = []
    last = time.time()
    start = last
    while True:
        if (time.time() - last) * 1000 >= idle_ms: break
        if (time.time() - start) * 1000 >= max_ms: break
        r = h.read(64, timeout_ms=50)
        if r:
            out.append(bytes(r)); last = time.time()
    return out

def send(h, payload, label, max_ms=5000):
    print(f"\n>>> {label}: send {payload.hex(' ')}")
    h.write(make_req(payload))
    rs = listen(h, idle_ms=300, max_ms=max_ms)
    print(f"    got {len(rs)} report(s)")
    for r in rs[:3]:
        print(f"      {r.hex(' ')}")
    if len(rs) > 3:
        print(f"      ... +{len(rs)-3} more")
    return rs

h = open_dev()
listen(h, idle_ms=80, max_ms=200)  # flush

# Test 1: cold [01][01] — expected no-data trailer
send(h, bytes([0x01, 0x01]), "cold [01][01]")

# Test 2: [01][00] (presumed reset)
send(h, bytes([0x01, 0x00]), "reset [01][00]", max_ms=1500)

# Test 3: [01][01] right after reset
send(h, bytes([0x01, 0x01]), "after-reset [01][01]")

h.close()
