"""hypertrace/calc/ext/ws_merge.py — LMU local WebSocket enrichment (penalty type).

Same isolation rule as rest_merge.py: this is the only place that opens this
WebSocket, on its own background thread, writing into `minfo`.

mNumPenalties (shared memory, see module_vehicles.py's `penalties` field) is
only ever a bare count — no type. LMU exposes the actual type on the same
machine, no multiplayer/server connection needed, over a WebSocket next to
the REST port: `ws://localhost:<REST port + 1>/websocket/ui`, subscribed
with `{"messageType":"SUB","topic":"LiveStandings"}`. Confirmed by
decompiling LMU Broadcast Control (ilspycmd) — it reads this exact feed for
its own penalty display, `PcConnectionContext.cs`'s `OnWsUiMessage` parses a
`penalties: {"DT": n, "SG": n, "TIME": n}` object per car in each `UPDATE`
message's `body` array.

No `websockets` package dependency: a small raw-socket client is enough for
one persistent read-only subscription, and matches this app's existing
REST/HTTP code (rest_merge.py, widgets/live_timing.py) already talking to
`localhost:6397`-and-friends by hand rather than pulling in an HTTP/WS
library for a couple of endpoints.

REMOVE ME — this whole file, its wiring in calc/module_control.py, and
VehiclesInfo.penaltyTypes in calc/module_info.py — the day mNumPenalties is
replaced with (or joined by) a real shared-memory penalty-type field. That
would make this entire module redundant.
"""
from __future__ import annotations

import base64
import json
import logging
import os
import socket
import struct
import threading
import time

from hypertrace.calc.module_info import minfo
from hypertrace.calc.realtime_state import realtime_state

logger = logging.getLogger(__name__)

_HOST = "127.0.0.1"
_PORT = 6398   # LMU's REST port (6397, see rest_merge.py) + 1 — same process, same lifetime.
_PATH = "/websocket/ui"
_SUB_MESSAGE = json.dumps({"messageType": "SUB", "topic": "LiveStandings"})
_IDLE_INTERVAL = 1.0    # while not live, and between reconnect attempts
_RECV_TIMEOUT = 2.0     # so the receive loop can notice a stop request promptly


def _recv_exact(sock: socket.socket, n: int) -> bytes | None:
    if n == 0:
        return b""
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            return None
        buf += chunk
    return buf


def _ws_handshake(sock: socket.socket) -> None:
    key = base64.b64encode(os.urandom(16)).decode()
    req = (
        f"GET {_PATH} HTTP/1.1\r\n"
        f"Host: {_HOST}:{_PORT}\r\n"
        f"Upgrade: websocket\r\n"
        f"Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        f"Sec-WebSocket-Version: 13\r\n"
        f"\r\n"
    ).encode()
    sock.sendall(req)
    resp = b""
    while b"\r\n\r\n" not in resp:
        chunk = sock.recv(4096)
        if not chunk:
            raise ConnectionError("WS handshake: connection closed")
        resp += chunk
    if b" 101 " not in resp.split(b"\r\n", 1)[0]:
        raise ConnectionError(f"WS handshake failed: {resp[:100]!r}")


def _ws_send(sock: socket.socket, opcode: int, payload: bytes) -> None:
    # Client-to-server frames must be masked (RFC 6455) — server frames never
    # are, that asymmetry is why _ws_recv_frame below always checks the mask
    # bit instead of assuming either way.
    mask_key = os.urandom(4)
    masked = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload))
    n = len(payload)
    if n < 126:
        header = struct.pack("BB", 0x80 | opcode, 0x80 | n)
    elif n < 65536:
        header = struct.pack("!BBH", 0x80 | opcode, 0x80 | 126, n)
    else:
        header = struct.pack("!BBQ", 0x80 | opcode, 0x80 | 127, n)
    sock.sendall(header + mask_key + masked)


