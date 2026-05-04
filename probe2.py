"""Probe 3 (READ-ONLY) — try Elitech 'device info' query with the
correct OUT report size (64 bytes total = 1 report-id byte + 63 payload)."""
import hid, time, sys

VID, PID = 0x2047, 0x0301
APP = bytes([0xCC, 0x00, 0x06, 0x00, 0xD2])  # read-only

def open_dev():
    for d in hid.enumerate(VID, PID):
        h = hid.device()
        h.open_path(d["path"])
        return h
    sys.exit("device not found")

def drain(h, ms=600):
    h.set_nonblocking(True)
    end = time.time() + ms / 1000.0
    out = []
    while time.time() < end:
        r = h.read(64, timeout_ms=50)
        if r:
            out.append(bytes(r))
    return out

def send(label, payload):
    print(f"\n=== {label} ===")
    body = payload + b"\x00" * (63 - len(payload))     # 63 data bytes
    wire = b"\x00" + body                              # + 1 report id = 64 total
    print(f"  wire ({len(wire)}B): {wire.hex(' ')[:96]}...")
    h = open_dev()
    drain(h, 50)
    n = h.write(wire)
    err = h.error() if n < 0 else ""
    print(f"  write -> {n}  err={err!r}")
    if n > 0:
        replies = drain(h, 800)
        print(f"  replies: {len(replies)}")
        for i, r in enumerate(replies):
            print(f"    [{i}] {len(r)}B: {r.hex(' ')}")
            txt = ''.join(chr(b) if 32 <= b < 127 else '.' for b in r)
            print(f"         ascii: {txt}")
    h.close()

# Variant A: TI Datapipe convention — first byte = valid byte count
send("A: [len=5][CC 00 06 00 D2]", bytes([5]) + APP)
# Variant B: raw command bytes
send("B: [CC 00 06 00 D2]", APP)
