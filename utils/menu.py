"""Interactive device picker."""

import asyncio

from bleak.backends.device import BLEDevice

from .ble import scan_devices

# Broadcast-name prefix (upper case) -> product name
PRODUCT_NAMES = {
    "WT901BLE67": "WT9011DCL",
    "HC-06": "BWT901CL",
}


def product_name(broadcast_name: str) -> str:
    for prefix, product in PRODUCT_NAMES.items():
        if broadcast_name.upper().startswith(prefix):
            return product
    return "Unknown"


async def choose_device(prefixes: tuple[str, ...], timeout: float) -> BLEDevice | None:
    """Scan, list WT901-type devices, and let the user pick one or re-scan.

    Returns None if the user quits.
    """
    while True:
        print(f"Scanning for {timeout:g}s...")
        found = await scan_devices(prefixes, timeout)
        print()
        if found:
            addr_header = "MAC Address / UUID"
            addr_width = max(len(addr_header), *(len(d.address) for d, _, _ in found))
            print("Devices found:")
            print(
                f"      {'Device Name':<12} {'Broadcast Name':<16} "
                f"{addr_header:<{addr_width}}  Strength"
            )
            for i, (dev, name, rssi) in enumerate(found, 1):
                print(
                    f"  [{i}] {product_name(name):<12} {name:<16} "
                    f"{dev.address:<{addr_width}}  {rssi} dBm"
                )
        else:
            print("No WT901 devices found. Make sure the sensor is powered and not")
            print("connected to another app or phone.")
        print("  [r] Re-scan")
        print("  [q] Quit")

        while True:
            try:
                choice = (await asyncio.to_thread(input, "Select: ")).strip().lower()
            except EOFError:
                return None
            if choice == "r":
                break
            if choice == "q":
                return None
            if choice.isdigit() and 1 <= int(choice) <= len(found):
                return found[int(choice) - 1][0]
            print("Invalid selection.")
