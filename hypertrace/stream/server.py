"""hypertrace/stream/server.py — HTTP server + render loop for stream overlays."""
from __future__ import annotations

import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from PySide6.QtCore import QBuffer, QObject, QPoint, Qt, QTimer
from PySide6.QtGui import QImage, QPixmap, QRegion
from PySide6.QtWidgets import QWidget

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# HTML template served per overlay
# ---------------------------------------------------------------------------

_HTML = """\
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:transparent; overflow:hidden; display:inline-block; }}
img {{ display:block; }}
</style>
</head>
<body>
<img id="f">
<script>
const img = document.getElementById('f');
const url = '/api/{name}.png';
let busy = false;
function tick() {{
  if (busy) return;
  busy = true;
  const ni = new Image();
  ni.onload = () => {{ img.src = ni.src; busy = false; requestAnimationFrame(tick); }};
  ni.onerror = () => {{ busy = false; setTimeout(tick, 250); }};
  ni.src = url + '?t=' + Date.now();
}}
tick();
</script>
</body>
</html>
"""

_INDEX_ROW = '<li><a href="/{name}">{name}</a> — <code>http://localhost:{{port}}/{name}</code></li>'

_BROADCAST_HTML = (
    "<!DOCTYPE html><html><head><meta charset='utf-8'><style>"
    "* { margin:0; padding:0; }"
    "html,body { background:transparent; overflow:hidden; }"
    "img { position:fixed; display:block; }"
    "#bc-tower   { left:8px; top:8px; }"
    "#bc-battle  { left:calc(50vw - 240px); bottom:30px; }"
    "#bc-driver  { left:calc(50vw - 180px); bottom:30px; }"
    "#bc-sectors { left:calc(50vw - 180px); bottom:30px; }"
    "</style></head><body>"
    "<img id='bc-tower'><img id='bc-battle'><img id='bc-driver'><img id='bc-sectors'>"
    "<script>"
    "function poll(id,name){"
    "const img=document.getElementById(id);let busy=false;"
    "function tick(){if(busy)return;busy=true;"
    "const ni=new Image();"
    "ni.onload=()=>{img.src=ni.src;busy=false;requestAnimationFrame(tick);};"
    "ni.onerror=()=>{busy=false;setTimeout(tick,250);};"
    "ni.src='/api/'+name+'.png?t='+Date.now();}"
    "tick();}"
    "poll('bc-tower','bc_tower');"
    "poll('bc-battle','bc_battle');"
    "poll('bc-driver','bc_driver');"
    "poll('bc-sectors','bc_sectors');"
    "</script></body></html>"
)

# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------

class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # type: ignore[override]
        path = self.path.split("?")[0]

        if path == "/":
            self._index()
        elif path == "/broadcast":
            self._broadcast_page()
        elif path.startswith("/api/") and path.endswith(".png"):
            self._frame(path[5:-4])
        elif path.lstrip("/"):
            self._page(path.lstrip("/"))
        else:
            self._404()

    def _broadcast_page(self) -> None:
        body = _BROADCAST_HTML.encode()
        self._send(200, "text/html; charset=utf-8", body)

    def _index(self) -> None:
        srv: StreamServer = self.server  # type: ignore[assignment]
        rows = "\n".join(
            f'<li><a href="/{n}">{n}</a> &nbsp; '
            f'<code>http://localhost:{srv.port}/{n}</code></li>'
            for n in sorted(srv.names())
        )
        body = (
            f"<html><body style='font-family:monospace;padding:16px'>"
            f"<h2>HyperTrace — Stream overlays</h2><ul>{rows}</ul></body></html>"
        ).encode()
        self._send(200, "text/html; charset=utf-8", body)

    def _page(self, name: str) -> None:
        srv: StreamServer = self.server  # type: ignore[assignment]
        if name not in srv.names():
            self._404(); return
        body = _HTML.format(name=name).encode()
        self._send(200, "text/html; charset=utf-8", body)

    def _frame(self, name: str) -> None:
        srv: StreamServer = self.server  # type: ignore[assignment]
        data = srv.get_frame(name)
        if data is None:
            self._404(); return
        self._send(200, "image/png", data,
                   extra=[("Cache-Control", "no-cache, no-store"),
                           ("Access-Control-Allow-Origin", "*")])

    def _send(self, code: int, ctype: str, body: bytes,
              extra: list[tuple[str, str]] | None = None) -> None:
        try:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            for k, v in (extra or []):
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)
        except (ConnectionAbortedError, BrokenPipeError, ConnectionResetError):
            pass

    def _404(self) -> None:
        self.send_response(404); self.end_headers()

    def log_message(self, *_) -> None:  # suppress request logs
        pass


