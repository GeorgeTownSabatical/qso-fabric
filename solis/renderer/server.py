from __future__ import annotations

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def run(host: str = "0.0.0.0", port: int = 9100) -> None:
    web_root = Path(__file__).resolve().parent / "web"

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(web_root), **kwargs)

    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Solis renderer serving {web_root} on {host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
