let trackBlocks = []; // 各レーンのブロックを格納する配列
let currentBpm = 120;
let currentDelay = 0;
let currentRenderWidth = 1000;
let currentRenderHeight = 1000;
let isPlaying = false;
let currentPlayingIndexes = []; // 各レーンの現在再生中のブロックインデックス
let playIntervals = []; // 各レーンの再生タイマー
let draggedTrackIndex = null;
let selectedTrackIndexes = []; // 各レーンの選択されたブロックインデックス
let playingTrackIndexes = []; // 各レーンの現在再生中のブロックインデックス
let clickToPlayEnabled = false;
let lanes = []; // レーンの情報を格納

// 初期化
document.addEventListener("DOMContentLoaded", function () {
  initializeControls();

  // 初期状態でHTMLに存在するレーン要素を考慮
  const existingLanes = document.querySelectorAll(".lane-container");

  // 既存のレーン要素を削除（後で正しいデータで再作成）
  existingLanes.forEach((lane) => lane.remove());
});

// pywebview API との通信
window.addEventListener("pywebviewready", function () {
  console.log("Track window ready");
  loadTrackBlocks();

  // 定期的にrender windowのサイズを確認（手動リサイズの検出）
  setInterval(checkRenderWindowSize, 1000);
});

function initializeControls() {
  const playButton = document.getElementById("play-button");
  const stopButton = document.getElementById("stop-button");
  const bpmInput = document.getElementById("bpm-input");
  const delayInput = document.getElementById("delay-input");
  const clickToggle = document.getElementById("click-toggle");
  const applySizeButton = document.getElementById("apply-size-button");
  const addLaneButton = document.getElementById("add-lane-button");

  playButton.addEventListener("click", startPlayback);
  stopButton.addEventListener("click", stopPlayback);
  bpmInput.addEventListener("change", updateBpm);
  delayInput.addEventListener("change", updateDelay);
  clickToggle.addEventListener("change", updateClickToPlay);
  applySizeButton.addEventListener("click", applyRenderSize);
  addLaneButton.addEventListener("click", addLane);
}

function createLaneElement(laneId) {
  try {
    const laneContainer = document.createElement("div");
    laneContainer.id = `lane-${laneId}`;
    laneContainer.className = "lane-container";
    laneContainer.innerHTML = `
      <div class="lane-header">
        <span class="lane-title">Lane ${laneId + 1}</span>
        <div class="lane-controls">
          <button class="lane-remove-btn" onclick="removeLane(${laneId})">×</button>
        </div>
      </div>
      <div class="lane-content">
        <div id="track-lane-${laneId}" class="track-lane">
        </div>
      </div>
    `;

    const lanesContainer = document.getElementById("lanes-container");
    if (lanesContainer) {
      lanesContainer.appendChild(laneContainer);
    }
  } catch (error) {
    console.error(`Error creating lane element ${laneId + 1}:`, error);
  }
}

function addLane() {
  try {
    const laneId = lanes.length;
    createLaneElement(laneId);
    lanes.push({
      id: laneId,
      blocks: [],
    });

    // trackBlocks配列に新しいレーンの配列を追加
    trackBlocks.push([]);

    // 新しいレーンの状態配列を初期化
    selectedTrackIndexes[laneId] = null;
    currentPlayingIndexes[laneId] = 0;
    playingTrackIndexes[laneId] = null;
    playIntervals[laneId] = null;
    saveTrackBlocks();
  } catch (error) {
    console.error("Error adding lane:", error);
  }
}

