"""Connect to a WT901DCL / BWT901CL over BLE (no Windows pairing) and print accel + gyro.

Usage: uv run python run.py [--name WT BWT HC-06] [--address AA:BB:CC:DD:EE:FF] [--timeout 5]
       [--osc-host localhost] [--osc-port 45533] [-v]

Without --address, shows a menu of the WT901-type devices found. Samples are sent
over OSC as one bundle: /imu/A{X,Y,Z} (accel, g), /imu/G{X,Y,Z} (gyro, deg/s) and
/imu/ang{X,Y,Z} (roll/pitch/yaw, deg). IMU values are printed
to the console only with -v.
"""

import argparse
import asyncio

from utils.ble import find_device, stream
from utils.menu import choose_device
from utils.osc import OscSender
from utils.protocol import FrameParser, RegisterReply
from utils.settings import describe_settings


async def main(args):
    prefixes = tuple(p.upper() for p in args.name)
    if args.address:
        print("Scanning...")
        device = await find_device(prefixes, args.address, args.timeout)
    else:
        device = await choose_device(prefixes, args.timeout)
        if device is None:
            return

    parser = FrameParser()
    osc = OscSender(args.osc_host, args.osc_port)
    print(f"Sending OSC to {args.osc_host}:{args.osc_port}")
    latest = {"acc": None, "gyro": None, "angle": None}
    fresh: set[str] = set()
    replies: asyncio.Queue = asyncio.Queue()

    async def on_connected(write):
        try:
            info = await describe_settings(write, replies)
        except Exception as e:  # noqa: BLE001
            info = f"settings unavailable ({e})"
        print(f"Connected to {device.name} [{device.address}]")
        print(f"{info}")
        print(f"\n\t(Ctrl+C to quit)")

    def on_data(data: bytes):
        for s in parser.feed(data):
            if isinstance(s, RegisterReply):
                replies.put_nowait(s)
                continue
            # Some sensors send acc, gyro and angle as separate frames, so wait until
            # all three are fresh and send one bundle per cycle.
            for key in latest:
                if (value := getattr(s, key)) is not None:
                    latest[key] = value
                    fresh.add(key)
            if fresh != set(latest) or not all(latest.values()):
                continue
            fresh.clear()
            a, g, ang = latest["acc"], latest["gyro"], latest["angle"]
            osc.send(a, g, ang)
            if args.verbose:
                print(
                    f"A[g] {a[0]:+8.2f} {a[1]:+8.2f} {a[2]:+8.2f}  "
                    f"G[dps] {g[0]:+9.2f} {g[1]:+9.2f} {g[2]:+9.2f}"
                )

    await stream(device, on_data, on_connected)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--name",
        nargs="+",
        default=["WT", "BWT", "HC-06"],
        help="advertised name prefixes to list (case-insensitive)",
    )
    ap.add_argument("--address", help="BLE address (skips the menu)")
    ap.add_argument("--timeout", type=float, default=5.0)
    ap.add_argument("--osc-host", default="localhost")
    ap.add_argument("--osc-port", type=int, default=45531)
    ap.add_argument(
        "-v", "--verbose", action="store_true", help="print IMU values to the console"
    )
    try:
        asyncio.run(main(ap.parse_args()))
    except KeyboardInterrupt:
        pass
    except (TimeoutError, ConnectionError) as e:
        raise SystemExit(str(e)) from None
