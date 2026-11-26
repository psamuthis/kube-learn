"""A tiny web server for exercise 1.1."""
import os
import socket
from http.server import BaseHTTPRequestHandler, HTTPServer


class Hello(BaseHTTPRequestHandler):
    def do_GET(self):
        body = f"hello from {socket.gethostname()} as uid {os.getuid()}\n".encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    print("listening on :8000", flush=True)
    HTTPServer(("0.0.0.0", 8000), Hello).serve_forever()
