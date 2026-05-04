# TH-Tool

A small command-line tool for the **CEM DT-191A / RS-191A** USB temperature
& humidity data logger (sold under various brands; HID `VID 0x2047 PID 0x0301`,
USB mass-storage product string `LOG_TRH`).

The vendor's Windows-only software is the usual flaky bundled affair. This is
a clean, scriptable replacement: read live values, dump records to CSV/XLSX,
and reconfigure the logger from the terminal.

The HID protocol was reverse-engineered from USB captures — there is no
vendor documentation behind any of this. **Use at your own risk.**

## Install

```
pip install -r requirements.txt
```

On Linux you'll likely need a udev rule so non-root users can talk to the
device. Drop this in `/etc/udev/rules.d/60-log-trh.rules`:

```
SUBSYSTEM=="usb", ATTRS{idVendor}=="2047", ATTRS{idProduct}=="0301", MODE="0666"
```

then `sudo udevadm control --reload && sudo udevadm trigger`.

On Windows, the device enumerates as HID out of the box — no driver work.

## Usage

```
python trh.py info
python trh.py fetch out.csv          # or out.xlsx
python trh.py set --sample 60 --unit c --time
```

### `info`
Prints model, logger name, capacity, current sample rate, LED cycle, start
mode, temperature unit, session start time, and a live reading.

### `fetch PATH`
Dumps all stored records. Output is CSV if `PATH` ends in `.csv`, else XLSX.
Columns: `timestamp, elapsed_minutes, temperature_c, humidity_rh`.

> **One-shot per power cycle.** The logger only streams its records out once
> after each plug-in. If you've already fetched on this session, unplug and
> replug before fetching again.

### `set [options]`
| flag | meaning |
| --- | --- |
| `--sample N` | sample interval — accepts `4s`, `60`, `5m`, `1h` |
| `--led N`    | LED flash cycle in seconds |
| `--start manual\|instant` | recording start mode |
| `--unit c\|f` | display unit on the device |
| `--name STR` | logger name (≤ 16 ASCII chars) |
| `--time`     | sync the device clock to the host clock |

> **`set` resets the session and erases stored records.** Run `fetch` first
> if you care about them.

## License

MIT. See [LICENSE](LICENSE).
