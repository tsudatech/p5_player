import os
import webview
import json
from pynput import mouse
from apis import EditorAPI, RenderAPI, TrackAPI
from utils import (
    start_image_server,
    create_smooth_lane_switch_js,
    create_base_html,
    create_single_iframe_js,
    create_clear_single_iframe_js,
)

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


# 固定のベースHTML（常に同じ構造を使用）
initial_html = create_base_html()


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
            blocks = {"blocks": code_blocks, "selected_code_id": selected_code_id}
            json.dump(blocks, f, ensure_ascii=False, indent=2)
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

                # 空の配列や不正な形式の場合はデフォルト値を使用
                if not track_blocks or not isinstance(track_blocks, list):
                    track_blocks = [[]]

                track_bpm = data.get("bpm", 120)
                track_delay = data.get("delay", 0)
                render_width = data.get("render_width", 1000)
                render_height = data.get("render_height", 1000)

        except Exception as e:
            print(f"Error loading track data: {e}")
            track_blocks = [[]]  # デフォルトで1つの空のレーン
            track_bpm = 120
            track_delay = 0
            render_width = 1000
            render_height = 1000
    else:
        track_blocks = [[]]  # デフォルトで1つの空のレーン
        track_bpm = 120
        track_delay = 0
        render_width = 1000
        render_height = 1000

    # 最終確認：最低1つのレーンが存在することを保証
    if not track_blocks or len(track_blocks) == 0:
        print("No lanes found, creating default lane")
        track_blocks = [[]]


def save_track_data():
    global track_bpm, track_delay, render_width, render_height
    # dataフォルダが存在しない場合は作成
    os.makedirs("data", exist_ok=True)
    try:
        data_to_save = {
            "bpm": track_bpm,
            "delay": track_delay,
            "track_blocks": track_blocks,
            "render_width": render_width,
            "render_height": render_height,
        }

        with open(TRACK_FILE, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=2)

    except Exception as e:
        print("Error saving track data:", e)


def update_render_window(code: str, lane_index=0):
    """iframeごと作り直してp5.jsスケッチを安全に再注入（レーン対応）"""
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

        js_code = create_smooth_lane_switch_js(lane_index, escaped_code)
        render_window.evaluate_js(js_code)


def update_render_window_single(code: str):
    """エディタからの単一コード実行用（全レーンをクリアして単一iframeで表示）"""
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

        js_code = create_single_iframe_js(escaped_code)
        render_window.evaluate_js(js_code)


def on_click(x, y, button, pressed):
    global track_window, click_to_play_enabled
    if pressed:
        print(f"Mouse clicked at ({x}, {y}) with {button}")

        # トグルがONの時のみplayを発火
        if click_to_play_enabled:
            print(f"Click to play enabled! Triggering play...")
            if track_window:
                # トラックウィンドウにplayコマンドを送信（delay処理はJavaScript側で行う）
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


if __name__ == "__main__":
    try:
        print("Starting p5_player...")

        # 永続化されたデータを読み込み
        load_blocks()
        load_track_data()

        # 画像サーバーを起動
        image_server = start_image_server(image_server_port)

        # 最初のブロックがある場合は初期化時にscriptタグを追加
        if code_blocks:
            selected_code_id = code_blocks[0]["id"]

        # APIクラスのインスタンス化（依存関係を注入）
        editor_api = EditorAPI(
            code_blocks=code_blocks,
            selected_code_id=selected_code_id,
            track_window=None,  # 後で設定
            save_blocks_func=save_blocks,
            update_render_window_func=update_render_window,
            update_render_window_single_func=update_render_window_single,
        )

        render_api = RenderAPI(
            render_width=render_width,
            render_height=render_height,
            track_window=None,  # 後で設定
            save_track_data_func=save_track_data,
        )

        # click_to_play_enabledを更新する関数
        def update_click_to_play_enabled(enabled):
            global click_to_play_enabled
            click_to_play_enabled = enabled

        track_api = TrackAPI(
            track_blocks=track_blocks,
            track_bpm=track_bpm,
            track_delay=track_delay,
            code_blocks=code_blocks,
            render_width=render_width,
            render_height=render_height,
            render_window=None,  # 後で設定
            editor_window=None,  # 後で設定
            track_window=None,  # 後で設定
            save_track_data_func=save_track_data,
            update_render_window_func=update_render_window,
            update_click_to_play_func=update_click_to_play_enabled,
        )

        print("Creating render window...")
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

        print("Creating editor window...")
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

        print("Creating track window...")
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

        # ウィンドウ参照をAPIクラスに設定
        editor_api.track_window = track_window
        render_api.track_window = track_window
        track_api.render_window = render_window
        track_api.editor_window = editor_window
        track_api.track_window = track_window

        # マウスリスナーとキーボードリスナーを起動
        mouse_listener, key_listener = start_mouse_listener()
        webview.settings["OPEN_DEVTOOLS_IN_DEBUG"] = False
        webview.start(debug=True)

    except Exception as e:
        print(f"Error during startup: {e}")
        import traceback

        traceback.print_exc()
