from pynput import mouse, keyboard
from typing import Optional


class MouseListenerManager:
    def __init__(self, track_window, click_to_play_enabled):
        self.track_window = track_window
        self.click_to_play_enabled = click_to_play_enabled
        self.cmd_pressed = False
        self.ctrl_pressed = False
        self.mouse_listener = None
        self.keyboard_listener = None

    def on_click(self, x, y, button, pressed):
        """マウスクリックイベントハンドラー"""
        if pressed:
            print(f"Mouse clicked at ({x}, {y}) with {button}")

            # トグルがONの時のみplayを発火
            if self.click_to_play_enabled:
                print(f"Click to play enabled! Triggering play...")
                if self.track_window:
                    # トラックウィンドウにplayコマンドを送信（delay処理はJavaScript側で行う）
                    self.track_window.evaluate_js("playCurrentTrack()")
            else:
                print(f"Click to play disabled - ignoring click")

    def on_key_press(self, key, render_window=None, editor_window=None):
        """キー押下イベントハンドラー"""
        try:
            # Ctrlキーの押下を検出
            if hasattr(key, "name") and key.name == "cmd":
                self.cmd_pressed = True
                return

            if hasattr(key, "name") and key.name == "ctrl":
                self.ctrl_pressed = True
                return

            # 文字キーの処理
            if hasattr(key, "char") and self.cmd_pressed:
                key_char = key.char.lower()
                if key_char == "h":
                    print("Ctrl+H pressed - hiding all windows")
                    if render_window:
                        render_window.hide()
                    if editor_window:
                        editor_window.hide()
                    if self.track_window:
                        self.track_window.hide()
                elif key_char == "s" and self.ctrl_pressed:
                    print("Ctrl+S pressed - showing all windows")
                    if render_window:
                        render_window.show()
                    if editor_window:
                        editor_window.show()
                    if self.track_window:
                        self.track_window.show()

        except AttributeError:
            pass

    def on_key_release(self, key):
        """キーリリースイベントハンドラー"""
        try:
            # Ctrlキーのリリースを検出
            if hasattr(key, "name") and key.name == "cmd":
                self.cmd_pressed = False
            if hasattr(key, "name") and key.name == "ctrl":
                self.ctrl_pressed = False
        except AttributeError:
            pass

    def start_listeners(self, render_window=None, editor_window=None):
        """マウスリスナーとキーボードリスナーを別スレッドで起動"""
        print("start_mouse_listener")

        self.mouse_listener = mouse.Listener(on_click=self.on_click)
        self.keyboard_listener = keyboard.Listener(
            on_press=lambda key: self.on_key_press(key, render_window, editor_window),
            on_release=self.on_key_release,
        )

        self.mouse_listener.start()
        self.keyboard_listener.start()

    def stop_listeners(self):
        """リスナーを停止"""
        if self.mouse_listener:
            self.mouse_listener.stop()
        if self.keyboard_listener:
            self.keyboard_listener.stop()

    def update_click_to_play_state(self, enabled):
        """クリック再生の有効/無効状態を更新"""
        self.click_to_play_enabled = enabled
