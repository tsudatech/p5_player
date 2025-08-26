def create_smooth_lane_switch_js(lane_index: int, escaped_code: str) -> str:
    """
    レーンのスムーズな切り替えを行うJavaScriptコードを生成

    Args:
        lane_index: レーンのインデックス
        escaped_code: エスケープされたp5.jsコード

    Returns:
        生成されたJavaScriptコード
    """
    return f"""
    // レーン {lane_index} のスムーズな切り替え
    let currentFrame = document.getElementById("p5-frame-lane-{lane_index}");
    
    // 新しいiframeを作成（非表示で）
    const newFrame = document.createElement("iframe");
    newFrame.id = "p5-frame-lane-{lane_index}-new";
    newFrame.style.border = "none";
    newFrame.style.width = "100vw";
    newFrame.style.height = "100vh";
    newFrame.style.position = "absolute";
    newFrame.style.top = "0";
    newFrame.style.left = "0";
    newFrame.style.zIndex = "{lane_index + 1}";
    newFrame.style.pointerEvents = "none";
    newFrame.style.opacity = "0";
    newFrame.style.transition = "opacity 0.15s ease-in-out";
    document.body.appendChild(newFrame);

    // 既存のiframeを前面に
    if (currentFrame) {{
        currentFrame.style.zIndex = "{lane_index + 1}";
        currentFrame.style.transition = "opacity 0.15s ease-in-out";
    }}

    // 新しいiframeにsrcdocを設定
    newFrame.srcdoc = `
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="utf-8" />
        <style>
          body {{
            margin: 0;
            padding: 0;
            overflow: hidden;
            background: transparent;
          }}
          canvas {{
            display: block;
            background: transparent;
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

    // 新しいiframeが読み込まれたら切り替え
    newFrame.onload = function() {{
        // 新しいiframeをフェードイン
        newFrame.style.opacity = "1";
        
        // 古いiframeをフェードアウト
        if (currentFrame) {{
            currentFrame.style.opacity = "0";
        }}
        
        // フェード完了後に古いiframeを削除
        setTimeout(function() {{
            if (currentFrame) {{
                currentFrame.remove();
            }}
            // 新しいiframeのIDを正しいものに変更
            newFrame.id = "p5-frame-lane-{lane_index}";
            newFrame.style.zIndex = "auto";
        }}, 150);
    }};

    // 既存のiframeがない場合は即座に表示
    if (!currentFrame) {{
        newFrame.style.opacity = "1";
        newFrame.id = "p5-frame-lane-{lane_index}";
    }}
    """


def create_clear_all_lanes_js() -> str:
    """
    全レーンのiframeをクリアするJavaScriptコードを生成

    Returns:
        生成されたJavaScriptコード
    """
    return """
    // 全レーンのiframeを削除
    const laneFrames = document.querySelectorAll('[id^="p5-frame-lane-"]');
    laneFrames.forEach(frame => frame.remove());
    console.log('All lane iframes cleared');
    """


def create_clear_specific_lane_js(lane_index: int) -> str:
    """
    特定のレーンのiframeをクリアするJavaScriptコードを生成

    Args:
        lane_index: レーンのインデックス

    Returns:
        生成されたJavaScriptコード
    """
    return f"""
    // 特定のレーンのiframeを削除
    const laneFrame = document.getElementById("p5-frame-lane-{lane_index}");
    if (laneFrame) {{
        laneFrame.remove();
        console.log('Lane {lane_index + 1} iframe cleared');
    }}
    """


def create_clear_single_iframe_js() -> str:
    """
    エディタの単一iframeをクリアするJavaScriptコードを生成

    Returns:
        生成されたJavaScriptコード
    """
    return """
    // エディタの単一iframeを削除
    const singleFrame = document.getElementById('single-iframe');
    if (singleFrame) {
        singleFrame.remove();
        console.log('Single iframe cleared');
    }
    """


def create_resize_handler_js() -> str:
    """
    ウィンドウリサイズハンドラーのJavaScriptコードを生成

    Returns:
        生成されたJavaScriptコード
    """
    return """
    let lastSize = {width: window.innerWidth, height: window.innerHeight};
    let resizeTimeout = null;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(() => {
            const newSize = {width: window.innerWidth, height: window.innerHeight};
            if (newSize.width !== lastSize.width || newSize.height !== lastSize.height) {
                lastSize = newSize;
                if (window.pywebview?.api) {
                    window.pywebview.api.on_render_window_resize(newSize.width, newSize.height);
                }
            }
        }, 50);
    });
    """


def create_single_iframe_js(escaped_code: str) -> str:
    """
    エディタからの単一コード実行用のJavaScriptコードを生成

    Args:
        escaped_code: エスケープされたp5.jsコード

    Returns:
        生成されたJavaScriptコード
    """
    return f"""
    // 全レーンのiframeをクリア
    const laneFrames = document.querySelectorAll('[id^="p5-frame-lane-"]');
    laneFrames.forEach(frame => frame.remove());
    
    // 既存の単一iframeがあれば削除
    const existingSingleFrame = document.getElementById('single-iframe');
    if (existingSingleFrame) {{
        existingSingleFrame.remove();
    }}
    
    // 単一のiframeを作成
    const iframe = document.createElement('iframe');
    iframe.id = 'single-iframe';
    iframe.style.width = '100vw';
    iframe.style.height = '100vh';
    iframe.style.border = 'none';
    iframe.style.position = 'absolute';
    iframe.style.top = '0';
    iframe.style.left = '0';
    iframe.style.zIndex = '1000';
    iframe.style.pointerEvents = 'none';
    
    document.body.appendChild(iframe);
    
    // iframeにコードを注入
    const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
    iframeDoc.open();
    iframeDoc.write(`
        <!DOCTYPE html>
        <html>
        <head>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/p5.js/1.7.0/p5.min.js"></script>
            <style>
                body {{ margin: 0; padding: 0; overflow: hidden; background: transparent; }}
                canvas {{ display: block; background: transparent; }}
            </style>
        </head>
        <body>
            <script>
                {escaped_code}
            </script>
        </body>
        </html>
    `);
    iframeDoc.close();
    """


def create_base_html() -> str:
    """
    レンダーウィンドウのベースHTMLを生成

    Returns:
        生成されたHTMLコード
    """
    return (
        """
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
            iframe {
                transition: opacity 0.15s ease-in-out;
            }
        </style>
        <script>
            """
        + create_resize_handler_js()
        + """
        </script>
    </head>
    <body>
    </body>
    </html>
    """
    )
