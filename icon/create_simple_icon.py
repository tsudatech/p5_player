#!/usr/bin/env python3
"""
p5_player用のシンプルなアイコンを生成するスクリプト（PIL不要）
"""

import os


def create_simple_icon():
    """シンプルなSVGアイコンを作成"""

    svg_content = """<?xml version="1.0" encoding="UTF-8"?>
<svg width="128" height="128" viewBox="0 0 128 128" xmlns="http://www.w3.org/2000/svg">
  <!-- 背景の円 -->
  <defs>
    <radialGradient id="grad1" cx="50%" cy="50%" r="50%">
      <stop offset="0%" style="stop-color:#6496ff;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#4169e1;stop-opacity:1" />
    </radialGradient>
  </defs>
  
  <!-- 背景円 -->
  <circle cx="64" cy="64" r="50" fill="url(#grad1)" stroke="#ffffff" stroke-width="3"/>
  
  <!-- p5 テキスト -->
  <text x="64" y="75" font-family="Arial, sans-serif" font-size="32" font-weight="bold" 
        text-anchor="middle" fill="#ffffff">p5</text>
  
  <!-- 装飾的な要素 -->
  <circle cx="40" cy="40" r="3" fill="#ffffff" opacity="0.7"/>
  <circle cx="88" cy="40" r="3" fill="#ffffff" opacity="0.7"/>
  <circle cx="40" cy="88" r="3" fill="#ffffff" opacity="0.7"/>
  <circle cx="88" cy="88" r="3" fill="#ffffff" opacity="0.7"/>
</svg>"""

    # SVGファイルを保存
    svg_path = "p5_player_icon.svg"
    with open(svg_path, "w") as f:
        f.write(svg_content)

    print(f"SVGアイコンが作成されました: {svg_path}")

    # PNGファイルも作成（システムコマンドを使用）
    png_path = "p5_player_icon.png"
    try:
        # macOSの場合、sipsコマンドを使用してSVGをPNGに変換
        os.system(f"sips -s format png {svg_path} --out {png_path}")
        print(f"PNGアイコンが作成されました: {png_path}")
    except:
        print("PNG変換に失敗しました。SVGファイルを使用してください。")

    return svg_path


if __name__ == "__main__":
    create_simple_icon()