# ---------------------------------------------------------------------------
# HTTP server
# ---------------------------------------------------------------------------

class StreamServer(HTTPServer):
    """Thread-safe HTTP server that stores the latest PNG frame per overlay."""

    def __init__(self, port: int, placeholder: bytes = b"") -> None:
        self._srv_port    = port
        self._frames: dict[str, bytes] = {}
        self._names:  set[str]         = set()
        self._lock        = threading.Lock()
        self._placeholder = placeholder

    # ------------------------------------------------------------------
    def try_start(self) -> bool:
        try:
            super().__init__(("", self._srv_port), _Handler)
            self._thread = threading.Thread(target=self.serve_forever, daemon=True)
            self._thread.start()
            logger.info("Stream server started on port %d", self._srv_port)
            return True
        except OSError as exc:
            logger.error("Stream server could not start (port %d): %s", self._srv_port, exc)
            return False

    def try_stop(self) -> None:
        try:
            self.shutdown()
        except Exception:
            pass
        logger.info("Stream server stopped")

    # ------------------------------------------------------------------
    def set_frame(self, name: str, data: bytes) -> None:
        with self._lock:
            self._frames[name] = data

    def get_frame(self, name: str) -> bytes | None:
        with self._lock:
            return self._frames.get(name) or (self._placeholder if self._placeholder else None)

    def add_name(self, name: str) -> None:
        with self._lock:
            self._names.add(name)

    def names(self) -> set[str]:
        with self._lock:
            return set(self._names)

    @property
    def port(self) -> int:
        return self._srv_port


# ---------------------------------------------------------------------------
# Render-to-PNG helper
# ---------------------------------------------------------------------------

