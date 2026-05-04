"""Probe 8 (mostly READ-ONLY) — grid scan low opcodes 0x00..0x0F to see
which (if any) elicit a response. We try four framings each:
  A) just [opcode] padded with zeros
  B) [opcode 00 00 00 00] (5-byte command, opcode + 4 zeros)
  C) [01][opcode] (TI Datapipe length=1 prefix)
  D) [05][opcode 00 00 00 00] (TI Datapipe length=5)

For each successful elicit, capture the response and stop further probing
of the same framing class.
"""
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

def make_report(payload):
    body = payload + b"\x00" * (63 - len(payload))
    return bytes([RID]) + body

def listen(h, sec):
    h.set_nonblocking(True)
    end = time.time() + sec
    out = []
    while time.time() < end:
        r = h.read(64, timeout_ms=50)
        if r:
            out.append(bytes(r))
    return out

h = open_dev()
listen(h, 0.1)  # flush

framings = {
    "A bare           ": lambda op: bytes([op]),
    "B opcode+4zero   ": lambda op: bytes([op, 0, 0, 0, 0]),
    "C TI[len1]+op    ": lambda op: bytes([1, op]),
    "D TI[len5]+op+4z ": lambda op: bytes([5, op, 0, 0, 0, 0]),
}

hits = []
for label, builder in framings.items():
    print(f"\n=== Framing {label.strip()} ===")
    for op in range(0x00, 0x10):
        cmd = builder(op)
        rep = make_report(cmd)
        h.write(rep)
        replies = listen(h, 0.4)
        flag = ""
        if replies:
            flag = f" <-- {len(replies)} reply"
            hits.append((label, op, replies))
        print(f"  op=0x{op:02x}  cmd={cmd.hex(' ')}{flag}")
        for r in replies:
            print(f"    {r.hex(' ')}")

h.close()
print(f"\n=== {len(hits)} hits total ===")
