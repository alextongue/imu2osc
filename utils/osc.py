"""OSC output of IMU samples."""

import socket

from pythonosc.osc_bundle_builder import IMMEDIATELY, OscBundleBuilder
from pythonosc.osc_message_builder import OscMessageBuilder
from pythonosc.udp_client import SimpleUDPClient

AXES = "XYZ"


class OscSender:
    """Sends one OSC bundle per sample: accel to /imu/A{X,Y,Z}, gyro to /imu/G{X,Y,Z},
    and roll/pitch/yaw to /imu/ang{X,Y,Z}."""

    def __init__(self, host: str = "localhost", port: int = 45533):
        # "localhost" can resolve to ::1 first, which IPv4-only OSC receivers never
        # see, so resolve to an IPv4 address explicitly.
        self._client = SimpleUDPClient(socket.gethostbyname(host), port)

    def send(self, acc, gyro, angle):
        bundle = OscBundleBuilder(IMMEDIATELY)
        for prefix, values in (("A", acc), ("G", gyro), ("ang", angle)):
            for axis, value in zip(AXES, values, strict=True):
                msg = OscMessageBuilder(f"/imu/{prefix}{axis}")
                msg.add_arg(float(value))
                bundle.add_content(msg.build())
        self._client.send(bundle.build())