def _ws_recv_frame(sock: socket.socket) -> tuple[int, bytes] | None:
    hdr = _recv_exact(sock, 2)
    if hdr is None:
        return None
    b0, b1 = hdr[0], hdr[1]
    opcode = b0 & 0x0F
    masked = b1 & 0x80
    length = b1 & 0x7F
    if length == 126:
        ext = _recv_exact(sock, 2)
        if ext is None:
            return None
        length = struct.unpack(">H", ext)[0]
    elif length == 127:
        ext = _recv_exact(sock, 8)
        if ext is None:
            return None
        length = struct.unpack(">Q", ext)[0]
    mask_key = _recv_exact(sock, 4) if masked else b""
    if masked and mask_key is None:
        return None
    payload = _recv_exact(sock, length)
    if payload is None:
        return None
    if masked:
        payload = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload))
    return opcode, payload


def _apply_update(message: str) -> None:
    try:
        data = json.loads(message)
    except Exception:
        return
    if data.get("messageType") != "UPDATE" or data.get("topic") != "LiveStandings":
        return
    body = data.get("body")
    if not isinstance(body, list):
        return
    by_slot: dict[int, tuple[int, int, int]] = {}
    for car in body:
        try:
            slot = int(car.get("slotID", -1))
        except (TypeError, ValueError):
            continue
        pen = car.get("penalties") or {}
        by_slot[slot] = (
            int(pen.get("DT", 0) or 0),
            int(pen.get("SG", 0) or 0),
            int(pen.get("TIME", 0) or 0),
        )
    if not by_slot:
        return
    # Written onto minfo.vehicles.penaltyTypes, NOT the matching VehicleData
    # in dataSet — that list is rebuilt from scratch by module_vehicles.py
    # roughly every 100ms, on its own thread, at its own cadence. Writing
    # per-car fields directly raced against that rebuild (this thread's
    # update landing, then immediately getting wiped by the next scan before
    # the widget ever read it) and made the tag flicker between the known
    # type and the shared-memory bare count. This dict survives every
    # rebuild untouched, so a slot's last known (DT, SG, TIME) — including
    # genuinely (0, 0, 0), once actually served — stays put until this
    # reports something new for it.
    minfo.vehicles.penaltyTypes.update(by_slot)


class WsMerge:
    def __init__(self) -> None:
        self._running = False
        self._thread: threading.Thread | None = None

    @property
    def running(self) -> bool:
        """Whether the WS thread is currently active (not necessarily connected —
        see is_connected for that)."""
        return self._running

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, name="LMUWsMerge", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
        # penaltyTypes is the one thing this module writes that doesn't
        # self-clear on its own (see _apply_update) — nothing else ever
        # resets it, so a stale entry would otherwise linger and could even
        # end up mislabeling a different car if slot IDs get reused.
        minfo.vehicles.penaltyTypes.clear()

    def _loop(self) -> None:
        while self._running:
            # Same gate rest_merge.py uses and for the same reason: nothing to
            # enrich while module_vehicles isn't refreshing minfo.vehicles
            # either, and this shouldn't hammer localhost:6398 with connect
            # attempts for as long as the app sits open with LMU closed.
            if not realtime_state.live:
                time.sleep(_IDLE_INTERVAL)
                continue
            try:
                self._run_connection()
            except Exception as exc:
                logger.debug("ws_merge: connection ended (%s)", exc)
            if self._running:
                time.sleep(_IDLE_INTERVAL)

    def _run_connection(self) -> None:
        sock = socket.create_connection((_HOST, _PORT), timeout=3)
        try:
            sock.settimeout(3)
            _ws_handshake(sock)
            _ws_send(sock, 0x1, _SUB_MESSAGE.encode())
            sock.settimeout(_RECV_TIMEOUT)
            while self._running and realtime_state.live:
                try:
                    result = _ws_recv_frame(sock)
                except socket.timeout:
                    continue
                if result is None:
                    break
                opcode, payload = result
                if opcode == 0x1:       # text
                    _apply_update(payload.decode(errors="replace"))
                elif opcode == 0x9:     # ping -> pong
                    _ws_send(sock, 0xA, payload)
                elif opcode == 0x8:     # close
                    break
        finally:
            sock.close()


ws_merge = WsMerge()
