import os
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler


class ImageRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory="images", **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()


def start_image_server(port=8080):
    """画像サーバーを起動"""
    try:
        # 画像ディレクトリが存在しない場合は作成
        os.makedirs("images", exist_ok=True)
        server = HTTPServer(("localhost", port), ImageRequestHandler)
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        print(f"Image server started on http://localhost:{port}")
        return server
    except Exception as e:
        print(f"Failed to start image server: {e}")
        return None
