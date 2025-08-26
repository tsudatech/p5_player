from typing import Dict, List
from utils import (
    create_clear_all_lanes_js,
    create_clear_specific_lane_js,
    create_clear_single_iframe_js,
)


class TrackAPI:
    def __init__(
        self,
        track_blocks,
        track_bpm,
        track_delay,
        code_blocks,
        render_width,
        render_height,
        render_window,
        editor_window,
        track_window,
        save_track_data_func,
        update_render_window_func,
        update_click_to_play_func=None,
    ):
        self.track_blocks = track_blocks
        self.track_bpm = track_bpm
        self.track_delay = track_delay
        self.code_blocks = code_blocks
        self.render_width = render_width
        self.render_height = render_height
        self.render_window = render_window
        self.editor_window = editor_window
        self.track_window = track_window
        self.save_track_data = save_track_data_func
        self.update_render_window = update_render_window_func
        self.update_click_to_play = update_click_to_play_func

    def get_track_blocks(self):
        """トラックブロックの一覧を取得（現在のコードブロックデータで解決）"""
        try:
            # トラックブロックを現在のコードブロックデータで解決
            resolved_lanes = []
            for lane_index, lane_blocks in enumerate(self.track_blocks):
                resolved_blocks = []
                for block_index, track_block in enumerate(lane_blocks):
                    try:
                        # 対応するコードブロックを検索
                        code_block = None
                        for cb in self.code_blocks:
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
                    except Exception as e:
                        print(
                            f"Error processing block {block_index} in lane {lane_index}: {e}"
                        )
                        continue

                resolved_lanes.append(resolved_blocks)

            result = {
                "track_blocks": resolved_lanes,
                "bpm": self.track_bpm,
                "delay": self.track_delay,
                "render_width": self.render_width,
                "render_height": self.render_height,
            }

            return result

        except Exception as e:
            print(f"Error in get_track_blocks: {e}")
            # エラーが発生した場合はデフォルト値を返す
            return {
                "track_blocks": [[]],
                "bpm": 120,
                "delay": 0,
                "render_width": 1000,
                "render_height": 1000,
            }

    def save_track_blocks(self, blocks):
        """トラックブロックを保存（参照データのみ）"""
        # 参照データのみを保存（name, codeは除外）
        reference_lanes = []
        for lane_index, lane_blocks in enumerate(blocks):
            reference_blocks = []
            for block_index, block in enumerate(lane_blocks):
                reference_block = {
                    "block_id": block.get("block_id"),
                    "duration": block.get("duration", 1000),
                    "bars": block.get("bars", 8),
                }
                reference_blocks.append(reference_block)
            reference_lanes.append(reference_blocks)

        self.track_blocks = reference_lanes
        # グローバルに反映
        try:
            import p5_player

            p5_player.track_blocks = self.track_blocks
        except Exception:
            pass
        try:
            self.save_track_data()
            return {"status": "success"}
        except Exception as e:
            print(f"Error saving track blocks: {e}")
            return {"status": "error", "message": str(e)}

    def update_bpm(self, bpm):
        """BPMを更新"""
        self.track_bpm = bpm
        try:
            self.save_track_data()
            return {"status": "success"}
        except Exception as e:
            print(f"Error saving BPM: {e}")
            return {"status": "error", "message": str(e)}

    def update_delay(self, delay):
        """Delay timeを更新"""
        self.track_delay = delay
        try:
            self.save_track_data()
            return {"status": "success"}
        except Exception as e:
            print(f"Error saving delay: {e}")
            return {"status": "error", "message": str(e)}

    def hide_all_windows(self):
        """全てのウィンドウを隠す"""
        if self.render_window:
            self.render_window.hide()
        if self.editor_window:
            self.editor_window.hide()
        if self.track_window:
            self.track_window.hide()
        return {"status": "success"}

    def show_all_windows(self):
        """全てのウィンドウを表示"""
        if self.render_window:
            self.render_window.show()
        if self.editor_window:
            self.editor_window.show()
        if self.track_window:
            self.track_window.show()
        return {"status": "success"}

    def add_track_block(self, block_data, lane_index=0):
        """トラックにブロックを追加（参照データのみ）"""
        # レーンが存在しない場合は作成
        while len(self.track_blocks) <= lane_index:
            self.track_blocks.append([])
            # グローバルにも新しいレーンを反映
            try:
                import p5_player

                p5_player.track_blocks = self.track_blocks
            except Exception:
                pass

        # 参照データのみを保存
        reference_block = {
            "block_id": block_data.get("id"),
            "duration": block_data.get("duration", 1000),
            "bars": block_data.get("bars", 8),
        }

        self.track_blocks[lane_index].append(reference_block)
        self.save_track_data()
        return {"status": "success", "track_blocks": self.track_blocks}

    def stop_playback(self):
        """トラックの再生を停止"""
        if self.track_window:
            self.track_window.evaluate_js("stopPlayback()")
        return {"status": "success"}

    def get_click_to_play_state(self):
        """クリック再生の有効/無効状態を取得"""
        # グローバル変数のclick_to_play_enabledの値を返す
        import p5_player

        return {"enabled": p5_player.click_to_play_enabled}

    def update_click_to_play_state(self, enabled):
        """クリック再生の有効/無効状態を更新"""
        if self.update_click_to_play:
            self.update_click_to_play(enabled)
        print(f"Click to play state updated: {enabled}")
        return {"status": "success"}

    def update_render_size(self, width, height):
        """レンダーウィンドウのサイズを更新"""
        self.render_width = width
        self.render_height = height

        # レンダーウィンドウのサイズを変更
        if self.render_window:
            try:
                self.render_window.resize(width, height)
            except Exception as e:
                print(f"Error resizing render window: {e}")
                return {"status": "error", "message": str(e)}

        # 設定を保存
        try:
            self.save_track_data()
        except Exception as e:
            print(f"Error saving track data: {e}")
            return {"status": "error", "message": str(e)}

        return {"status": "success"}

    def get_render_size(self):
        """現在のレンダーウィンドウサイズを取得"""
        return {"width": self.render_width, "height": self.render_height}

    def play_multiple_lanes(self, lane_data):
        """複数レーンの同時再生"""
        if self.render_window:
            try:
                # アクティブなレーンのインデックスを取得
                active_lane_indices = [
                    lane_info.get("lane_index", 0) for lane_info in lane_data
                ]

                # 全レーンのiframeを一旦クリア
                js_code = create_clear_all_lanes_js()
                self.render_window.evaluate_js(js_code)

                # アクティブなレーンのコードを個別に実行
                for lane_info in lane_data:
                    lane_index = lane_info.get("lane_index", 0)
                    code = lane_info.get("code", "")
                    if code:
                        self.update_render_window(code, lane_index)

                return {"status": "success", "lanes_played": len(lane_data)}
            except Exception as e:
                print(f"Error playing multiple lanes: {e}")
                return {"status": "error", "message": str(e)}
        return {"status": "error", "message": "Render window not available"}

    def clear_all_lanes(self):
        """全レーンのiframeをクリア"""
        if self.render_window:
            try:
                js_code = create_clear_all_lanes_js()
                self.render_window.evaluate_js(js_code)
                return {"status": "success"}
            except Exception as e:
                print(f"Error clearing lanes: {e}")
                return {"status": "error", "message": str(e)}
        return {"status": "error", "message": "Render window not available"}

    def clear_specific_lane(self, lane_index):
        """特定のレーンのiframeをクリア"""
        if self.render_window:
            try:
                js_code = create_clear_specific_lane_js(lane_index)
                self.render_window.evaluate_js(js_code)
                return {"status": "success"}
            except Exception as e:
                print(f"Error clearing lane {lane_index + 1}: {e}")
                return {"status": "error", "message": str(e)}
        return {"status": "error", "message": "Render window not available"}

    def clear_single_iframe(self):
        """エディタの単一iframeをクリア"""
        if self.render_window:
            try:
                js_code = create_clear_single_iframe_js()
                self.render_window.evaluate_js(js_code)
                return {"status": "success"}
            except Exception as e:
                print(f"Error clearing single iframe: {e}")
                return {"status": "error", "message": str(e)}
        return {"status": "error", "message": "Render window not available"}

    def update_single_lane(self, lane_index, code):
        """特定のレーンのiframeのみを更新（他のレーンに影響しない）"""
        if self.render_window:
            try:
                self.update_render_window(code, lane_index)
                return {"status": "success"}
            except Exception as e:
                print(f"Error updating single lane {lane_index + 1}: {e}")
                return {"status": "error", "message": str(e)}
        return {"status": "error", "message": "Render window not available"}
