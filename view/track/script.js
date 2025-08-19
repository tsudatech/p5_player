let trackBlocks = [];
let currentBpm = 120;
let currentDelay = 0;
let isPlaying = false;
let currentPlayingIndex = 0;
let playInterval = null;
let draggedTrackIndex = null;
let selectedTrackIndex = null;
let playingTrackIndex = null;
let clickToPlayEnabled = false;

// 初期化
document.addEventListener("DOMContentLoaded", function () {
  initializeControls();
});

// pywebview API との通信
window.addEventListener("pywebviewready", function () {
  console.log("Track window ready");
  loadTrackBlocks();
});

function initializeControls() {
  const playButton = document.getElementById("play-button");
  const stopButton = document.getElementById("stop-button");
  const bpmInput = document.getElementById("bpm-input");
  const delayInput = document.getElementById("delay-input");
  const clickToggle = document.getElementById("click-toggle");

  playButton.addEventListener("click", startPlayback);
  stopButton.addEventListener("click", stopPlayback);
  bpmInput.addEventListener("change", updateBpm);
  delayInput.addEventListener("change", updateDelay);
  clickToggle.addEventListener("change", updateClickToPlay);
}

function updateClickToPlay() {
  const clickToggle = document.getElementById("click-toggle");
  clickToPlayEnabled = clickToggle.checked;
  console.log("Click to play enabled:", clickToPlayEnabled);

  // Python側に状態を通知
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.update_click_to_play_state(clickToPlayEnabled);
  }
}

function loadTrackBlocks() {
  // Python側からトラックブロックを読み込み
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.get_track_blocks().then((data) => {
      trackBlocks = data.track_blocks || [];
      currentBpm = data.bpm || 120;
      currentDelay = data.delay || 0;

      // BPM入力フィールドを更新
      const bpmInput = document.getElementById("bpm-input");
      if (bpmInput) {
        bpmInput.value = currentBpm;
      }

      // Delay入力フィールドを更新
      const delayInput = document.getElementById("delay-input");
      if (delayInput) {
        delayInput.value = currentDelay;
      }

      renderTrackBlocks();
    });
  }
}

function saveTrackBlocks() {
  // Python側にトラックブロックを保存
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.save_track_blocks(trackBlocks);
  }
}

function renderTrackBlocks() {
  const lane = document.getElementById("track-lane");
  lane.innerHTML = "";

  trackBlocks.forEach((block, index) => {
    const blockElement = createTrackBlockElement(block, index);
    lane.appendChild(blockElement);
  });
}

function createTrackBlockElement(block, index) {
  const blockDiv = document.createElement("div");
  const isSelected = index === selectedTrackIndex;
  const isPlaying = index === playingTrackIndex;
  const isCompleted = isPlaying && index < currentPlayingIndex;

  let className = "track-block bg-base-200 border border-neutral";
  if (isSelected) className += " selected border-primary";
  if (isPlaying) className += " playing";
  if (isCompleted) className += " completed";

  blockDiv.className = className;
  blockDiv.dataset.index = index;
  blockDiv.draggable = true;

  const nameDiv = document.createElement("div");
  nameDiv.className = "track-block-name";
  nameDiv.textContent = block.name || "Block";

  const durationDiv = document.createElement("div");
  durationDiv.className = "track-block-duration";
  durationDiv.textContent = `${block.duration}ms`;

  // 小節数設定
  const barsDiv = document.createElement("div");
  barsDiv.className = "track-block-bars";

  const barsLabel = document.createElement("label");
  barsLabel.textContent = "Bars:";

  const barsInput = document.createElement("input");
  barsInput.type = "number";
  barsInput.min = "1";
  barsInput.max = "32";
  barsInput.value = block.bars || 8;
  barsInput.onchange = (e) => {
    updateBlockBars(index, parseInt(e.target.value) || 8);
  };

  barsDiv.appendChild(barsLabel);
  barsDiv.appendChild(barsInput);

  const removeButton = document.createElement("button");
  removeButton.className = "track-block-remove";
  removeButton.textContent = "×";
  removeButton.onclick = (e) => {
    e.stopPropagation();
    removeTrackBlock(index);
  };

  // ドラッグ&ドロップイベント
  blockDiv.ondragstart = (e) => {
    draggedTrackIndex = index;
    blockDiv.classList.add("dragging");
    e.dataTransfer.effectAllowed = "move";
    e.dataTransfer.setData("text/html", index);
  };

  blockDiv.ondragend = () => {
    blockDiv.classList.remove("dragging");
    draggedTrackIndex = null;
    // 全てのブロックのドラッグオーバー状態をリセット
    document.querySelectorAll(".track-block").forEach((block) => {
      block.classList.remove("drag-over");
    });
    // レーンを再描画して状態をリセット
    renderTrackBlocks();
  };

  blockDiv.ondragover = (e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    if (draggedTrackIndex !== null && draggedTrackIndex !== index) {
      blockDiv.classList.add("drag-over");
    }
  };

  blockDiv.ondragleave = () => {
    blockDiv.classList.remove("drag-over");
  };

  blockDiv.ondrop = (e) => {
    e.preventDefault();
    blockDiv.classList.remove("drag-over");
    if (draggedTrackIndex !== null && draggedTrackIndex !== index) {
      moveTrackBlock(draggedTrackIndex, index);
    }
    // ドロップ後も全てのブロックのドラッグオーバー状態をリセット
    document.querySelectorAll(".track-block").forEach((block) => {
      block.classList.remove("drag-over");
    });
  };

  // クリックで選択
  blockDiv.onclick = (e) => {
    // 削除ボタンや小節数入力フィールドのクリックは除外
    if (
      e.target.classList.contains("track-block-remove") ||
      e.target.tagName === "INPUT"
    ) {
      return;
    }
    selectTrackBlock(index);
  };

  blockDiv.appendChild(nameDiv);
  blockDiv.appendChild(durationDiv);
  blockDiv.appendChild(barsDiv);
  blockDiv.appendChild(removeButton);

  return blockDiv;
}

