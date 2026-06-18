"""lmu_app/stream/server.py — HTTP server + render loop for stream overlays."""
from __future__ import annotations

import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from PySide6.QtCore import QBuffer, QObject, QPoint, Qt, QTimer
from PySide6.QtGui import QPixmap, QRegion
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
    "#bc-tower  { left:8px; top:8px; }"
    "#bc-battle { left:calc(50vw - 200px); bottom:30px; }"
    "#bc-driver { left:calc(50vw - 180px); bottom:30px; }"
    "</style></head><body>"
    "<img id='bc-tower'><img id='bc-battle'><img id='bc-driver'>"
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
            f"<h2>LMU App — Stream overlays</h2><ul>{rows}</ul></body></html>"
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

def render_widget_png(widget: QWidget) -> bytes:
    """Render a (possibly hidden) Qt widget to a transparent PNG in memory."""
    w = widget.width() or widget.sizeHint().width() or 1
    h = widget.height() or widget.sizeHint().height() or 1
    widget.ensurePolished()
    px = QPixmap(w, h)
    px.fill(Qt.GlobalColor.transparent)
    # Use positional args — PySide6 keyword is 'renderFlags', not 'flags'
    widget.render(px, QPoint(0, 0), QRegion(), QWidget.RenderFlag.DrawChildren)
    buf = QBuffer()
    buf.open(QBuffer.OpenModeFlag.WriteOnly)
    px.save(buf, "PNG")
    data = bytes(buf.data())
    logger.debug("render_widget_png %s: %dx%d → %d bytes", widget.__class__.__name__, w, h, len(data))
    return data


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

        self._timer = QTimer(self)
        self._timer.setInterval(50)   # 20 fps
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

        srv = StreamServer(port, self._placeholder)
        ok  = srv.try_start()
        if ok:
            self._server = srv
            for name in self._widgets:
                srv.add_name(name)
            self._timer.start()
        return ok

    def stop(self) -> None:
        self._timer.stop()
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
        snap = self._reader.get()
        in_garage = self._hide_in_garage and snap.player_in_garage
        for key in list(self._enabled):
            widget = self._widgets.get(key)
            if widget is None:
                continue
            if in_garage:
                if self._placeholder:
                    self._server.set_frame(key, self._placeholder)
                continue
            if snap.game_running and snap.session_active:
                try:
                    widget.on_data(snap)
                except Exception:
                    pass
            try:
                png = render_widget_png(widget)
                self._server.set_frame(key, png)
            except Exception as exc:
                logger.warning("Stream render error (%s): %s", key, exc)
