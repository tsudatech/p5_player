import os
import webview
import json
import uuid
from pynput import mouse
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading

render_window = None
editor_window = None
track_window = None
code_blocks = []
selected_code_id = None
track_blocks = []
track_bpm = 120
track_delay = 0
DATA_FILE = "data/code_blocks.json"
TRACK_FILE = "data/track_data.json"
click_to_play_enabled = False
image_server_port = 8080


class ImageRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory="images", **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()


def start_image_server():
    """画像サーバーを起動"""
    try:
        # 画像ディレクトリが存在しない場合は作成
        os.makedirs("images", exist_ok=True)

        server = HTTPServer(("localhost", image_server_port), ImageRequestHandler)
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        print(f"Image server started on http://localhost:{image_server_port}")
        return server
    except Exception as e:
        print(f"Failed to start image server: {e}")
        return None


# ---- 永続化用の関数 ----
def load_blocks():
    global code_blocks, selected_code_id
    # dataフォルダが存在しない場合は作成
    os.makedirs("data", exist_ok=True)

    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                code_blocks = data.get("blocks", [])
                selected_code_id = data.get("selected_code_id", None)
        except Exception as e:
            print("Error loading data:", e)
            code_blocks = []
            selected_code_id = None


def save_blocks():
    # dataフォルダが存在しない場合は作成
    os.makedirs("data", exist_ok=True)

    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(
                {"blocks": code_blocks, "selected_code_id": selected_code_id},
                f,
                ensure_ascii=False,
                indent=2,
            )
    except Exception as e:
        print("Error saving data:", e)