function addTrackBlockInternal(blockData) {
  const bars = 8; // デフォルトの小節数
  const duration = Math.round((60 / currentBpm) * 4 * bars * 1000); // BPMから8小節分の再生時間を計算（ミリ秒）

  const trackBlock = {
    id: blockData.id,
    name: blockData.name,
    code: blockData.code,
    duration: duration,
    bars: bars,
  };

  trackBlocks.push(trackBlock);
  saveTrackBlocks();
  renderTrackBlocks();
}

function removeTrackBlock(index) {
  trackBlocks.splice(index, 1);

  // 選択インデックスを調整
  if (selectedTrackIndex === index) {
    selectedTrackIndex = null;
  } else if (selectedTrackIndex > index) {
    selectedTrackIndex--;
  }

  saveTrackBlocks();
  renderTrackBlocks();
}

function startPlayback() {
  if (trackBlocks.length === 0 || isPlaying) return;

  isPlaying = true;

  // 選択されたブロックがある場合はそこから開始、なければ最初から
  if (selectedTrackIndex !== null && selectedTrackIndex < trackBlocks.length) {
    currentPlayingIndex = selectedTrackIndex;
  } else {
    currentPlayingIndex = 0;
  }

  const playButton = document.getElementById("play-button");
  const stopButton = document.getElementById("stop-button");

  playButton.disabled = true;
  stopButton.disabled = false;

  playNextBlock();
}

function stopPlayback() {
  isPlaying = false;
  currentPlayingIndex = 0;
  playingTrackIndex = null;

  const playButton = document.getElementById("play-button");
  const stopButton = document.getElementById("stop-button");

  playButton.disabled = false;
  stopButton.disabled = true;

  if (playInterval) {
    clearTimeout(playInterval);
    playInterval = null;
  }

  // レーンを再描画して再生状態をリセット
  renderTrackBlocks();
}

function playNextBlock() {
  if (!isPlaying || currentPlayingIndex >= trackBlocks.length) {
    stopPlayback();
    return;
  }

  const block = trackBlocks[currentPlayingIndex];

  // 現在再生中のブロックインデックスを更新
  playingTrackIndex = currentPlayingIndex;

  // Python側にコードを送信して実行
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.play_track_block(block.code);
  }

  // レーンを再描画して再生状態を更新
  renderTrackBlocks();

  // 次のブロックの再生をスケジュール
  playInterval = setTimeout(() => {
    currentPlayingIndex++;
    playNextBlock();
  }, block.duration);
}

function updateBpm() {
  const bpm = parseInt(document.getElementById("bpm-input").value) || 120;
  currentBpm = bpm;

  // 既存のブロックの再生時間を更新（各ブロックの小節数を使用）
  trackBlocks.forEach((block) => {
    const bars = block.bars || 8;
    block.duration = Math.round((60 / bpm) * 4 * bars * 1000);
  });

  // Python側にBPMを保存
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.update_bpm(bpm);
  }

  saveTrackBlocks();
  renderTrackBlocks();
}

function updateDelay() {
  const delay = parseInt(document.getElementById("delay-input").value) || 0;
  currentDelay = delay;

  // Python側にDelayを保存
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.update_delay(delay);
  }
}

function updateBlockBars(index, bars) {
  if (index >= 0 && index < trackBlocks.length) {
    trackBlocks[index].bars = bars;
    trackBlocks[index].duration = Math.round(
      (60 / currentBpm) * 4 * bars * 1000
    );
    saveTrackBlocks();
    renderTrackBlocks();
  }
}

function moveTrackBlock(fromIndex, toIndex) {
  if (
    fromIndex === toIndex ||
    fromIndex < 0 ||
    fromIndex >= trackBlocks.length ||
    toIndex < 0 ||
    toIndex >= trackBlocks.length
  ) {
    return;
  }

  // ブロックの順序を変更
  const movedBlock = trackBlocks.splice(fromIndex, 1)[0];
  trackBlocks.splice(toIndex, 0, movedBlock);

  // 移動したブロックを選択状態にする
  selectedTrackIndex = toIndex;

  saveTrackBlocks();
  renderTrackBlocks();
}

function selectTrackBlock(index) {
  selectedTrackIndex = index;
  renderTrackBlocks();
}

// エディタウィンドウからのブロック追加要求を受け取る
window.addTrackBlock = function (blockData) {
  // 文字列として渡された場合はパースする
  if (typeof blockData === "string") {
    try {
      blockData = JSON.parse(blockData);
    } catch (e) {
      console.error("Failed to parse block data:", e);
      return;
    }
  }

  // Python側のAPIを使用してブロックを追加
  if (window.pywebview && window.pywebview.api) {
    const bars = 8; // デフォルトの小節数
    const duration = Math.round((60 / currentBpm) * 4 * bars * 1000);

    const trackBlock = {
      id: blockData.id,
      name: blockData.name,
      code: blockData.code,
      duration: duration,
      bars: bars,
    };

    window.pywebview.api.add_track_block(trackBlock).then((result) => {
      if (result.status === "success") {
        trackBlocks = result.track_blocks;
        renderTrackBlocks();
      }
    });
  }
};

// Python側から呼び出されるplay関数
window.playCurrentTrack = function () {
  console.log("playCurrentTrack called from Python");
  if (!isPlaying) {
    startPlayback();
  } else {
    stopPlayback();
  }
};