function removeLane(laneId) {
  if (lanes.length <= 1) {
    alert("At least one lane is required");
    return;
  }

  // レーン要素を削除
  const laneElement = document.getElementById(`lane-${laneId}`);
  if (laneElement) {
    laneElement.remove();
  }

  // 配列から削除
  lanes.splice(laneId, 1);
  trackBlocks.splice(laneId, 1);

  // 残りのレーンのIDを再割り当て
  lanes.forEach((lane, index) => {
    lane.id = index;
    const laneElement = document.getElementById(`lane-${index}`);
    if (laneElement) {
      laneElement.id = `lane-${index}`;
      laneElement.querySelector(".lane-title").textContent = `Lane ${
        index + 1
      }`;
      laneElement.querySelector(".lane-remove-btn").onclick = () =>
        removeLane(index);
      laneElement.querySelector(".track-lane").id = `track-lane-${index}`;
    }
  });

  saveTrackBlocks();
  renderTrackBlocks();
}

function updateClickToPlay() {
  const clickToggle = document.getElementById("click-toggle");
  clickToPlayEnabled = clickToggle.checked;

  // Python側に状態を通知
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.update_click_to_play_state(clickToPlayEnabled);
  }
}

function loadTrackBlocks() {
  // Python側からトラックブロックを読み込み
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api
      .get_track_blocks()
      .then((data) => {
        try {
          trackBlocks = data.track_blocks || [[]]; // デフォルトで1つのレーン
          currentBpm = data.bpm || 120;
          // delayの値が設定されている場合のみ更新（ユーザーが変更した値を保持）
          if (data.delay !== undefined && data.delay !== null) {
            currentDelay = data.delay;
          }
          currentRenderWidth = data.render_width || 1000;
          currentRenderHeight = data.render_height || 1000;

          // レーンの初期化
          lanes = [];
          selectedTrackIndexes = []; // 選択状態をリセット
          currentPlayingIndexes = []; // 再生状態をリセット
          playingTrackIndexes = []; // 再生中状態をリセット
          playIntervals = []; // タイマーをリセット
          for (let i = 0; i < trackBlocks.length; i++) {
            lanes.push({
              id: i,
              blocks: trackBlocks[i] || [],
            });
            selectedTrackIndexes[i] = null; // 各レーンの選択状態を初期化
            currentPlayingIndexes[i] = 0; // 各レーンの再生状態を初期化
            playingTrackIndexes[i] = null; // 各レーンの再生中状態を初期化
            playIntervals[i] = null; // 各レーンのタイマーを初期化
          }

          // 既存のレーン要素をすべて削除
          const existingLanes = document.querySelectorAll(".lane-container");
          existingLanes.forEach((lane) => lane.remove());

          // 必要なレーン要素を作成
          lanes.forEach((lane, index) => {
            console.log(`Creating lane ${index + 1}`);
            createLaneElement(index);
          });

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

          // レンダーサイズ入力フィールドを更新
          const renderWidthInput = document.getElementById("render-width");
          if (renderWidthInput) {
            renderWidthInput.value = currentRenderWidth;
          }

          const renderHeightInput = document.getElementById("render-height");
          if (renderHeightInput) {
            renderHeightInput.value = currentRenderHeight;
          }

          renderTrackBlocks();
        } catch (error) {
          console.error("Error processing track data:", error);
          // エラーが発生した場合はデフォルト値を使用
          trackBlocks = [[]];
          lanes = [{ id: 0, blocks: [] }];
          selectedTrackIndexes = [null]; // 選択状態を初期化
          currentPlayingIndexes = [0]; // 再生状態を初期化
          playingTrackIndexes = [null]; // 再生中状態を初期化
          playIntervals = [null]; // タイマーを初期化
          renderTrackBlocks();
        }
      })
      .catch((error) => {
        console.error("Error calling get_track_blocks:", error);
        // API呼び出しに失敗した場合はデフォルト値を使用
        trackBlocks = [[]];
        lanes = [{ id: 0, blocks: [] }];
        selectedTrackIndexes = [null]; // 選択状態を初期化
        currentPlayingIndexes = [0]; // 再生状態を初期化
        playingTrackIndexes = [null]; // 再生中状態を初期化
        playIntervals = [null]; // タイマーを初期化
        renderTrackBlocks();
      });
  } else {
    console.error("pywebview API not available");
    // APIが利用できない場合はデフォルト値を使用
    trackBlocks = [[]];
    lanes = [{ id: 0, blocks: [] }];
    selectedTrackIndexes = [null]; // 選択状態を初期化
    currentPlayingIndexes = [0]; // 再生状態を初期化
    playingTrackIndexes = [null]; // 再生中状態を初期化
    playIntervals = [null]; // タイマーを初期化
    renderTrackBlocks();
  }
}

