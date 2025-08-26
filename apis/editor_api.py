import uuid
import json
from typing import Dict, List, Optional


class EditorAPI:
    def __init__(
        self,
        code_blocks,
        selected_code_id,
        track_window,
        save_blocks_func,
        update_render_window_func,
        update_render_window_single_func,
    ):
        self.code_blocks = code_blocks
        self.selected_code_id = selected_code_id
        self.track_window = track_window
        self.save_blocks = save_blocks_func
        self.update_render_window = update_render_window_func
        self.update_render_window_single = update_render_window_single_func

    def add_block(self):
        new_block = {
            "id": str(uuid.uuid4()),
            "name": f"Block {len(self.code_blocks) + 1}",
            "code": "// New p5.js sketch\n"
            "function setup() {\n"
            "  createCanvas(400, 400);\n"
            "}\n\n"
            "function draw() {\n"
            "  background(220);\n"
            "}",
        }
        self.code_blocks.append(new_block)
        self.selected_code_id = new_block["id"]
        self.save_blocks()
        return {"blocks": self.code_blocks, "selected_code_id": self.selected_code_id}

    def add_block_to_track(self, index, lane_index=0):
        """ブロックをトラックに追加"""
        if 0 <= index < len(self.code_blocks):
            block = self.code_blocks[index]
            if self.track_window:
                self.track_window.evaluate_js(
                    f"addTrackBlock({json.dumps(block)}, {lane_index})"
                )
            return {"status": "success"}
        return {"status": "error", "message": "Invalid block index"}

    def select_block(self, index):
        if 0 <= index < len(self.code_blocks):
            self.selected_code_id = self.code_blocks[index]["id"]
            self.save_blocks()
            return self.code_blocks[index]["code"]
        return ""

    def update_block(self, code):
        if self.selected_code_id is not None:
            for block in self.code_blocks:
                if block["id"] == self.selected_code_id:
                    block["code"] = code
                    self.save_blocks()
                    # トラックの再生を停止
                    if self.track_window:
                        self.track_window.evaluate_js("stopPlayback()")
                    # エディタ用の単一iframeでコードを表示
                    self.update_render_window_single(code)
                    # トラックウィンドウに更新を通知
                    if self.track_window:
                        self.track_window.evaluate_js("loadTrackBlocks()")
                    break
        return {"blocks": self.code_blocks, "selected_code_id": self.selected_code_id}

    def update_block_name(self, index, name):
        if 0 <= index < len(self.code_blocks):
            self.code_blocks[index]["name"] = name
            self.save_blocks()
            # トラックウィンドウに更新を通知
            if self.track_window:
                self.track_window.evaluate_js("loadTrackBlocks()")
        return {"blocks": self.code_blocks, "selected_code_id": self.selected_code_id}

    def get_block_by_id(self, block_id):
        """IDでブロックを取得"""
        for i, block in enumerate(self.code_blocks):
            if block.get("id") == block_id:
                return {"block": block, "index": i}
        return None

    def reorder_blocks(self, new_blocks, moved_block_id=None):
        self.code_blocks = new_blocks

        # 移動したブロックのIDが指定されている場合は、それを選択状態にする
        if moved_block_id is not None:
            self.selected_code_id = moved_block_id

        self.save_blocks()
        # トラックウィンドウに更新を通知
        if self.track_window:
            self.track_window.evaluate_js("loadTrackBlocks()")
        return {"blocks": self.code_blocks, "selected_code_id": self.selected_code_id}

    def get_all_blocks(self):
        """すべてのブロックと選択されたブロックIDを取得"""
        return {"blocks": self.code_blocks, "selected_code_id": self.selected_code_id}

    def load_first_block(self):
        """最初のブロックを読み込む"""
        if self.code_blocks:
            self.selected_code_id = self.code_blocks[0]["id"]
            self.save_blocks()
            return {
                "code": self.code_blocks[0]["code"],
                "selected_code_id": self.selected_code_id,
            }
        return {"code": "// No blocks available", "selected_code_id": None}

    def delete_block(self, index):
        if 0 <= index < len(self.code_blocks):
            # 削除するブロックのID
            deleted_block_id = self.code_blocks[index]["id"]

            # 削除するブロックが現在選択されている場合
            if self.selected_code_id == deleted_block_id:
                # 次のブロックを選択、なければ前のブロックを選択
                if index < len(self.code_blocks) - 1:
                    self.selected_code_id = self.code_blocks[index + 1]["id"]
                elif index > 0:
                    self.selected_code_id = self.code_blocks[index - 1]["id"]
                else:
                    self.selected_code_id = None

            # ブロックを削除
            del self.code_blocks[index]
            self.save_blocks()

            # トラックウィンドウに更新を通知
            if self.track_window:
                self.track_window.evaluate_js("loadTrackBlocks()")

            return {
                "blocks": self.code_blocks,
                "selected_code_id": self.selected_code_id,
            }
        return {"status": "error", "message": "Invalid block index"}