def load_track_data():
    global track_blocks, track_bpm, track_delay
    # dataフォルダが存在しない場合は作成
    os.makedirs("data", exist_ok=True)

    if os.path.exists(TRACK_FILE):
        try:
            with open(TRACK_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                track_blocks = data.get("track_blocks", [])
                track_bpm = data.get("bpm", 120)
                track_delay = data.get("delay", 0)
        except Exception as e:
            print("Error loading track data:", e)
            track_blocks = []
            track_bpm = 120
            track_delay = 0


def save_track_data():
    global track_bpm, track_delay
    # dataフォルダが存在しない場合は作成
    os.makedirs("data", exist_ok=True)

    try:
        with open(TRACK_FILE, "w", encoding="utf-8") as f:
            json.dump(
                {"bpm": track_bpm, "delay": track_delay, "track_blocks": track_blocks},
                f,
                ensure_ascii=False,
                indent=2,
            )
    except Exception as e:
        print("Error saving track data:", e)


def update_render_window(code: str):
    """iframeごと作り直してp5.jsスケッチを安全に再注入"""
    global render_window, image_server_port
    if render_window:
        # バッククォートとバックスラッシュをエスケープ
        escaped_code = code.replace("\\", "\\\\")
        escaped_code = escaped_code.replace("`", "\\`")
        escaped_code = escaped_code.replace("$", "\\$")
        escaped_code = escaped_code.replace(
            'loadImage("images', f'loadImage("http://localhost:{image_server_port}'
        )

        js_code = f"""
        // 既存のiframeを削除
        const oldFrame = document.getElementById("p5-frame");
        if (oldFrame) oldFrame.remove();

        // 新しいiframeを作成
        const iframe = document.createElement("iframe");
        iframe.id = "p5-frame";
        iframe.style.border = "none";
        iframe.style.width = "100vw";
        iframe.style.height = "100vh";

        // srcdocでp5ライブラリとスケッチを注入
        iframe.srcdoc = `
          <!DOCTYPE html>
          <html>
          <head>
            <meta charset="utf-8" />
            <style>
              body {{
                margin: 0;
                padding: 0;
                overflow: hidden;
              }}
              canvas {{
                display: block;
              }}
            </style>
            <script src="https://cdn.jsdelivr.net/npm/p5@1.9.2/lib/p5.min.js"></script>
          </head>
          <body>
            <script>
              {escaped_code}
            <\/script>
          </body>
          </html>
        `;

        document.body.appendChild(iframe);
        """

        render_window.evaluate_js(js_code)


def on_click(x, y, button, pressed):
    global track_window, click_to_play_enabled
    if pressed:
        print(f"Mouse clicked at ({x}, {y}) with {button}")

        # トグルがONの時のみplayを発火
        if click_to_play_enabled:
            print(f"Click to play enabled! Triggering play...")
            if track_window:
                # トラックウィンドウにplayコマンドを送信
                time.sleep(track_delay / 1000.0)  # Convert ms to seconds
                track_window.evaluate_js("playCurrentTrack()")
        else:
            print(f"Click to play disabled - ignoring click")


# キー押下のタイミングを記録
key_press_times = {}


def on_key_press(key):
    global render_window, editor_window, track_window, key_press_times
    try:
        if hasattr(key, "char"):
            current_time = time.time()
            key_char = key.char.lower()

            # 前回の押下時刻を取得
            last_press_time = key_press_times.get(key_char, 0)

            # 0.5秒以内の連続押下を検出
            if current_time - last_press_time < 0.5:
                if key_char == "h":
                    print("Double H pressed - hiding all windows")
                    if render_window:
                        render_window.hide()
                    if editor_window:
                        editor_window.hide()
                    if track_window:
                        track_window.hide()
                elif key_char == "s":
                    print("Double S pressed - showing all windows")
                    if render_window:
                        render_window.show()
                    if editor_window:
                        editor_window.show()
                    if track_window:
                        track_window.show()
                # 連続押下を検出したらタイミングをリセット
                key_press_times[key_char] = 0
            else:
                # 初回押下の時刻を記録
                key_press_times[key_char] = current_time

    except AttributeError:
        pass


def start_mouse_listener():
    """マウスリスナーとキーボードリスナーを別スレッドで起動"""
    print("start_mouse_listener")
    from pynput import keyboard

    listener = mouse.Listener(on_click=on_click)
    key_listener = keyboard.Listener(on_press=on_key_press)
    listener.start()
    key_listener.start()
    return listener, key_listener


class EditorAPI:
    def add_block(self):
        global code_blocks, selected_code_id
        new_block = {
            "id": str(uuid.uuid4()),
            "name": f"Block {len(code_blocks) + 1}",
            "code": "// New p5.js sketch\n"
            "function setup() {\n"
            "  createCanvas(400, 400);\n"
            "}\n\n"
            "function draw() {\n"
            "  background(220);\n"
            "}",
        }
        code_blocks.append(new_block)
        selected_code_id = new_block["id"]
        save_blocks()
        return {"blocks": code_blocks, "selected_code_id": selected_code_id}

    def add_block_to_track(self, index):
        """ブロックをトラックに追加"""
        global code_blocks, track_window
        if 0 <= index < len(code_blocks):
            block = code_blocks[index]
            if track_window:
                track_window.evaluate_js(f"addTrackBlock({block})")
            return {"status": "success"}
        return {"status": "error", "message": "Invalid block index"}

    def select_block(self, index):
        global selected_code_id
        if 0 <= index < len(code_blocks):
            selected_code_id = code_blocks[index]["id"]
            save_blocks()
            return code_blocks[index]["code"]
        return ""

    def update_block(self, code):
        global code_blocks, selected_code_id
        if selected_code_id is not None:
            for block in code_blocks:
                if block["id"] == selected_code_id:
                    block["code"] = code
                    save_blocks()
                    update_render_window(code)
                    break
        return {"blocks": code_blocks, "selected_code_id": selected_code_id}

    def update_block_name(self, index, name):
        global code_blocks
        if 0 <= index < len(code_blocks):
            code_blocks[index]["name"] = name
            save_blocks()
        return {"blocks": code_blocks, "selected_code_id": selected_code_id}

    def get_block_by_id(self, block_id):
        """IDでブロックを取得"""
        for i, block in enumerate(code_blocks):
            if block.get("id") == block_id:
                return {"block": block, "index": i}
        return None

    def reorder_blocks(self, new_blocks, moved_block_id=None):
        global code_blocks, selected_code_id
        code_blocks = new_blocks

        # 移動したブロックのIDが指定されている場合は、それを選択状態にする
        if moved_block_id is not None:
            selected_code_id = moved_block_id

        save_blocks()
        return {"blocks": code_blocks, "selected_code_id": selected_code_id}

    def delete_block(self, index):
        global code_blocks, selected_code_id
        if 0 <= index < len(code_blocks):
            # 削除するブロックのID
            deleted_block_id = code_blocks[index]["id"]

            # 削除するブロックが現在選択されている場合
            if selected_code_id == deleted_block_id:
                # 次のブロックを選択、なければ前のブロックを選択
                if index < len(code_blocks) - 1:
                    selected_code_id = code_blocks[index + 1]["id"]
                elif index > 0:
                    selected_code_id = code_blocks[index - 1]["id"]
                else:
                    selected_code_id = None

            # ブロックを削除
            code_blocks.pop(index)

            save_blocks()
            return {"blocks": code_blocks, "selected_code_id": selected_code_id}
        return None

    def get_all_blocks(self):
        global code_blocks, selected_code_id, render_window
        return {"blocks": code_blocks, "selected_code_id": selected_code_id}

    def load_first_block(self):
        global code_blocks, selected_code_id, render_window
        if code_blocks:
            selected_code_id = code_blocks[0]["id"]
            code = code_blocks[0]["code"]
            update_render_window(code)
            return {"code": code, "selected_code_id": selected_code_id}
        else:
            # ブロックが空なら何もしない
            return {"code": "", "selected_code_id": None}


class RenderAPI:
    def notify_ready(self):
        # 初期化完了の通知（必要に応じて追加の処理を行う）
        pass


class TrackAPI:
    def play_track_block(self, code):
        """トラックウィンドウから送信されたコードを実行"""
        global render_window
        if render_window:
            update_render_window(code)
        return {"status": "success"}

    def get_track_blocks(self):
        """トラックブロックの一覧を取得"""
        global track_blocks, track_bpm, track_delay
        return {"track_blocks": track_blocks, "bpm": track_bpm, "delay": track_delay}

    def save_track_blocks(self, blocks):
        """トラックブロックを保存"""
        global track_blocks
        track_blocks = blocks
        save_track_data()
        return {"status": "success"}

    def update_bpm(self, bpm):
        """BPMを更新"""
        global track_bpm
        track_bpm = bpm
        save_track_data()
        return {"status": "success"}

    def update_delay(self, delay):
        """Delay timeを更新"""
        global track_delay
        track_delay = delay
        save_track_data()
        return {"status": "success"}

    def hide_all_windows(self):
        """全てのウィンドウを隠す"""
        global render_window, editor_window, track_window
        if render_window:
            render_window.hide()
        if editor_window:
            editor_window.hide()
        if track_window:
            track_window.hide()
        return {"status": "success"}

    def show_all_windows(self):
        """全てのウィンドウを表示"""
        global render_window, editor_window, track_window
        if render_window:
            render_window.show()
        if editor_window:
            editor_window.show()
        if track_window:
            track_window.show()
        return {"status": "success"}

    def add_track_block(self, block_data):
        """トラックにブロックを追加"""
        global track_blocks
        track_blocks.append(block_data)
        save_track_data()
        return {"status": "success", "track_blocks": track_blocks}

    def update_click_to_play_state(self, enabled):
        """クリック再生の有効/無効状態を更新"""
        global click_to_play_enabled
        click_to_play_enabled = enabled
        print(f"Click to play state updated: {enabled}")
        return {"status": "success"}


if __name__ == "__main__":
    load_blocks()
    load_track_data()

    # 画像サーバーを起動
    image_server = start_image_server()

    editor_api = EditorAPI()
    render_api = RenderAPI()
    track_api = TrackAPI()

    # 固定のベースHTML（常に同じ構造を使用）
    initial_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {
                margin: 0;
                padding: 0;
                background: transparent;
                overflow: hidden;
            }
            canvas {
                display: block;
            }
        </style>
    </head>
    <body>
    </body>
    </html>
    """

    # 最初のブロックがある場合は初期化時にscriptタグを追加
    if code_blocks:
        selected_code_id = code_blocks[0]["id"]

    render_window = webview.create_window(
        "Transparent Always on Top p5.js",
        html=initial_html,
        js_api=render_api,
        width=1000,
        height=1000,
        x=0,
        y=250,
        frameless=True,
        transparent=True,
        on_top=True,
    )

    editor_window = webview.create_window(
        "Code Editor",
        "view/editor/index.html",
        js_api=editor_api,
        width=1000,
        height=1000,
        x=1000,
        y=250,
        on_top=True,
    )

    track_window = webview.create_window(
        "Track Window",
        "view/track/index.html",
        js_api=track_api,
        width=2000,
        height=200,
        x=0,
        y=0,
        on_top=True,
    )

    # マウスリスナーとキーボードリスナーを起動
    mouse_listener, key_listener = start_mouse_listener()

    webview.start(
        # デバッグモード
        # debug=True
    )