function saveTrackBlocks() {
  // Python側にトラックブロックを保存（参照データのみ）
  if (window.pywebview && window.pywebview.api) {
    // 参照データのみを送信
    const referenceBlocks = trackBlocks.map((laneBlocks) =>
      laneBlocks.map((block) => ({
        block_id: block.block_id,
        duration: block.duration,
        bars: block.bars,
      }))
    );
    window.pywebview.api.save_track_blocks(referenceBlocks);
  }
}

function renderTrackBlocks() {
  try {
    // 各レーンをレンダリング
    lanes.forEach((lane, laneIndex) => {
      renderLaneBlocks(laneIndex);
    });
  } catch (error) {
    console.error("Error rendering track blocks:", error);
  }
}

function renderLaneBlocks(laneIndex) {
  try {
    const laneElement = document.getElementById(`track-lane-${laneIndex}`);
    if (laneElement) {
      laneElement.innerHTML = "";
      const laneBlocks = trackBlocks[laneIndex] || [];
      laneBlocks.forEach((block, blockIndex) => {
        try {
          const blockElement = createTrackBlockElement(
            block,
            blockIndex,
            laneIndex
          );
          laneElement.appendChild(blockElement);
        } catch (error) {
          console.error(
            `Error creating block element for lane ${laneIndex}, block ${blockIndex}:`,
            error
          );
        }
      });
    } else {
      console.warn(`Lane element track-lane-${laneIndex} not found`);
    }
  } catch (error) {
    console.error(`Error rendering lane ${laneIndex} blocks:`, error);
  }
}

function createTrackBlockElement(block, index, laneIndex) {
  const blockDiv = document.createElement("div");
  const isSelected = selectedTrackIndexes[laneIndex] === index; // 各レーンで独立した選択
  const isPlaying = playingTrackIndexes[laneIndex] === index; // このレーンの現在再生中のブロック
  const isCompleted =
    currentPlayingIndexes[laneIndex] !== undefined &&
    index < currentPlayingIndexes[laneIndex]; // このレーンの完了したブロック

  let className = "track-block bg-base-200 border border-neutral";
  if (isSelected) className += " selected border-primary";
  if (isPlaying) className += " playing";
  if (isCompleted) className += " completed";

  blockDiv.className = className;
  blockDiv.dataset.index = index;
  blockDiv.dataset.laneIndex = laneIndex;
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
    updateBlockBars(index, parseInt(e.target.value) || 8, laneIndex);
  };

  barsDiv.appendChild(barsLabel);
  barsDiv.appendChild(barsInput);

  const removeButton = document.createElement("button");
  removeButton.className = "track-block-remove";
  removeButton.textContent = "×";
  removeButton.onclick = (e) => {
    e.stopPropagation();
    removeTrackBlock(index, laneIndex);
  };

  // ドラッグ&ドロップイベント
  blockDiv.ondragstart = (e) => {
    draggedTrackIndex = index;
    blockDiv.classList.add("dragging");
    e.dataTransfer.effectAllowed = "move";
    e.dataTransfer.setData("text/html", JSON.stringify({ index, laneIndex }));
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
      const dragData = JSON.parse(e.dataTransfer.getData("text/html"));
      moveTrackBlock(dragData.index, index, dragData.laneIndex, laneIndex);
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
    selectTrackBlock(index, laneIndex);
  };

  blockDiv.appendChild(nameDiv);
  blockDiv.appendChild(durationDiv);
  blockDiv.appendChild(barsDiv);
  blockDiv.appendChild(removeButton);

  return blockDiv;
}

