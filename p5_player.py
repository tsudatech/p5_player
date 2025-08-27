import os
import webview
import json
from apis import EditorAPI, RenderAPI, TrackAPI
from utils import (
    start_image_server,
    create_smooth_lane_switch_js,
    create_base_html,
    create_single_iframe_js,
    MouseListenerManager,
)


class P5Player:
    def __init__(self):
        self.render_window = None
        self.editor_window = None
        self.track_window = None
        self.code_blocks = []
        self.selected_code_id = None
        self.track_blocks = []
        self.track_bpm = 120
        self.track_delay = 0
        self.render_width = 1000
        self.render_height = 1000
        self.DATA_FILE = "data/code_blocks.json"
        self.TRACK_FILE = "data/track_data.json"
        self.click_to_play_enabled = False
        self.image_server_port = 8080
        self.mouse_listener_manager = None
        self.initial_html = create_base_html()

    def load_blocks(self):
        """コードブロックを読み込み"""
        # dataフォルダが存在しない場合は作成
        os.makedirs("data", exist_ok=True)
        if not os.path.exists(self.DATA_FILE):
            return

        try:
            with open(self.DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.code_blocks = data.get("blocks", [])
                self.selected_code_id = data.get("selected_code_id", None)
        except Exception as e:
            print("Error loading data:", e)
            self.code_blocks = []
            self.selected_code_id = None

    def save_blocks(self):
        """コードブロックを保存"""
        # dataフォルダが存在しない場合は作成
        os.makedirs("data", exist_ok=True)
        try:
            with open(self.DATA_FILE, "w", encoding="utf-8") as f:
                blocks = {
                    "blocks": self.code_blocks,
                    "selected_code_id": self.selected_code_id,
                }
                json.dump(blocks, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print("Error saving data:", e)

    def load_track_data(self):
        """トラックデータを読み込み"""
        # dataフォルダが存在しない場合は作成
        os.makedirs("data", exist_ok=True)
        if os.path.exists(self.TRACK_FILE):
            with open(self.TRACK_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.track_blocks = data.get("track_blocks", [])
                if not self.track_blocks or not isinstance(self.track_blocks, list):
                    self.track_blocks = [[]]

                self.track_bpm = data.get("bpm", 120)
                self.track_delay = data.get("delay", 0)
                self.render_width = data.get("render_width", 1000)
                self.render_height = data.get("render_height", 1000)

        else:
            self.track_blocks = [[]]  # デフォルトで1つの空のレーン
            self.track_bpm = 120
            self.track_delay = 0
            self.render_width = 1000
            self.render_height = 1000

        # 最終確認：最低1つのレーンが存在することを保証
        if not self.track_blocks or len(self.track_blocks) == 0:
            print("No lanes found, creating default lane")
            self.track_blocks = [[]]

    def save_track_data(self):
        """トラックデータを保存"""
        # dataフォルダが存在しない場合は作成
        os.makedirs("data", exist_ok=True)
        try:
            data_to_save = {
                "bpm": self.track_bpm,
                "delay": self.track_delay,
                "track_blocks": self.track_blocks,
                "render_width": self.render_width,
                "render_height": self.render_height,
            }

            with open(self.TRACK_FILE, "w", encoding="utf-8") as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=2)

        except Exception as e:
            print("Error saving track data:", e)

    def update_render_window(self, code: str, lane_index=0):
        """iframeごと作り直してp5.jsスケッチを安全に再注入（レーン対応）"""
        if self.render_window:
            # バッククォートとバックスラッシュをエスケープ
            escaped_code = code.replace("\\", "\\\\")
            escaped_code = escaped_code.replace("`", "\\`")
            escaped_code = escaped_code.replace("$", "\\$")
            # ダブルクォートとシングルクォートの両方に対応
            escaped_code = escaped_code.replace(
                'loadImage("images',
                f'loadImage("http://localhost:{self.image_server_port}',
            )
            escaped_code = escaped_code.replace(
                "loadImage('images",
                f"loadImage('http://localhost:{self.image_server_port}",
            )

            js_code = create_smooth_lane_switch_js(lane_index, escaped_code)
            self.render_window.evaluate_js(js_code)

    def update_render_window_single(self, code: str):
        """エディタからの単一コード実行用（全レーンをクリアして単一iframeで表示）"""
        if self.render_window:
            # バッククォートとバックスラッシュをエスケープ
            escaped_code = code.replace("\\", "\\\\")
            escaped_code = escaped_code.replace("`", "\\`")
            escaped_code = escaped_code.replace("$", "\\$")
            # ダブルクォートとシングルクォートの両方に対応
            escaped_code = escaped_code.replace(
                'loadImage("images',
                f'loadImage("http://localhost:{self.image_server_port}',
            )
            escaped_code = escaped_code.replace(
                "loadImage('images",
                f"loadImage('http://localhost:{self.image_server_port}",
            )

            js_code = create_single_iframe_js(escaped_code)
            self.render_window.evaluate_js(js_code)

    def set_code_blocks(self, new_blocks):
        """コードブロックを設定"""
        self.code_blocks = new_blocks

    def update_click_to_play_enabled(self, enabled):
        """クリック再生の有効/無効を更新"""
        self.click_to_play_enabled = enabled
        if self.mouse_listener_manager:
            self.mouse_listener_manager.update_click_to_play_state(enabled)

    def run(self):
        """アプリケーションを起動"""
        try:
            print("Starting p5_player...")

            # 永続化されたデータを読み込み
            self.load_blocks()
            self.load_track_data()

            # 画像サーバーを起動
            image_server = start_image_server(self.image_server_port)

            # 最初のブロックがある場合は初期化時にscriptタグを追加
            if self.code_blocks:
                self.selected_code_id = self.code_blocks[0]["id"]

            # APIクラスのインスタンス化（依存関係を注入）
            editor_api = EditorAPI(
                code_blocks=self.code_blocks,
                selected_code_id=self.selected_code_id,
                track_window=None,  # 後で設定
                save_blocks_func=self.save_blocks,
                update_render_window_func=self.update_render_window,
                update_render_window_single_func=self.update_render_window_single,
                set_code_blocks_func=self.set_code_blocks,
                p5_player_instance=self,  # P5Playerインスタンスを渡す
            )

            render_api = RenderAPI(
                render_width=self.render_width,
                render_height=self.render_height,
                track_window=None,  # 後で設定
                save_track_data_func=self.save_track_data,
            )

            track_api = TrackAPI(
                track_blocks=self.track_blocks,
                track_bpm=self.track_bpm,
                track_delay=self.track_delay,
                code_blocks=self.code_blocks,
                render_width=self.render_width,
                render_height=self.render_height,
                render_window=None,  # 後で設定
                editor_window=None,  # 後で設定
                track_window=None,  # 後で設定
                save_track_data_func=self.save_track_data,
                update_render_window_func=self.update_render_window,
                update_click_to_play_func=self.update_click_to_play_enabled,
                p5_player_instance=self,  # P5Playerインスタンスを渡す
            )

            print("Creating render window...")
            self.render_window = webview.create_window(
                "Transparent Always on Top p5.js",
                html=self.initial_html,
                js_api=render_api,
                width=self.render_width,
                height=self.render_height,
                x=0,
                y=250,
                frameless=True,
                transparent=True,
                on_top=True,
            )

            print("Creating editor window...")
            self.editor_window = webview.create_window(
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
            self.track_window = webview.create_window(
                "Track Window",
                "view/track/index.html",
                js_api=track_api,
                width=2000,
                height=350,
                x=0,
                y=0,
                on_top=True,
            )

            # ウィンドウ参照をAPIクラスに設定
            editor_api.track_window = self.track_window
            render_api.track_window = self.render_window
            track_api.render_window = self.render_window
            track_api.editor_window = self.editor_window
            track_api.track_window = self.track_window

            # マウスリスナーマネージャーを初期化して起動
            self.mouse_listener_manager = MouseListenerManager(
                self.track_window, self.click_to_play_enabled
            )
            self.mouse_listener_manager.start_listeners(
                self.render_window, self.editor_window
            )
            webview.settings["OPEN_DEVTOOLS_IN_DEBUG"] = False
            webview.start(debug=True)

        except Exception as e:
            print(f"Error during startup: {e}")
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    app = P5Player()
    app.run()
