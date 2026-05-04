"""Probe 2 — discover the right HID output-report size for this device.
Still strictly read-only at the application layer (only sends the
Elitech 'get device info' bytes), but tries different report sizes."""
import hid, time, sys

VID, PID = 0x2047, 0x0301
APP_CMD = bytes([0xCC, 0x00, 0x06, 0x00, 0xD2])  # Elitech device-info, read-only

def open_dev():
    for d in hid.enumerate(VID, PID):
        h = hid.device()
        h.open_path(d["path"])
        return h
    sys.exit("device not found")

def drain(h, ms=400):
    h.set_nonblocking(True)
    end = time.time() + ms / 1000.0
    out = []
    while time.time() < end:
        r = h.read(64, timeout_ms=50)
        if r:
            out.append(bytes(r))
    return out

def try_size(report_size, with_len_prefix):
    print(f"\n--- size={report_size}  len_prefix={with_len_prefix} ---")
    h = open_dev()
    drain(h, 50)
    payload = bytes([len(APP_CMD)]) + APP_CMD if with_len_prefix else APP_CMD
    body = payload + b"\x00" * (report_size - len(payload))
    wire = b"\x00" + body  # report id 0 + report body
    print(f"  wire ({len(wire)}B): {wire.hex(' ')[:80]}{'...' if len(wire)>27 else ''}")
    n = h.write(wire)
    err = h.error() if n < 0 else ""
    print(f"  write -> {n}  err={err!r}")
    if n > 0:
        replies = drain(h, 500)
        print(f"  replies: {len(replies)}")
        for i, r in enumerate(replies):
            print(f"    [{i}] {len(r)}B: {r.hex(' ')}")
    h.close()

for sz in (8, 16, 32, 64):
    for lp in (False, True):
        try_size(sz, lp)
