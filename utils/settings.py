"""Read the sensor's output-rate and baud-rate registers."""

import asyncio

from .ble import Writer
from .protocol import (
    REG_BAUD,
    REG_RATE,
    RegisterReply,
    describe_baud,
    describe_rate,
    read_register_command,
)


async def read_register(
    write: Writer,
    replies: asyncio.Queue,
    reg: int,
    timeout: float = 1.0,
    tries: int = 3,
) -> int | None:
    """Request one register and wait for its value; None if the sensor never answers."""
    for _ in range(tries):
        while not replies.empty():
            replies.get_nowait()
        await write(read_register_command(reg))
        try:
            async with asyncio.timeout(timeout):
                while True:
                    reply: RegisterReply = await replies.get()
                    first = reg if reply.start is None else reply.start
                    i = reg - first
                    if 0 <= i < len(reply.values):
                        return reply.values[i]
        except TimeoutError:
            continue
    return None


async def describe_settings(write: Writer, replies: asyncio.Queue) -> str:
    """e.g. 'data rate 10 Hz, baud rate 115200 bps'."""
    rate = await read_register(write, replies, REG_RATE)
    baud = await read_register(write, replies, REG_BAUD)
    return (
        f"\tData rate:\t{describe_rate(rate) if rate is not None else 'unavailable'}\n"
        f"\tBaud rate:\t{describe_baud(baud) if baud is not None else 'unavailable'}"
    )
