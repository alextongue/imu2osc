"""Scan and stream helpers. No OS-level pairing is done: like the vendor app,
this scans advertisements and opens an unpaired GATT connection."""

import asyncio
from collections.abc import Awaitable, Callable

from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice

from .protocol import NOTIFY_UUIDS, SERVICE_UUIDS, WRITE_UUIDS

Writer = Callable[[bytes], Awaitable[None]]


def is_wit_device(
    name: str, service_uuids: list[str] | None, prefixes: tuple[str, ...]
) -> bool:
    """True for WT901/BWT901-type sensors, by advertised name or sensor service."""
    return name.upper().startswith(prefixes) or any(
        u in SERVICE_UUIDS for u in service_uuids or []
    )


async def scan_devices(
    prefixes: tuple[str, ...], timeout: float
) -> list[tuple[BLEDevice, str, int]]:
    """Scan for WT901-type devices; returns (device, name, rssi), strongest first."""
    seen = await BleakScanner.discover(timeout=timeout, return_adv=True)
    found = []
    for dev, adv in seen.values():
        name = adv.local_name or dev.name or ""
        if is_wit_device(name, adv.service_uuids, prefixes):
            found.append((dev, name or "(unnamed)", adv.rssi))
    return sorted(found, key=lambda f: f[2], reverse=True)


async def find_device(
    prefixes: tuple[str, ...], address: str | None, timeout: float
) -> BLEDevice:
    def match(dev, adv):
        if address:
            return dev.address.upper() == address.upper()
        name = adv.local_name or dev.name or ""
        return is_wit_device(name, adv.service_uuids, prefixes)

    dev = await BleakScanner.find_device_by_filter(match, timeout=timeout)
    if dev is None:
        raise TimeoutError(
            "No WT901 device found. Check that it is powered, advertising, and not connected to another app or phone."
        )
    return dev


async def stream(
    device: BLEDevice,
    on_data: Callable[[bytes], None],
    on_connected: Callable[[Writer], Awaitable[None]],
    retries: int = 3,
):
    """Connect, subscribe to the notify characteristic, and run until disconnect or cancel.

    on_connected(write) runs as a task once notifications are flowing; write sends
    bytes to the sensor.
    """
    last_error = None
    for attempt in range(1, retries + 1):
        disconnected = asyncio.Event()
        try:
            async with BleakClient(
                device,
                timeout=20.0,
                disconnected_callback=lambda _c, ev=disconnected: ev.set(),
            ) as client:
                notify, write_uuid = next(
                    (
                        (n, w)
                        for n, w in zip(NOTIFY_UUIDS, WRITE_UUIDS, strict=True)
                        if client.services.get_characteristic(n)
                    ),
                    (None, None),
                )
                if notify is None:
                    raise ConnectionError(
                        "No known sensor data characteristic on this device."
                    )

                async def write(data: bytes, uuid=write_uuid, c=client):
                    await c.write_gatt_char(uuid, data, response=False)

                await client.start_notify(notify, lambda _c, d: on_data(bytes(d)))
                task = asyncio.create_task(on_connected(write))
                try:
                    await disconnected.wait()
                finally:
                    task.cancel()
                print("Device disconnected.")
                return
        except Exception as e:  # noqa: BLE001
            last_error = e
            print(f"Connect attempt {attempt}/{retries} failed: {e}")
            await asyncio.sleep(1.0)
    raise ConnectionError(f"Could not connect: {last_error}")