function addTrackBlockInternal(blockData, laneIndex = 0) {
  const bars = 8; // デフォルトの小節数
  const duration = Math.round((60 / currentBpm) * 4 * bars * 1000); // BPMから8小節分の再生時間を計算（ミリ秒）
  const trackBlock = {
    block_id: blockData.id,
    name: blockData.name,
    code: blockData.code,
    duration: duration,
    bars: bars,
  };

  // 指定されたレーンにブロックを追加
  if (!trackBlocks[laneIndex]) {
    trackBlocks[laneIndex] = [];
  }
  trackBlocks[laneIndex].push(trackBlock);
  saveTrackBlocks();
  renderTrackBlocks();
}

function removeTrackBlock(index, laneIndex) {
  if (trackBlocks[laneIndex] && index < trackBlocks[laneIndex].length) {
    trackBlocks[laneIndex].splice(index, 1);

    // 選択インデックスを調整
    if (selectedTrackIndexes[laneIndex] === index) {
      selectedTrackIndexes[laneIndex] = null;
    } else if (selectedTrackIndexes[laneIndex] > index) {
      selectedTrackIndexes[laneIndex]--;
    }

    saveTrackBlocks();
    renderTrackBlocks();
  }
}

function startPlayback() {
  if (isPlaying) {
    return;
  }

  // 各レーンにブロックがあるかチェック
  const hasBlocks = trackBlocks.some((lane) => lane.length > 0);
  if (!hasBlocks) {
    console.log("Playback not started: no blocks in any lane");
    return;
  }

  isPlaying = true;

  // エディタの単一iframeをクリア
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.clear_single_iframe().catch((error) => {
      console.error("Error clearing single iframe:", error);
    });
  }

  // 各レーンの再生状態を初期化
  currentPlayingIndexes = [];
  playIntervals = [];

  trackBlocks.forEach((laneBlocks, laneIndex) => {
    // 選択されたブロックがある場合はそこから開始、なければ最初から
    let startIndex = 0;
    if (
      selectedTrackIndexes[laneIndex] !== null &&
      selectedTrackIndexes[laneIndex] < laneBlocks.length
    ) {
      startIndex = selectedTrackIndexes[laneIndex];
    }
    currentPlayingIndexes[laneIndex] = startIndex;
    playIntervals[laneIndex] = null;
  });

  const playButton = document.getElementById("play-button");
  const stopButton = document.getElementById("stop-button");

  playButton.disabled = true;
  stopButton.disabled = false;

  // delayがある場合は、delay後に各レーンの再生を開始
  if (currentDelay > 0) {
    setTimeout(() => {
      if (isPlaying) {
        startAllLanes();
      }
    }, currentDelay);
  } else {
    startAllLanes();
  }
}

function startAllLanes() {
  trackBlocks.forEach((laneBlocks, laneIndex) => {
    if (laneBlocks.length > 0) {
      playLaneNextBlock(laneIndex);
    }
  });
}

function stopPlayback() {
  isPlaying = false;
  currentPlayingIndexes = [];
  playingTrackIndexes = [];

  const playButton = document.getElementById("play-button");
  const stopButton = document.getElementById("stop-button");

  playButton.disabled = false;
  stopButton.disabled = true;

  // 各レーンのタイマーをクリア
  playIntervals.forEach((interval, laneIndex) => {
    if (interval) {
      clearTimeout(interval);
      playIntervals[laneIndex] = null;
    }
  });

  // 全レーンのiframeをクリア
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.clear_all_lanes().catch((error) => {
      console.error("Error calling clear_all_lanes:", error);
    });
  }

  // レーンを再描画して再生状態をリセット
  renderTrackBlocks();
}

