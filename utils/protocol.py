"""WitMotion BLE 5.0 (WT901BLE / WT901DCL) GATT UUIDs and frame parser."""

import struct
from collections.abc import Iterator
from dataclasses import dataclass

# GATT layouts: WT901BLE uses the vendor ffe5 service (UUIDs from Wit.BluetoothLE.dll
# of the vendor app); BWT901CL ("HC-06") uses a Microchip ISSC transparent-UART bridge.
SERVICE_UUIDS = (
    "0000ffe5-0000-1000-8000-00805f9a34fb",
    "49535343-fe7d-4ae5-8fa9-9fafd205e455",
)
NOTIFY_UUIDS = (  # sensor -> host, in the order they are tried
    "0000ffe4-0000-1000-8000-00805f9a34fb",
    "49535343-1e4d-4bd9-ba61-23c647249616",
)

WRITE_UUIDS = (  # host -> sensor, same order as NOTIFY_UUIDS
    "0000ffe9-0000-1000-8000-00805f9a34fb",
    "49535343-8841-43f4-a8d4-ecbe34729bb3",
)

ACC_RANGE_G = 16.0
GYRO_RANGE_DPS = 2000.0
ANGLE_RANGE_DEG = 180.0

HEADER = 0x55
FLAG_COMBINED = 0x61  # 20 bytes: acc, gyro, angle
FLAG_ACC = 0x51  # 11 bytes each, older output mode
FLAG_GYRO = 0x52
FLAG_ANGLE = 0x53
FLAG_REGS_BLE = 0x71  # 20 bytes: reply to a register read (WT901BLE)
FLAG_REGS_CL = 0x5F  # 11 bytes: reply to a register read (BWT901CL)

REG_RATE = 0x03  # data output rate (code)
REG_BAUD = 0x04  # serial baud rate (code)

# Register value codes, from the vendor app's jy901s.xml command panel
RATE_HZ = {
    1: "0.2",
    2: "0.5",
    3: "1",
    4: "2",
    5: "5",
    6: "10",
    7: "20",
    8: "50",
    9: "100",
    11: "200",
}
BAUD_BPS = {
    1: 4800,
    2: 9600,
    3: 19200,
    4: 38400,
    5: 57600,
    6: 115200,
    7: 230400,
    8: 460800,
    9: 921600,
}


def read_register_command(reg: int) -> bytes:
    return bytes([0xFF, 0xAA, 0x27, reg, 0x00])


def describe_rate(code: int) -> str:
    if code in RATE_HZ:
        return f"{RATE_HZ[code]} Hz"
    return {12: "single output", 13: "output off"}.get(code, f"unknown (code {code})")


def describe_baud(code: int) -> str:
    return f"{BAUD_BPS[code]} bps" if code in BAUD_BPS else f"unknown (code {code})"


@dataclass
class Sample:
    acc: tuple[float, float, float] | None = None  # g
    gyro: tuple[float, float, float] | None = None  # deg/s
    angle: tuple[float, float, float] | None = None  # deg: roll, pitch, yaw


@dataclass
class RegisterReply:
    """Consecutive register values; start is None if the frame doesn't say (the
    values then begin at whichever register was requested)."""

    start: int | None
    values: tuple[int, ...]


def _scale(vals, full_scale):
    return tuple(v / 32768.0 * full_scale for v in vals)


class FrameParser:
    """Reassembles 0x55-framed packets from arbitrary notification chunks."""

    def __init__(self):
        self._buf = bytearray()

    def feed(self, data: bytes) -> Iterator[Sample | RegisterReply]:
        self._buf.extend(data)
        while True:
            start = self._buf.find(HEADER)
            if start < 0:
                self._buf.clear()
                return
            del self._buf[:start]
            if len(self._buf) < 2:
                return
            flag = self._buf[1]
            if flag in (FLAG_COMBINED, FLAG_REGS_BLE):
                size = 20
            elif flag in (FLAG_ACC, FLAG_GYRO, FLAG_ANGLE, FLAG_REGS_CL):
                size = 11
            else:
                del self._buf[:1]  # false header, resync
                continue
            if len(self._buf) < size:
                return
            frame = bytes(self._buf[:size])
            del self._buf[:size]
            if flag == FLAG_COMBINED:
                v = struct.unpack("<9h", frame[2:])
                yield Sample(
                    _scale(v[0:3], ACC_RANGE_G),
                    _scale(v[3:6], GYRO_RANGE_DPS),
                    _scale(v[6:9], ANGLE_RANGE_DEG),
                )
                continue
            if flag == FLAG_REGS_BLE:
                yield RegisterReply(
                    frame[2] | frame[3] << 8, struct.unpack("<8H", frame[4:])
                )
                continue
            if sum(frame[:10]) & 0xFF != frame[10]:
                continue  # bad checksum
            if flag == FLAG_REGS_CL:
                yield RegisterReply(None, struct.unpack("<4H", frame[2:10]))
                continue
            v = struct.unpack("<3h", frame[2:8])
            if flag == FLAG_ACC:
                yield Sample(acc=_scale(v, ACC_RANGE_G))
            elif flag == FLAG_GYRO:
                yield Sample(gyro=_scale(v, GYRO_RANGE_DPS))
            elif flag == FLAG_ANGLE:
                yield Sample(angle=_scale(v, ANGLE_RANGE_DEG))
