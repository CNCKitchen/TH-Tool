"""Parse the USBPcap file and extract HID traffic on the LOG_TRH device.
USBPcap link-layer format (LINKTYPE_USBPCAP = 249) per Wireshark docs.

We dump every interrupt OUT/IN payload with the full hex; HID reports are
identifiable by the 0x3F leading report-id byte.
"""
import struct, sys, datetime
sys.stdout.reconfigure(line_buffering=True)

PCAP = r"c:\Users\stefa\Desktop\TH-Tool\usbpcap"

GLOBAL_HDR = "<IHHiIII"  # magic, vmaj, vmin, thiszone, sigfigs, snaplen, network
GLOBAL_HDR_SZ = struct.calcsize(GLOBAL_HDR)
PKT_HDR = "<IIII"        # ts_sec, ts_usec, incl_len, orig_len
PKT_HDR_SZ = struct.calcsize(PKT_HDR)

# USBPcap pseudo-header (little-endian)
# https://desowin.org/usbpcap/captureformat.html
USBPCAP_HDR = "<HQIHBHHBBI"  # headerLen, irpId, status, function, info,
                              # bus, device, endpoint, transfer, dataLen
USBPCAP_HDR_SZ = struct.calcsize(USBPCAP_HDR)

XFER = {0: "ISOC", 1: "INTR", 2: "CTRL", 3: "BULK"}

with open(PCAP, "rb") as f:
    g = f.read(GLOBAL_HDR_SZ)
    magic, vmaj, vmin, _, _, snap, net = struct.unpack(GLOBAL_HDR, g)
    print(f"pcap magic=0x{magic:08x} ver={vmaj}.{vmin} link={net} (249 = USBPcap)")
    assert net == 249

    pkts = []
    while True:
        h = f.read(PKT_HDR_SZ)
        if not h or len(h) < PKT_HDR_SZ:
            break
        ts_s, ts_us, incl, orig = struct.unpack(PKT_HDR, h)
        body = f.read(incl)
        if len(body) < USBPCAP_HDR_SZ:
            continue
        hdr_len, irp, status, func, info, bus, dev, ep, xfer, dlen = \
            struct.unpack_from(USBPCAP_HDR, body, 0)
        data = body[hdr_len:hdr_len+dlen]
        pkts.append((ts_s + ts_us/1e6, bus, dev, ep, xfer, info, func, data))

print(f"\n{len(pkts)} packets")

# Discover (bus,dev) of our HID device. We expect to see vendor 2047 / product 0301
# in some control descriptor exchange. Easier: filter by interrupt + payload starts 0x3F.
hid_pkts = [p for p in pkts if p[4] == 1 and p[7] and p[7][0] == 0x3F]
print(f"{len(hid_pkts)} interrupt packets with leading 0x3F (LOG_TRH HID)")

# Identify the (bus, dev) tuple
seen = {}
for ts, bus, dev, ep, xfer, info, func, data in hid_pkts:
    seen[(bus, dev)] = seen.get((bus, dev), 0) + 1
print(f"  bus/dev distribution: {seen}")

# Pick the most common
target = max(seen, key=seen.get)
print(f"  using bus={target[0]} dev={target[1]}\n")

# info bit 0: 0=submit, 1=complete (PDO->FDO)
# Direction is in endpoint MSB: 0x80 = IN, otherwise OUT.
print("--- HID OUT/IN sequence ---")
t0 = None
for ts, bus, dev, ep, xfer, info, func, data in hid_pkts:
    if (bus, dev) != target:
        continue
    if t0 is None:
        t0 = ts
    direction = "IN " if (ep & 0x80) else "OUT"
    submit_or_complete = "<-" if info & 1 else "->"
    rel = ts - t0
    # Skip submit-side OUT duplicates? In USBPcap, OUT submit has the data,
    # OUT complete is empty. IN submit is empty, IN complete has data.
    if not data:
        continue
    print(f"[{rel:7.3f}s] {direction} ep=0x{ep:02x}  ({len(data)}B): {data.hex(' ')}")
