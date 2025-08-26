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
        set_code_blocks_func,
    ):
        self.code_blocks = code_blocks
        self.selected_code_id = selected_code_id
        self.track_window = track_window
        self.save_blocks = save_blocks_func
        self.update_render_window = update_render_window_func
        self.update_render_window_single = update_render_window_single_func
        self.set_code_blocks = set_code_blocks_func

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
        # 同期して保存
        self.set_code_blocks(self.code_blocks)
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

    def get_track_info_for_editor(self):
        """エディタ側のレーン選択ダイアログ用に、現在のレーン一覧を返す"""
        try:
            lanes_info = []

            # 1) まずはグローバルを参照
            try:
                import p5_player  # グローバルのtrack_blocksを参照

                track_blocks = getattr(p5_player, "track_blocks", []) or []
            except Exception:
                track_blocks = []

            # 2) グローバルが空の場合はファイルから読み込み
            if not track_blocks:
                try:
                    import json, os

                    TRACK_FILE = "data/track_data.json"
                    if os.path.exists(TRACK_FILE):
                        with open(TRACK_FILE, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            track_blocks = data.get("track_blocks", []) or []
                except Exception:
                    track_blocks = []

            # 3) それでも空なら、トラックウィンドウのDOMから推測
            if not track_blocks and self.track_window:
                try:
                    lane_count = self.track_window.evaluate_js(
                        "(function(){return document.querySelectorAll('.lane-container').length;})()"
                    )
                    if isinstance(lane_count, int) and lane_count > 0:
                        track_blocks = [[] for _ in range(lane_count)]
                except Exception:
                    pass

            for i, lane in enumerate(track_blocks):
                lanes_info.append(
                    {
                        "lane_index": i,
                        "lane_name": f"Lane {i + 1}",
                        "block_count": len(lane or []),
                    }
                )

            # レーンが1つもない場合でも最低1つ返す
            if not lanes_info:
                lanes_info = [
                    {"lane_index": 0, "lane_name": "Lane 1", "block_count": 0}
                ]
            return {"lanes": lanes_info}
        except Exception:
            return {
                "lanes": [{"lane_index": 0, "lane_name": "Lane 1", "block_count": 0}]
            }

    def select_block(self, index):
        if 0 <= index < len(self.code_blocks):
            self.selected_code_id = self.code_blocks[index]["id"]
            # 選択のみでも同期しておく
            self.set_code_blocks(self.code_blocks)
            self.save_blocks()
            return self.code_blocks[index]["code"]
        return ""

    def update_block(self, code):
        if self.selected_code_id is not None:
            for block in self.code_blocks:
                if block["id"] == self.selected_code_id:
                    block["code"] = code
                    # 同期して保存
                    self.set_code_blocks(self.code_blocks)
                    self.save_blocks()
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
            # 同期して保存
            self.set_code_blocks(self.code_blocks)
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
        # 新しいリストに差し替え
        self.code_blocks = new_blocks

        # 移動したブロックのIDが指定されている場合は、それを選択状態にする
        if moved_block_id is not None:
            self.selected_code_id = moved_block_id

        # 同期して保存
        self.set_code_blocks(self.code_blocks)
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
            # 同期して保存
            self.set_code_blocks(self.code_blocks)
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
            # 同期して保存
            self.set_code_blocks(self.code_blocks)
            self.save_blocks()

            # トラックウィンドウに更新を通知
            if self.track_window:
                self.track_window.evaluate_js("loadTrackBlocks()")

            return {
                "blocks": self.code_blocks,
                "selected_code_id": self.selected_code_id,
            }
        return {"status": "error", "message": "Invalid block index"}
