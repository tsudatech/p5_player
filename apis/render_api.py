from typing import Dict


class RenderAPI:
    def __init__(self, render_width, render_height, track_window, save_track_data_func):
        self.render_width = render_width
        self.render_height = render_height
        self.track_window = track_window
        self.save_track_data = save_track_data_func

    def notify_ready(self):
        # 初期化完了の通知（必要に応じて追加の処理を行う）
        pass

    def on_render_window_resize(self, width, height):
        """レンダーウィンドウが手動でリサイズされた時の処理"""
        print(f"on_render_window_resize called: {width}x{height}")
        self.render_width = width
        self.render_height = height
        self.save_track_data()

        if self.track_window:
            print("Updating track window...")
            self.track_window.evaluate_js(
                f"""
                document.getElementById('render-width').value = {width};
                document.getElementById('render-height').value = {height};
                currentRenderWidth = {width};
                currentRenderHeight = {height};
                console.log('Track window updated with size:', {width}, 'x', {height});
            """
            )
        else:
            print("Track window not available")

        return {"status": "success"}
