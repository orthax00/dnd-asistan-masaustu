"""Yerel kontrol API'si (yalnızca 127.0.0.1). DnD asistanı gibi başka uygulamalar karakter seçebilir.

    GET  /status              -> {"running": bool, "preset": "...", "presets": [...]}
    POST /preset/<ad>         -> o karaktere geç (ad URL-encoded)
    POST /preset/index/<n>    -> listedeki n. karaktere geç (0'dan başlar)

İstekler `on_command(cmd, arg)` ile arayüz iş parçacığına iletilir; durum `get_status()` ile okunur.
"""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote

DEFAULT_PORT = 47321


class ControlServer:
    def __init__(self, on_command, get_status, port=DEFAULT_PORT):
        self.on_command, self.get_status, self.port = on_command, get_status, port
        self.httpd = None

    def start(self):
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def _send(self, code, obj):
                body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                if self.path.rstrip("/") == "/status":
                    return self._send(200, outer.get_status())
                self._send(404, {"error": "bulunamadı"})

            def do_POST(self):
                parts = [unquote(p) for p in self.path.strip("/").split("/")]
                status = outer.get_status()
                if len(parts) == 3 and parts[:2] == ["preset", "index"] and parts[2].isdigit():
                    i = int(parts[2])
                    if i >= len(status["presets"]):
                        return self._send(404, {"error": "böyle bir sıra yok"})
                    outer.on_command("preset", status["presets"][i])
                    return self._send(200, {"ok": True, "preset": status["presets"][i]})
                if len(parts) == 2 and parts[0] == "preset":
                    if parts[1] not in status["presets"]:
                        return self._send(404, {"error": "böyle bir karakter yok"})
                    outer.on_command("preset", parts[1])
                    return self._send(200, {"ok": True, "preset": parts[1]})
                self._send(404, {"error": "bulunamadı"})

            def log_message(self, *args):
                pass

        self.httpd = ThreadingHTTPServer(("127.0.0.1", self.port), Handler)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def stop(self):
        if self.httpd:
            self.httpd.shutdown()
            self.httpd = None
