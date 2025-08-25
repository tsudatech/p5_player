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
render_width = 1000
render_height = 1000
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
    global track_blocks, track_bpm, track_delay, render_width, render_height
    # dataフォルダが存在しない場合は作成
    os.makedirs("data", exist_ok=True)

    if os.path.exists(TRACK_FILE):
        try:
            with open(TRACK_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                track_blocks = data.get("track_blocks", [])
                track_bpm = data.get("bpm", 120)
                track_delay = data.get("delay", 0)
                render_width = data.get("render_width", 1000)
                render_height = data.get("render_height", 1000)
        except Exception as e:
            print("Error loading track data:", e)
            track_blocks = []
            track_bpm = 120
            track_delay = 0
            render_width = 1000
            render_height = 1000


def save_track_data():
    global track_bpm, track_delay, render_width, render_height
    # dataフォルダが存在しない場合は作成
    os.makedirs("data", exist_ok=True)

    try:
        with open(TRACK_FILE, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "bpm": track_bpm,
                    "delay": track_delay,
                    "track_blocks": track_blocks,
                    "render_width": render_width,
                    "render_height": render_height,
                },
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
        # ダブルクォートとシングルクォートの両方に対応
        escaped_code = escaped_code.replace(
            'loadImage("images', f'loadImage("http://localhost:{image_server_port}'
        )
        escaped_code = escaped_code.replace(
            "loadImage('images", f"loadImage('http://localhost:{image_server_port}"
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


# Ctrlキーの状態を追跡
cmd_pressed = False
ctrl_pressed = False


def on_key_press(key):
    global render_window, editor_window, track_window, cmd_pressed, ctrl_pressed
    try:
        # Ctrlキーの押下を検出
        if hasattr(key, "name") and key.name == "cmd":
            cmd_pressed = True
            return

        if hasattr(key, "name") and key.name == "ctrl":
            ctrl_pressed = True
            return

        # 文字キーの処理
        if hasattr(key, "char") and cmd_pressed:
            key_char = key.char.lower()
            if key_char == "h":
                print("Ctrl+H pressed - hiding all windows")
                if render_window:
                    render_window.hide()
                if editor_window:
                    editor_window.hide()
                if track_window:
                    track_window.hide()
            elif key_char == "s" and ctrl_pressed:
                print("Ctrl+S pressed - showing all windows")
                if render_window:
                    render_window.show()
                if editor_window:
                    editor_window.show()
                if track_window:
                    track_window.show()

    except AttributeError:
        pass


def on_key_release(key):
    global cmd_pressed, ctrl_pressed
    try:
        # Ctrlキーのリリースを検出
        if hasattr(key, "name") and key.name == "cmd":
            cmd_pressed = False
        if hasattr(key, "name") and key.name == "ctrl":
            ctrl_pressed = False
    except AttributeError:
        pass


def start_mouse_listener():
    """マウスリスナーとキーボードリスナーを別スレッドで起動"""
    print("start_mouse_listener")
    from pynput import keyboard

    listener = mouse.Listener(on_click=on_click)
    key_listener = keyboard.Listener(on_press=on_key_press, on_release=on_key_release)
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
                    # トラックウィンドウに更新を通知
                    if track_window:
                        track_window.evaluate_js("loadTrackBlocks()")
                    break
        return {"blocks": code_blocks, "selected_code_id": selected_code_id}

    def update_block_name(self, index, name):
        global code_blocks
        if 0 <= index < len(code_blocks):
            code_blocks[index]["name"] = name
            save_blocks()
            # トラックウィンドウに更新を通知
            if track_window:
                track_window.evaluate_js("loadTrackBlocks()")
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
        # トラックウィンドウに更新を通知
        if track_window:
            track_window.evaluate_js("loadTrackBlocks()")
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
            # トラックウィンドウに更新を通知
            if track_window:
                track_window.evaluate_js("loadTrackBlocks()")
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
        """トラックブロックの一覧を取得（現在のコードブロックデータで解決）"""
        global track_blocks, track_bpm, track_delay, code_blocks

        # トラックブロックを現在のコードブロックデータで解決
        resolved_blocks = []
        for track_block in track_blocks:
            # 対応するコードブロックを検索
            code_block = None
            for cb in code_blocks:
                if cb.get("id") == track_block.get("block_id"):
                    code_block = cb
                    break

            if code_block:
                # 現在のコードブロックデータで解決
                resolved_block = {
                    "block_id": track_block.get("block_id"),
                    "name": code_block.get("name", "Unknown Block"),
                    "code": code_block.get("code", ""),
                    "duration": track_block.get("duration", 1000),
                    "bars": track_block.get("bars", 8),
                }
                resolved_blocks.append(resolved_block)
            else:
                # 対応するコードブロックが見つからない場合は削除対象
                print(
                    f"Warning: Code block with id {track_block.get('block_id')} not found, skipping"
                )

        return {
            "track_blocks": resolved_blocks,
            "bpm": track_bpm,
            "delay": track_delay,
            "render_width": render_width,
            "render_height": render_height,
        }

    def save_track_blocks(self, blocks):
        """トラックブロックを保存（参照データのみ）"""
        global track_blocks

        # 参照データのみを保存（name, codeは除外）
        reference_blocks = []
        for block in blocks:
            reference_block = {
                "block_id": block.get("block_id"),
                "duration": block.get("duration", 1000),
                "bars": block.get("bars", 8),
            }
            reference_blocks.append(reference_block)

        track_blocks = reference_blocks
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
        """トラックにブロックを追加（参照データのみ）"""
        global track_blocks

        # 参照データのみを保存
        reference_block = {
            "block_id": block_data.get("id"),
            "duration": block_data.get("duration", 1000),
            "bars": block_data.get("bars", 8),
        }

        track_blocks.append(reference_block)
        save_track_data()
        return {"status": "success", "track_blocks": track_blocks}

    def update_click_to_play_state(self, enabled):
        """クリック再生の有効/無効状態を更新"""
        global click_to_play_enabled
        click_to_play_enabled = enabled
        print(f"Click to play state updated: {enabled}")
        return {"status": "success"}

    def update_render_size(self, width, height):
        """レンダーウィンドウのサイズを更新"""
        global render_width, render_height, render_window
        render_width = width
        render_height = height

        # レンダーウィンドウのサイズを変更
        if render_window:
            render_window.resize(width, height)

        # 設定を保存
        save_track_data()
        print(f"Render window size updated: {width}x{height}")
        return {"status": "success"}

    def get_render_size(self):
        """現在のレンダーウィンドウサイズを取得"""
        global render_width, render_height
        return {"width": render_width, "height": render_height}


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
        width=render_width,
        height=render_height,
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
    webview.settings["OPEN_DEVTOOLS_IN_DEBUG"] = False
    webview.start(debug=True)
