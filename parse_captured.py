"""Parse the 212 records captured during probe7 op=0x01 dump and write a CSV.

Each input line is the raw HID input report as hex (64 bytes / 128 hex chars):
  [0x3F][len][seq_hi][seq_lo][record bytes...]
"""
import struct, csv, datetime, sys
sys.stdout.reconfigure(line_buffering=True)

# Captured during probe7 framing C, op=0x01
PAGES_HEX = [
    "3f 3e 00 01 b6 08 0e 10 ca 08 a4 10 c0 08 b8 10 c0 08 30 11 ca 08 1c 11 d4 08 4e 11 e8 08 12 11 f2 08 12 11 fc 08 1c 11 06 09 12 11 1a 09 fe 10 1a 09 f4 10 1a 09 ea 10 06 09 f4 10 fc 08 f4 10",
    "3f 3e 00 02 f2 08 12 11 e8 08 26 11 de 08 44 11 ca 08 62 11 c0 08 80 11 b6 08 94 11 ac 08 b2 11 a2 08 c6 11 98 08 d0 11 8e 08 ee 11 84 08 f8 11 84 08 0c 12 7a 08 16 12 70 08 2a 12 70 08 48 12",
    "3f 3e 00 03 66 08 48 12 66 08 5c 12 5c 08 66 12 5c 08 7a 12 52 08 84 12 52 08 98 12 48 08 98 12 48 08 a2 12 48 08 ac 12 3e 08 b6 12 3e 08 c0 12 3e 08 ca 12 3e 08 ca 12 34 08 d4 12 34 08 d4 12",
    "3f 3e 00 04 34 08 de 12 34 08 e8 12 2a 08 e8 12 2a 08 e8 12 2a 08 f2 12 2a 08 f2 12 20 08 fc 12 20 08 fc 12 20 08 10 13 20 08 10 13 16 08 10 13 16 08 1a 13 16 08 1a 13 16 08 1a 13 16 08 24 13",
    "3f 3e 00 05 0c 08 38 13 0c 08 2e 13 0c 08 38 13 0c 08 38 13 0c 08 38 13 0c 08 38 13 0c 08 38 13 02 08 42 13 02 08 56 13 02 08 4c 13 02 08 4c 13 02 08 56 13 02 08 56 13 f8 07 60 13 f8 07 56 13",
    "3f 3e 00 06 f8 07 60 13 f8 07 56 13 f8 07 60 13 f8 07 6a 13 f8 07 6a 13 f8 07 6a 13 ee 07 6a 13 ee 07 6a 13 ee 07 6a 13 ee 07 6a 13 ee 07 6a 13 ee 07 74 13 ee 07 6a 13 ee 07 74 13 e4 07 7e 13",
    "3f 3e 00 07 e4 07 74 13 e4 07 74 13 e4 07 74 13 e4 07 74 13 e4 07 74 13 e4 07 74 13 e4 07 74 13 e4 07 74 13 da 07 7e 13 da 07 7e 13 da 07 7e 13 da 07 7e 13 da 07 7e 13 da 07 7e 13 da 07 7e 13",
    "3f 3e 00 08 da 07 88 13 da 07 7e 13 da 07 7e 13 da 07 7e 13 d0 07 7e 13 d0 07 7e 13 d0 07 7e 13 d0 07 7e 13 d0 07 7e 13 d0 07 7e 13 d0 07 7e 13 d0 07 7e 13 d0 07 7e 13 d0 07 88 13 d0 07 7e 13",
    "3f 3e 00 09 d0 07 7e 13 c6 07 7e 13 c6 07 88 13 c6 07 7e 13 c6 07 88 13 c6 07 88 13 c6 07 7e 13 c6 07 88 13 c6 07 7e 13 c6 07 88 13 c6 07 88 13 c6 07 88 13 c6 07 88 13 c6 07 88 13 c6 07 88 13",
    "3f 3e 00 0a c6 07 88 13 c6 07 88 13 c6 07 7e 13 c6 07 88 13 d0 07 7e 13 d0 07 7e 13 da 07 7e 13 da 07 74 13 e4 07 74 13 44 07 2e 0e cc 06 5a 0f f4 06 18 10 1c 07 72 10 3a 07 a4 10 62 07 1c 11",
    "3f 3e 00 0b 80 07 12 11 b2 07 08 11 da 07 08 11 f8 07 08 11 16 08 08 11 34 08 f4 10 3e 08 ea 10 3e 08 f4 10 3e 08 08 11 3e 08 1c 11 3e 08 26 11 3e 08 3a 11 3e 08 44 11 48 08 4e 11 48 08 58 11",
    "3f 3e 00 0c 48 08 62 11 52 08 6c 11 52 08 76 11 5c 08 80 11 5c 08 8a 11 66 08 8a 11 66 08 94 11 70 08 94 11 7a 08 94 11 84 08 9e 11 84 08 9e 11 8e 08 9e 11 8e 08 9e 11 98 08 c6 11 98 08 f8 11",
    "3f 3e 00 0d a2 08 0c 12 b6 08 e4 11 ca 08 c6 11 e8 08 a8 11 e8 08 94 11 e8 08 94 11 de 08 9e 11 de 08 a8 11 de 08 a8 11 d4 08 c6 11 ca 08 d0 11 d4 08 ee 11 e8 08 d0 11 fc 08 b2 11 10 09 94 11",
    "3f 3e 00 0e 24 09 8a 11 2e 09 80 11 42 09 58 11 4c 09 4e 11 42 09 44 11 42 09 4e 11 56 09 3a 11 6a 09 30 11 6a 09 12 11 6a 09 26 11 74 09 1c 11 74 09 fe 10 7e 09 12 11 7e 09 fe 10 7e 09 12 11",
    "3f 0a 00 0f 92 09 f4 10 9c 09 ea 10",
]

