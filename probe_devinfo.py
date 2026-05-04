"""Probe 1 (READ-ONLY) — try the Elitech 'device info' query in two
HID-transport flavours and log everything.

Strictly read-only: only command CC 00 06 00 D2 (Elitech 'get device info')
is sent. No writes, no setting changes. If this gets a response, we have a
huge head start; if not, we'll think again before sending anything else.
"""
import hid, time, sys

VID, PID = 0x2047, 0x0301

def open_dev():
    for d in hid.enumerate(VID, PID):
        h = hid.device()
        h.open_path(d["path"])
        return h
    sys.exit("device not found")

def drain(h, ms=300):
    """Read any pending input reports for `ms` and return them."""
    h.set_nonblocking(True)
    end = time.time() + ms / 1000.0
    out = []
    while time.time() < end:
        r = h.read(64, timeout_ms=50)
        if r:
            out.append(bytes(r))
    return out

def try_send(label, payload):
    """payload is the application bytes (without HID report ID).
    On Windows hidapi we prepend 0x00 as report ID."""
    print(f"\n=== {label} ===")
    print(f"  out app bytes ({len(payload)}): {payload.hex(' ')}")
    h = open_dev()
    drain(h, 100)  # flush stale
    # Right-pad to 64 bytes for the OUT report, prepend report-id 0.
    pad = payload + b"\x00" * (64 - len(payload))
    wire = b"\x00" + pad  # 65 bytes total
    n = h.write(wire)
    print(f"  hid.write returned: {n}")
    replies = drain(h, 600)
    print(f"  replies: {len(replies)}")
    for i, r in enumerate(replies):
        print(f"    [{i}] {len(r)}B: {r.hex(' ')}")
    h.close()
    return replies

# Candidate A: TI Datapipe standard — first byte = valid-byte count.
A = bytes([5, 0xCC, 0x00, 0x06, 0x00, 0xD2])

# Candidate B: raw command, no length prefix.
B = bytes([0xCC, 0x00, 0x06, 0x00, 0xD2])

ra = try_send("A: Datapipe wrapper [len=5][CC 00 06 00 D2]", A)
rb = try_send("B: Raw [CC 00 06 00 D2]", B)

print("\nSummary:", "A=", len(ra), " B=", len(rb))