function playLaneNextBlock(laneIndex) {
  const laneBlocks = trackBlocks[laneIndex];
  const currentIndex = currentPlayingIndexes[laneIndex];

  if (!isPlaying || !laneBlocks || currentIndex >= laneBlocks.length) {
    // このレーンの再生が終了
    playingTrackIndexes[laneIndex] = null;

    // このレーンのiframeをクリア
    if (window.pywebview && window.pywebview.api) {
      window.pywebview.api.clear_specific_lane(laneIndex).catch((error) => {
        console.error(`Error clearing lane ${laneIndex + 1}:`, error);
      });
    }

    renderLaneBlocks(laneIndex);

    // 全レーンの再生が終了したかチェック
    checkAllLanesFinished();
    return;
  }

  // 現在再生中のブロックインデックスを更新（このレーンのみ）
  playingTrackIndexes[laneIndex] = currentIndex;
  const block = laneBlocks[currentIndex];

  // 単一レーンの再生（他のレーンに影響しない）
  if (window.pywebview && window.pywebview.api) {
    // このレーンのiframeのみを更新
    updateSingleLane(laneIndex, block);
  }

  // このレーンのみ再描画して再生状態を更新
  renderLaneBlocks(laneIndex);

  // 次のブロックの再生をスケジュール（このレーンのみ）
  playIntervals[laneIndex] = setTimeout(() => {
    currentPlayingIndexes[laneIndex]++;
    playLaneNextBlock(laneIndex);
  }, block.duration);
}

function updateSingleLane(laneIndex, block) {
  if (window.pywebview && window.pywebview.api) {
    // このレーンのiframeのみを更新（他のレーンに影響しない）
    window.pywebview.api
      .update_single_lane(laneIndex, block.code)
      .catch((error) => {
        console.error(
          `Lane ${laneIndex + 1}: Error calling update_single_lane:`,
          error
        );
      });
  }
}

function checkAllLanesFinished() {
  // 全レーンの再生が終了したかチェック
  const allFinished = trackBlocks.every((laneBlocks, laneIndex) => {
    const currentIndex = currentPlayingIndexes[laneIndex];
    return !laneBlocks || currentIndex >= laneBlocks.length;
  });

  if (allFinished) {
    console.log("All lanes finished playing");
    stopPlayback();
  }
}

function updateBpm() {
  const bpm = parseInt(document.getElementById("bpm-input").value) || 120;
  currentBpm = bpm;

  // 既存のブロックのdurationを新しいBPMで更新
  let durationUpdated = false;
  trackBlocks.forEach((laneBlocks, laneIndex) => {
    laneBlocks.forEach((block, blockIndex) => {
      if (block.bars) {
        const oldDuration = block.duration;
        block.duration = Math.round((60 / currentBpm) * 4 * block.bars * 1000);
        if (oldDuration !== block.duration) {
          durationUpdated = true;
        }
      }
    });
  });

  // Python側にBPMを保存
  if (window.pywebview && window.pywebview.api) {
    console.log(`Updating BPM to ${bpm} via Python API`);
    window.pywebview.api
      .update_bpm(bpm)
      .then((result) => {
        if (result.status === "success") {
          // durationが更新された場合は、更新されたtrackBlocksも保存
          if (durationUpdated) {
            window.pywebview.api
              .save_track_blocks(trackBlocks)
              .then((saveResult) => {
                renderTrackBlocks();
              })
              .catch((saveError) => {
                console.error("Error saving track blocks:", saveError);
                renderTrackBlocks();
              });
          } else {
            renderTrackBlocks();
          }
        } else {
          console.error("Failed to update BPM:", result.message);
          // エラーの場合はJavaScript側でも保存
          saveTrackBlocks();
          renderTrackBlocks();
        }
      })
      .catch((error) => {
        console.error("Error calling update_bpm:", error);
        // エラーの場合はJavaScript側でも保存
        saveTrackBlocks();
        renderTrackBlocks();
      });
  } else {
    console.error("pywebview API not available");
    saveTrackBlocks();
    renderTrackBlocks();
  }
}