def parse(pages_hex):
    raw = b""
    for line in pages_hex:
        rep = bytes.fromhex(line.replace(" ", ""))
        rid, length = rep[0], rep[1]
        assert rid == 0x3F, f"bad report id 0x{rid:02x}"
        app = rep[2:2 + length]
        seq = (app[0] << 8) | app[1]
        data = app[2:]
        # sanity: each "data" should be a multiple of 4 bytes
        assert len(data) % 4 == 0
        raw += data
    return raw

raw = parse(PAGES_HEX)
print(f"Raw record bytes: {len(raw)}  (expected 212 * 4 = 848)")

records = []
for i in range(0, len(raw), 4):
    t_raw, rh_raw = struct.unpack_from("<hh", raw, i)
    records.append((t_raw / 100.0, rh_raw / 100.0))

print(f"Records parsed: {len(records)}")

temps = [t for t, _ in records]
hums  = [r for _, r in records]
print(f"\nVerify against PDF:")
print(f"  N      = {len(records)}     (PDF: 212)")
print(f"  T min  = {min(temps):>5.2f}    (PDF: 17.4)")
print(f"  T max  = {max(temps):>5.2f}    (PDF: 24.6)")
print(f"  RH min = {min(hums):>5.2f}    (PDF: 36.3)")
print(f"  RH max = {max(hums):>5.2f}    (PDF: 50.0)")

# Compose timestamps from known start + 5 min interval (PDF-derived)
start = datetime.datetime(2026, 3, 9, 19, 57, 1)
interval = datetime.timedelta(minutes=5)

# Save CSV
csv_path = r"c:\Users\stefa\Desktop\TH-Tool\log_trh_records.csv"
with open(csv_path, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["timestamp", "temperature_c", "humidity_rh"])
    for i, (t, rh) in enumerate(records):
        ts = (start + i * interval).isoformat(sep=" ")
        w.writerow([ts, f"{t:.2f}", f"{rh:.2f}"])
print(f"\nWrote {csv_path}")

# Show first/last 3 with timestamps
print("\nFirst 3 records:")
for i in range(3):
    ts = start + i * interval
    print(f"  {ts}  T={records[i][0]:.2f} C  RH={records[i][1]:.2f} %")
print("Last 3 records:")
for i in range(len(records) - 3, len(records)):
    ts = start + i * interval
    print(f"  {ts}  T={records[i][0]:.2f} C  RH={records[i][1]:.2f} %")
