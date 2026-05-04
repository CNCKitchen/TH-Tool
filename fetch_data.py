"""Fetch all data records from the LOG_TRH and verify against the PDF
(212 records, T 17.4-24.6 C, RH 36.3-50.0 %).

Protocol summary (reverse-engineered, READ-ONLY here):
  Wire HID report = 64 bytes:
    [0x3F report-id] [len] [app payload (len bytes)] [pad...]

  op=0x01 (dump records):
    request app payload  = single byte 0x01
    response             = stream of 64-byte reports:
        [0x3F][len=0x3E][seq_hi=0][seq_lo=N][60 bytes data]   (full page)
        [0x3F][len=0x0A][0][N][8 bytes data]                  (last page)
        [0x3F][len=0x03][00 00 XX]                            (3-byte trailer)
    Each record = 4 bytes: T_int16_LE, RH_int16_LE, both x100.
"""
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
    return bytes([RID]) + body  # 64 bytes total

def read_until_idle(h, idle_ms=300, max_total_ms=4000):
    """Read input reports until idle_ms of silence or hard cap."""
    h.set_nonblocking(True)
    out = []
    last_rx = time.time()
    start = last_rx
    while True:
        if (time.time() - last_rx) * 1000 >= idle_ms:
            break
        if (time.time() - start) * 1000 >= max_total_ms:
            break
        r = h.read(64, timeout_ms=50)
        if r:
            out.append(bytes(r))
            last_rx = time.time()
    return out

def fetch_records():
    h = open_dev()
    read_until_idle(h, idle_ms=80)  # flush stale

    h.write(make_req(bytes([0x01])))
    reports = read_until_idle(h, idle_ms=300, max_total_ms=5000)
    h.close()

    print(f"Got {len(reports)} HID reports")

    # Each report: [0x3F][len][app payload]
    # App payload for data pages: [seq_hi][seq_lo][record bytes...]
    # Trailer: [0x3F][len=3][00 00 XX]
    pages = {}    # seq -> data bytes
    trailers = []
    for r in reports:
        if r[0] != RID:
            print(f"  unexpected report id 0x{r[0]:02x}: {r.hex(' ')[:80]}")
            continue
        length = r[1]
        app = r[2:2+length]
        if length >= 2 and length != 3:
            seq = (app[0] << 8) | app[1]
            data = app[2:]
            pages[seq] = data
            print(f"  page {seq:3d}  len={length}  data={len(data)}B")
        else:
            trailers.append(app)
            print(f"  trailer len={length} payload={app.hex(' ')}")

    # Concatenate pages in order
    if not pages:
        sys.exit("no data pages received")
    ordered = sorted(pages.items())
    blob = b"".join(d for _, d in ordered)
    print(f"\nTotal data: {len(blob)} bytes ({len(blob)//4} records)")

    # Parse records: T_int16_LE, RH_int16_LE, both x100
    records = []
    for i in range(0, len(blob) - len(blob) % 4, 4):
        t_raw, rh_raw = struct.unpack_from("<hh", blob, i)
        records.append((t_raw / 100.0, rh_raw / 100.0))
    return records

if __name__ == "__main__":
    recs = fetch_records()
    print(f"\nFirst 5 records:  {recs[:5]}")
    print(f"Last 5 records:   {recs[-5:]}")

    temps = [t for t, _ in recs]
    hums  = [h for _, h in recs]
    print(f"\nN={len(recs)}")
    print(f"T:   min={min(temps):.2f}  max={max(temps):.2f}  (PDF: 17.4..24.6)")
    print(f"RH:  min={min(hums):.2f}  max={max(hums):.2f}  (PDF: 36.3..50.0)")