function updateDelay() {
  const delay = parseInt(document.getElementById("delay-input").value) || 0;

  // Python側にDelayを保存
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.update_delay(delay).then((result) => {
      if (result.status === "success") {
        // 保存成功後にcurrentDelayを更新
        currentDelay = delay;
      }
    });
  } else {
    // APIが利用できない場合は即座に更新
    currentDelay = delay;
  }
}

function applyRenderSize() {
  const width = parseInt(document.getElementById("render-width").value) || 1000;
  const height =
    parseInt(document.getElementById("render-height").value) || 1000;

  // 値の範囲を制限
  const clampedWidth = Math.max(100, Math.min(3000, width));
  const clampedHeight = Math.max(100, Math.min(3000, height));

  // 入力フィールドを更新された値で更新
  document.getElementById("render-width").value = clampedWidth;
  document.getElementById("render-height").value = clampedHeight;

  currentRenderWidth = clampedWidth;
  currentRenderHeight = clampedHeight;

  // Python側にレンダーサイズを更新
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.update_render_size(clampedWidth, clampedHeight);
  } else {
    console.error("pywebview API not available");
  }
}

function checkRenderWindowSize() {
  if (window.pywebview?.api) {
    window.pywebview.api
      .get_render_size()
      .then((data) => {
        if (
          data.width !== currentRenderWidth ||
          data.height !== currentRenderHeight
        ) {
          currentRenderWidth = data.width;
          currentRenderHeight = data.height;
          document.getElementById("render-width").value = data.width;
          document.getElementById("render-height").value = data.height;
        }
      })
      .catch((error) => {
        console.error("Error checking render size:", error);
      });
  }
}

function updateBlockBars(index, bars, laneIndex) {
  if (
    trackBlocks[laneIndex] &&
    index >= 0 &&
    index < trackBlocks[laneIndex].length
  ) {
    const block = trackBlocks[laneIndex][index];
    block.bars = bars;
    block.duration = Math.round((60 / currentBpm) * 4 * bars * 1000);

    // Python側に更新されたtrackBlocksを保存
    if (window.pywebview && window.pywebview.api) {
      window.pywebview.api
        .save_track_blocks(trackBlocks)
        .then((result) => {
          if (result.status != "success") {
            saveTrackBlocks();
          }
          renderTrackBlocks();
        })
        .catch((error) => {
          saveTrackBlocks();
          renderTrackBlocks();
        });
    } else {
      console.error("pywebview API not available");
      saveTrackBlocks();
      renderTrackBlocks();
    }
  }
}

function moveTrackBlock(fromIndex, toIndex, fromLaneIndex, toLaneIndex) {
  if (
    (fromIndex === toIndex && fromLaneIndex === toLaneIndex) ||
    fromIndex < 0 ||
    fromLaneIndex < 0 ||
    !trackBlocks[fromLaneIndex] ||
    fromIndex >= trackBlocks[fromLaneIndex].length ||
    toIndex < 0 ||
    toLaneIndex < 0 ||
    !trackBlocks[toLaneIndex] ||
    toIndex >= trackBlocks[toLaneIndex].length
  ) {
    return;
  }

  // ブロックの順序を変更
  const movedBlock = trackBlocks[fromLaneIndex].splice(fromIndex, 1)[0];
  trackBlocks[toLaneIndex].splice(toIndex, 0, movedBlock);

  // 移動したブロックを選択状態にする
  selectedTrackIndexes[toLaneIndex] = toIndex;

  saveTrackBlocks();
  renderTrackBlocks();
}

function selectTrackBlock(index, laneIndex) {
  selectedTrackIndexes[laneIndex] = index;
  renderTrackBlocks();
}

// エディタウィンドウからのブロック追加要求を受け取る
window.addTrackBlock = function (blockData, laneIndex = 0) {
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

    window.pywebview.api
      .add_track_block(trackBlock, laneIndex)
      .then((result) => {
        if (result.status === "success") {
          // 追加後に最新のデータを再読み込み
          loadTrackBlocks();
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