def render_widget_qimage(widget: QWidget) -> QImage:
    """Render a (possibly hidden) Qt widget to a transparent QImage.

    MUST be called on the GUI thread (it paints the widget). The returned
    QImage can then be PNG-encoded on a worker thread — see encode_png() —
    so the expensive zlib compression never blocks the GUI event loop.
    """
    w = widget.width() or widget.sizeHint().width() or 1
    h = widget.height() or widget.sizeHint().height() or 1
    widget.ensurePolished()
    img = QImage(w, h, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    # Use positional args — PySide6 keyword is 'renderFlags', not 'flags'
    widget.render(img, QPoint(0, 0), QRegion(), QWidget.RenderFlag.DrawChildren)
    return img


def encode_png(img: QImage) -> bytes:
    """PNG-encode a QImage to bytes. Thread-safe — safe to call off the GUI thread."""
    buf = QBuffer()
    buf.open(QBuffer.OpenModeFlag.WriteOnly)
    img.save(buf, "PNG")
    data = bytes(buf.data())
    buf.close()
    return data


def render_widget_png(widget: QWidget) -> bytes:
    """Render a widget straight to PNG bytes (GUI thread only). Convenience wrapper."""
    return encode_png(render_widget_qimage(widget))


# ---------------------------------------------------------------------------
# Stream manager (lives in Qt main thread)
# ---------------------------------------------------------------------------

class StreamManager(QObject):
    """
    Manages a set of hidden stream widgets.
    On each tick: feeds data → renders each enabled widget → pushes PNG to server.
    """

    def __init__(self, reader, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._reader        = reader
        self._server: StreamServer | None = None
        self._widgets: dict[str, QWidget] = {}
        self._enabled: set[str]           = set()
        self._hide_in_garage: bool        = False
        self._placeholder: bytes          = b""
        self._last_render: dict[str, float] = {}   # key → monotonic time of last render

        # PNG encoding runs on a dedicated worker thread so the heavy zlib
        # compression never blocks the GUI thread (which would stutter the
        # on-screen overlays). GUI thread only does widget.render() → QImage.
        self._enc_lock    = threading.Lock()
        self._enc_pending: dict[str, QImage] = {}   # key → latest QImage (latest-wins)
        self._enc_event   = threading.Event()
        self._enc_thread: threading.Thread | None = None
        self._enc_running = False
        self._on_data_wants_snap: dict[str, bool] = {}   # cached per-widget-key signature check

        self._timer = QTimer(self)
        self._timer.setInterval(16)   # ~60 fps tick — per-widget throttling handles actual rate
        self._timer.timeout.connect(self._tick)

    # ------------------------------------------------------------------
    def start(self, port: int) -> bool:
        if self._server is not None:
            self._server.try_stop()
        # Generate 1×1 transparent PNG in main Qt thread (Qt-safe)
        ph_px = QPixmap(1, 1)
        ph_px.fill(Qt.GlobalColor.transparent)
        ph_buf = QBuffer()
        ph_buf.open(QBuffer.OpenModeFlag.WriteOnly)
        ph_px.save(ph_buf, "PNG")
        self._placeholder = bytes(ph_buf.data())
        ph_buf.close()

        srv = StreamServer(port, self._placeholder)
        ok  = srv.try_start()
        if ok:
            self._server = srv
            for name in self._widgets:
                srv.add_name(name)
            self._enc_running = True
            self._enc_thread = threading.Thread(
                target=self._encoder_loop, name="StreamEncoder", daemon=True)
            self._enc_thread.start()
            self._timer.start()
        return ok

    def _encoder_loop(self) -> None:
        """Worker: drains pending QImages, PNG-encodes them, pushes to server."""
        while self._enc_running:
            self._enc_event.wait(0.5)
            self._enc_event.clear()
            with self._enc_lock:
                batch = self._enc_pending
                self._enc_pending = {}
            for key, img in batch.items():
                try:
                    png = encode_png(img)
                    if self._server is not None:
                        self._server.set_frame(key, png)
                except Exception as exc:
                    logger.warning("Stream encode error (%s): %s", key, exc)

    def stop(self) -> None:
        self._timer.stop()
        self._enc_running = False
        self._enc_event.set()
        if self._enc_thread is not None:
            self._enc_thread.join(timeout=1.0)
            self._enc_thread = None
        with self._enc_lock:
            self._enc_pending.clear()
        if self._server is not None:
            # Push transparent placeholder so OBS clears before server stops
            if self._placeholder:
                for name in self._server.names():
                    self._server.set_frame(name, self._placeholder)
                import time; time.sleep(0.25)
            self._server.try_stop()
            self._server = None

    def set_hide_in_garage(self, hide: bool) -> None:
        self._hide_in_garage = hide

    @property
    def is_running(self) -> bool:
        return self._server is not None

    # ------------------------------------------------------------------
    def add_widget(self, key: str, widget: QWidget) -> None:
        self._widgets[key] = widget
        if self._server:
            self._server.add_name(key)

    def set_widget_enabled(self, key: str, enabled: bool) -> None:
        if enabled:
            self._enabled.add(key)
        else:
            self._enabled.discard(key)
            if self._server and self._placeholder:
                self._server.set_frame(key, self._placeholder)

    # ------------------------------------------------------------------
    def _tick(self) -> None:
        if self._server is None:
            return
        import time as _time
        now = _time.monotonic()
        snap = self._reader.get()
        in_garage = self._hide_in_garage and snap.player_in_garage
        for key in list(self._enabled):
            widget = self._widgets.get(key)
            if widget is None:
                continue
            # Per-widget rate throttling: respect stream_hz attribute (default 30)
            hz = getattr(widget, "stream_hz", 30)
            if now - self._last_render.get(key, 0.0) < 1.0 / hz:
                continue
            self._last_render[key] = now
            if in_garage:
                if self._placeholder:
                    self._server.set_frame(key, self._placeholder)
                continue
            if snap.game_running and snap.session_active:
                try:
                    # Migrated widgets read hypertrace.calc.module_info.minfo
                    # directly and take no argument; the still-on-hold
                    # broadcast/live-timing widgets still expect the legacy
                    # snapshot object — checked once per widget and cached.
                    wants_snap = self._on_data_wants_snap.get(key)
                    if wants_snap is None:
                        import inspect
                        try:
                            wants_snap = len(inspect.signature(widget.on_data).parameters) >= 1
                        except (TypeError, ValueError):
                            wants_snap = True
                        self._on_data_wants_snap[key] = wants_snap
                    widget.on_data(snap) if wants_snap else widget.on_data()
                except Exception:
                    pass
            try:
                img = render_widget_qimage(widget)          # GUI thread (light)
                with self._enc_lock:
                    self._enc_pending[key] = img             # latest-wins, no backlog
                self._enc_event.set()                        # wake encoder thread
            except Exception as exc:
                logger.warning("Stream render error (%s): %s", key, exc)
