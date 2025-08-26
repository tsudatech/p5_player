let editor;
let blocks = [];
let selectedCodeId = null;
let draggedIndex = null;
let editingIndex = null;
let dropIndicator = null;
let deleteConfirmIndex = null; // 削除確認中のブロックインデックス
let deleteConfirmTimeout = null; // 削除確認のタイムアウト

function refreshBlockList() {
  const listEl = document.getElementById("blockList");
  const dropIndicator = document.getElementById("dropIndicator");

  // 既存のブロックアイテムとドロップゾーンを削除
  const existingItems = listEl.querySelectorAll(".block-item, .drop-zone");
  existingItems.forEach((item) => item.remove());

  // ドロップインジケーターを最初に配置
  listEl.appendChild(dropIndicator);

  blocks.forEach((block, i) => {
    const item = document.createElement("div");
    const isSelected = blocks[i].id === selectedCodeId;
    item.className = "block-item card bg-base-200 border border-primary";
    if (!isSelected) {
      item.style.borderColor = "#1e293b";
    }
    item.draggable = true;
    item.dataset.index = i;

    // ドラッグハンドル
    const handle = document.createElement("span");
    handle.className = "drag-handle";
    handle.textContent = "⋮⋮";
    /**
     * ドラッグハンドルのmousedownイベント
     */
    handle.onmousedown = (e) => {
      e.stopPropagation();
      item.draggable = true;
    };

    // ブロック名
    const nameSpan = document.createElement("span");
    nameSpan.className = "block-name";
    const blockName = block.name || `Block ${i + 1}`;
    nameSpan.textContent = blockName;

    // 名前の長さに基づいて横幅を調整
    const tempSpan = document.createElement("span");
    tempSpan.style.visibility = "hidden";
    tempSpan.style.position = "absolute";
    tempSpan.style.whiteSpace = "pre";
    tempSpan.style.font = window.getComputedStyle(nameSpan).font;
    tempSpan.textContent = blockName;
    document.body.appendChild(tempSpan);

    const textWidth = tempSpan.offsetWidth;
    document.body.removeChild(tempSpan);

    const minWidth = 60;
    const padding = 8;
    const width = Math.max(minWidth, textWidth + padding);
    nameSpan.style.width = width + "px";

    /**
     * ブロック名クリックで編集開始
     */
    nameSpan.onclick = (e) => {
      e.stopPropagation();
      startEditingName(i, nameSpan);
    };

    // トラック追加ボタン
    const addTrackButton = document.createElement("button");
    addTrackButton.className = "add-track-button";
    addTrackButton.textContent = "+";
    addTrackButton.title = "Add to track";

    /**
     * トラック追加ボタンクリックでブロックをトラックに追加
     */
    addTrackButton.onclick = (e) => {
      e.stopPropagation();
      showLaneSelectionDialog(i);
    };

    // 削除ボタン
    const deleteButton = document.createElement("button");
    deleteButton.className = "delete-button";
    deleteButton.textContent = "×";
    deleteButton.title =
      "Click once to prepare deletion, click again to confirm";

    /**
     * 削除ボタンクリックでブロックを削除（2回押下で削除）
     */
    deleteButton.onclick = (e) => {
      e.stopPropagation();
      handleDeleteClick(i, deleteButton, blockName);
    };

    // ボタンコンテナを作成
    const buttonContainer = document.createElement("div");
    buttonContainer.className = "flex ml-auto";
    buttonContainer.appendChild(addTrackButton);
    buttonContainer.appendChild(deleteButton);

    item.appendChild(handle);
    item.appendChild(nameSpan);
    item.appendChild(buttonContainer);

    /**
     * ブロックアイテムクリックで選択
     */
    item.onclick = () => selectBlock(i);

    /**
     * ブロックアイテムのドラッグ開始
     */
    item.ondragstart = (e) => {
      draggedIndex = i;
      item.classList.add("dragging");
      e.dataTransfer.effectAllowed = "move";
      e.dataTransfer.setData("text/html", i);
    };

    /**
     * ブロックアイテムのドラッグ終了
     */
    item.ondragend = () => {
      item.classList.remove("dragging");
      draggedIndex = null;
      hideDropIndicator();
      // 全てのドロップゾーンのハイライトを削除
      document.querySelectorAll(".drop-zone").forEach((zone) => {
        zone.classList.remove("drag-over");
      });
    };

    /**
     * ブロックアイテム上でドラッグ中の要素が来たとき
     */
    item.ondragover = (e) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = "move";
      if (draggedIndex !== null && draggedIndex !== i) {
        // 常にブロックの上に青い線を表示
        showDropIndicator(item, "before");
      }
    };

    /**
     * ブロックアイテムからドラッグ中の要素が離れたとき
     */
    item.ondragleave = () => {
      hideDropIndicator();
    };

    /**
     * ブロックアイテムにドロップされたとき
     */
    item.ondrop = (e) => {
      e.preventDefault();
      hideDropIndicator();
      if (draggedIndex !== null && draggedIndex !== i) {
        // 常にブロックの上にドロップ（ブロックの位置に移動）
        moveBlock(draggedIndex, i);
      }
    };

    listEl.appendChild(item);
  });
}

/**
 * ドロップインジケーターを表示する
 * @param {HTMLElement} element - 対象要素
 * @param {"before"|"after"} position - 表示位置
 */
function showDropIndicator(element, position) {
  const indicator = document.getElementById("dropIndicator");
  const rect = element.getBoundingClientRect();
  const containerRect = document
    .getElementById("blockList")
    .getBoundingClientRect();

  if (position === "before") {
    indicator.style.top = rect.top - containerRect.top + "px";
  } else {
    indicator.style.top = rect.bottom - containerRect.top + "px";
  }

  indicator.classList.add("visible");
}

/**
 * ドロップインジケーターを非表示にする
 */
function hideDropIndicator() {
  const indicator = document.getElementById("dropIndicator");
  indicator.classList.remove("visible");
}

/**
 * ブロック名の編集を開始する
 * @param {number} index - 編集対象のブロックインデックス
 * @param {HTMLElement} nameSpan - ブロック名表示用のspan要素
 */
function startEditingName(index, nameSpan) {
  if (!nameSpan || index < 0 || index >= blocks.length) {
    return;
  }

  if (editingIndex !== null) {
    // 既に編集中の場合は保存
    saveEditingName();
  }

  editingIndex = index;
  const currentName = blocks[index].name || `Block ${index + 1}`;

  // 入力フィールドに変更
  const input = document.createElement("input");
  input.type = "text";
  input.value = currentName;
  input.className = "block-name editing";

  // 名前の長さに基づいて横幅を調整
  const tempSpan = document.createElement("span");
  tempSpan.style.visibility = "hidden";
  tempSpan.style.position = "absolute";
  tempSpan.style.whiteSpace = "pre";
  tempSpan.style.font = window.getComputedStyle(nameSpan).font;
  tempSpan.textContent = currentName;
  document.body.appendChild(tempSpan);

  const textWidth = tempSpan.offsetWidth;
  document.body.removeChild(tempSpan);

  // 最小幅を設定し、名前の長さに応じて調整
  const minWidth = 60;
  const padding = 8;
  const width = Math.max(minWidth, textWidth + padding);
  input.style.width = width + "px";

  /**
   * フォーカスが外れたら保存
   */
  input.onblur = () => saveEditingName();
  /**
   * Enterで保存、Escapeでキャンセル
   */
  input.onkeydown = (e) => {
    if (e.key === "Enter") {
      saveEditingName();
    } else if (e.key === "Escape") {
      cancelEditingName();
    }
  };

  /**
   * 入力中に幅を動的に調整
   */
  input.oninput = () => {
    const tempSpan = document.createElement("span");
    tempSpan.style.visibility = "hidden";
    tempSpan.style.position = "absolute";
    tempSpan.style.whiteSpace = "pre";
    tempSpan.style.font = window.getComputedStyle(nameSpan).font;
    tempSpan.textContent = input.value || " ";
    document.body.appendChild(tempSpan);

    const textWidth = tempSpan.offsetWidth;
    document.body.removeChild(tempSpan);

    const minWidth = 60;
    const padding = 8;
    const width = Math.max(minWidth, textWidth + padding);
    input.style.width = width + "px";
  };

  nameSpan.innerHTML = "";
  nameSpan.appendChild(input);
  input.focus();
  input.select();
}

/**
 * ブロック名の編集内容を保存する
 */
function saveEditingName() {
  if (editingIndex === null) return;

  const nameSpan = document.querySelector(
    `[data-index="${editingIndex}"] .block-name`
  );
  if (!nameSpan) {
    editingIndex = null;
    return;
  }

  const input = nameSpan.querySelector("input");
  if (!input) {
    editingIndex = null;
    return;
  }

  const newName = input.value.trim();

  if (newName) {
    window.pywebview.api
      .update_block_name(editingIndex, newName)
      .then((data) => {
        blocks = data.blocks;
        refreshBlockList();
      });
  } else {
    cancelEditingName();
  }

  editingIndex = null;
}

/**
 * ブロック名の編集をキャンセルする
 */
function cancelEditingName() {
  if (editingIndex === null) return;

  const nameSpan = document.querySelector(
    `[data-index="${editingIndex}"] .block-name`
  );
  if (!nameSpan) {
    editingIndex = null;
    return;
  }

  const currentName = blocks[editingIndex].name || `Block ${editingIndex + 1}`;
  nameSpan.textContent = currentName;

  editingIndex = null;
}

/**
 * ブロックの順序を変更し、Python側にも通知する
 * @param {number} fromIndex - 移動元インデックス
 * @param {number} toIndex - 移動先インデックス
 */
function moveBlock(fromIndex, toIndex) {
  // 移動したブロックのIDを取得
  const movedBlockId = blocks[fromIndex].id;

  // ブロックの順序を変更
  const movedBlock = blocks.splice(fromIndex, 1)[0];
  blocks.splice(toIndex, 0, movedBlock);

  // Python側に変更を通知（移動したブロックのIDも渡す）
  window.pywebview.api.reorder_blocks(blocks, movedBlockId).then((data) => {
    blocks = data.blocks;
    selectedCodeId = data.selected_code_id;
    refreshBlockList();

    // 移動したブロックのコードをエディタに表示
    const selectedBlock = blocks.find((block) => block.id === selectedCodeId);
    if (selectedBlock) {
      setTimeout(() => {
        editor.setValue(selectedBlock.code);
      }, 10);
    }
  });
}

/**
 * 新しいブロックを追加する
 */
function addBlock() {
  window.pywebview.api.add_block().then((data) => {
    blocks = data.blocks;
    selectedCodeId = data.selected_code_id;
    refreshBlockList();

    const selectedBlock = blocks.find((block) => block.id === selectedCodeId);
    if (selectedBlock) {
      editor.setValue(selectedBlock.code);
    }
  });
}

/**
 * 指定したインデックスのブロックを選択する
 * @param {number} i - 選択するブロックのインデックス
 */
function selectBlock(i) {
  window.pywebview.api.select_block(i).then((code) => {
    selectedCodeId = blocks[i].id;
    refreshBlockList();
    editor.setValue(code);
  });
}

/**
 * 現在のエディタ内容を保存し、Python側で実行する
 */
function playCode() {
  const code = editor.getValue();
  window.pywebview.api.update_block(code).then((data) => {
    blocks = data.blocks;
    selectedCodeId = data.selected_code_id;
    refreshBlockList();
  });
}

/**
 * 削除ボタンのクリック処理（2回押下で削除）
 * @param {number} index - 削除対象のブロックインデックス
 * @param {HTMLElement} button - 削除ボタン要素
 * @param {string} blockName - ブロック名
 */
function handleDeleteClick(index, button, blockName) {
  // 既存のタイムアウトをクリア
  if (deleteConfirmTimeout) {
    clearTimeout(deleteConfirmTimeout);
  }

  // 同じブロックの2回目のクリックの場合
  if (deleteConfirmIndex === index) {
    // 確認状態をリセット
    deleteConfirmIndex = null;
    deleteConfirmTimeout = null;

    // 実際に削除を実行
    deleteBlock(index);
    return;
  }

  // 異なるブロックのクリックの場合、前の確認状態をリセット
  if (deleteConfirmIndex !== null) {
    const prevButton = document.querySelector(
      `[data-index="${deleteConfirmIndex}"] .delete-button`
    );
    if (prevButton) {
      prevButton.classList.remove("confirm");
    }
  }

  // 新しいブロックの確認状態を設定
  deleteConfirmIndex = index;
  button.classList.add("confirm");
  button.textContent = "!";
  button.title = `Click again to delete "${blockName}"`;

  // 3秒後に確認状態をリセット
  deleteConfirmTimeout = setTimeout(() => {
    if (deleteConfirmIndex === index) {
      button.classList.remove("confirm");
      button.textContent = "×";
      button.title = "Click once to prepare deletion, click again to confirm";
      deleteConfirmIndex = null;
      deleteConfirmTimeout = null;
    }
  }, 3000);
}

/**
 * レーン選択ダイアログを表示する
 * @param {number} blockIndex - 追加するブロックのインデックス
 */
function showLaneSelectionDialog(blockIndex) {
  // 既存のダイアログがあれば削除
  const existingDialog = document.getElementById("lane-selection-dialog");
  if (existingDialog) {
    existingDialog.remove();
  }

  // ダイアログを作成
  const dialog = document.createElement("div");
  dialog.id = "lane-selection-dialog";
  dialog.className =
    "fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50";

  dialog.innerHTML = `
    <div class="bg-base-200 p-6 rounded-lg shadow-lg w-full max-w-md mx-4">
      <h3 class="text-lg font-semibold mb-4">Select Lane</h3>
      <div id="lane-options" class="space-y-2 mb-6"></div>
      <div class="flex justify-end gap-2 sticky bottom-0 bg-base-200 pt-2">
        <button id="cancel-lane-selection" class="btn btn-ghost">Cancel</button>
        <button id="confirm-lane-selection" class="btn btn-primary">Add to Lane</button>
      </div>
    </div>
  `;

  document.body.appendChild(dialog);

  // レーン情報を取得して更新
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api
      .get_track_info_for_editor()
      .then((data) => {
        const laneOptions = document.getElementById("lane-options");
        laneOptions.innerHTML = "";

        const lanes = data.lanes || [];
        lanes.forEach((lane) => {
          const laneDiv = document.createElement("div");
          laneDiv.className = "flex items-center";
          laneDiv.innerHTML = `
          <input type="radio" id="lane-${lane.lane_index}" name="lane" value="${
            lane.lane_index
          }" ${lane.lane_index === 0 ? "checked" : ""} class="mr-2">
          <label for="lane-${lane.lane_index}">${lane.lane_name} (${
            lane.block_count
          } blocks)</label>
        `;
          laneOptions.appendChild(laneDiv);
        });
      })
      .catch((error) => {
        console.error("Error getting track info:", error);
        // エラーが発生した場合はデフォルトのレーンを表示
        const laneOptions = document.getElementById("lane-options");
        laneOptions.innerHTML = `
        <div class="flex items-center">
          <input type="radio" id="lane-0" name="lane" value="0" checked class="mr-2">
          <label for="lane-0">Lane 1 (0 blocks)</label>
        </div>
      `;
      });
  }

  // イベントリスナーを追加
  document.getElementById("cancel-lane-selection").onclick = () => {
    dialog.remove();
  };

  document.getElementById("confirm-lane-selection").onclick = () => {
    const selectedLane = document.querySelector(
      'input[name="lane"]:checked'
    ).value;
    addBlockToTrack(blockIndex, parseInt(selectedLane));
    dialog.remove();
  };

  // 背景クリックでダイアログを閉じる
  dialog.onclick = (e) => {
    if (e.target === dialog) {
      dialog.remove();
    }
  };
}

/**
 * 指定したインデックスのブロックをトラックに追加する
 * @param {number} index - 追加するブロックのインデックス
 * @param {number} laneIndex - 追加するレーンのインデックス
 */
function addBlockToTrack(index, laneIndex = 0) {
  if (index >= 0 && index < blocks.length) {
    // Python側のAPIを呼び出してトラックに追加
    window.pywebview.api.add_block_to_track(index, laneIndex).then((result) => {
      if (result.status != "success") {
        console.error("Failed to add block to track:", result.message);
      }
    });
  }
}

/**
 * 指定したインデックスのブロックを削除する
 * @param {number} index - 削除するブロックのインデックス
 */
function deleteBlock(index) {
  window.pywebview.api.delete_block(index).then((data) => {
    if (data) {
      blocks = data.blocks;
      selectedCodeId = data.selected_code_id;
      refreshBlockList();

      // 現在選択されているブロックのコードをエディタに表示
      const selectedBlock = blocks.find((block) => block.id === selectedCodeId);
      if (selectedBlock) {
        editor.setValue(selectedBlock.code);
      } else {
        editor.setValue("");
      }
    }
  });
}

/**
 * Monacoエディタとブロックリストの初期化処理
 */
function initializeEditor() {
  require.config({
    paths: {
      vs: "https://cdn.jsdelivr.net/npm/monaco-editor@0.52.2/min/vs",
    },
  });
  require(["vs/editor/editor.main"], function () {
    // Tokyo Nightテーマの定義
    monaco.editor.defineTheme("tokyo-night", {
      base: "vs-dark",
      inherit: true,
      rules: [
        { token: "comment", foreground: "5f6996" },
        { token: "keyword", foreground: "bb9af7" },
        { token: "string", foreground: "9ece6a" },
        { token: "number", foreground: "ff9e64" },
        { token: "operator", foreground: "89ddff" },
        { token: "function", foreground: "7aa2f7" },
        { token: "variable", foreground: "c0caf5" },
        { token: "type", foreground: "2ac3de" },
        { token: "class", foreground: "c0caf5" },
        { token: "constant", foreground: "ff9e64" },
        { token: "parameter", foreground: "e0af68" },
        { token: "property", foreground: "7dcfff" },
        { token: "punctuation", foreground: "89ddff" },
        { token: "delimiter", foreground: "89ddff" },
        { token: "tag", foreground: "f7768e" },
        { token: "attribute.name", foreground: "bb9af7" },
        { token: "attribute.value", foreground: "9ece6a" },
        { token: "meta", foreground: "565a6e" },
        { token: "meta.preprocessor", foreground: "bb9af7" },
        { token: "meta.tag", foreground: "f7768e" },
        { token: "storage", foreground: "bb9af7" },
        { token: "storage.type", foreground: "bb9af7" },
        { token: "entity.name.function", foreground: "7aa2f7" },
        { token: "entity.name.class", foreground: "c0caf5" },
        { token: "entity.name.type", foreground: "2ac3de" },
        { token: "entity.name.tag", foreground: "f7768e" },
        { token: "entity.other.attribute-name", foreground: "bb9af7" },
        { token: "support.function", foreground: "2ac3de" },
        { token: "support.constant", foreground: "bb9af7" },
        { token: "support.type", foreground: "2ac3de" },
        { token: "support.class", foreground: "2ac3de" },
        { token: "invalid", foreground: "ff5370" },
        { token: "invalid.deprecated", foreground: "bb9af7" },
      ],
      colors: {
        "editor.background": "#24283b",
        "editor.foreground": "#a9b1d6",
        "editorCursor.foreground": "#c0caf5",
        "editor.lineHighlightBackground": "#292e42",
        "editorLineNumber.activeForeground": "#8089b3",
        "editorLineNumber.foreground": "#3b4261",
        "editor.selectionBackground": "#6f7bb640",
        "editor.inactiveSelectionBackground": "#6f7bb615",
        "editor.wordHighlightBackground": "#6f7bb633",
        "editor.findMatchBackground": "#3d59a166",
        "editor.findMatchHighlightBackground": "#3d59a166",
        "editorBracketMatch.background": "#1f2335",
        "editorBracketMatch.border": "#545c7e",
        "editorIndentGuide.background": "#2d324a",
        "editorIndentGuide.activeBackground": "#3b4261",
        "sideBar.background": "#1f2335",
        "sideBar.foreground": "#8089b3",
        "sideBarTitle.foreground": "#8089b3",
        "statusBar.background": "#1f2335",
        "statusBar.foreground": "#8089b3",
        "titleBar.activeBackground": "#1f2335",
        "titleBar.activeForeground": "#8089b3",
        "activityBar.background": "#1f2335",
        "activityBar.foreground": "#8089b3",
        "activityBar.inactiveForeground": "#41496b",
        "tab.activeBackground": "#1f2335",
        "tab.activeForeground": "#a9b1d6",
        "tab.inactiveBackground": "#1f2335",
        "tab.inactiveForeground": "#8089b3",
        "panel.background": "#1f2335",
        "panel.border": "#1b1e2e",
        "panelTitle.activeBorder": "#3d59a1",
        "panelTitle.activeForeground": "#a9b1d6",
        "panelTitle.inactiveForeground": "#8089b3",
        "input.background": "#1b1e2e",
        "input.foreground": "#a9b1d6",
        "input.placeholderForeground": "#4a5272",
        "input.border": "#282e44",
        "dropdown.background": "#1b1e2e",
        "dropdown.foreground": "#8089b3",
        "dropdown.border": "#1b1e2e",
        "list.activeSelectionBackground": "#2c324a",
        "list.activeSelectionForeground": "#a9b1d6",
        "list.inactiveSelectionBackground": "#292e42",
        "list.inactiveSelectionForeground": "#a9b1d6",
        "list.hoverBackground": "#1b1e2e",
        "list.hoverForeground": "#a9b1d6",
        "list.focusForeground": "#a9b1d6",
        "menu.foreground": "#8089b3",
        "menubar.selectionForeground": "#c0caf5",
        "breadcrumb.foreground": "#545c7e",
        "breadcrumb.focusForeground": "#a9b1d6",
        "breadcrumb.activeSelectionForeground": "#a9b1d6",
        "scrollbarSlider.background": "#9cacff15",
        "scrollbarSlider.hoverBackground": "#9cacff10",
        "scrollbarSlider.activeBackground": "#9cacff22",
      },
    });

    editor = monaco.editor.create(document.getElementById("editor"), {
      value: "// Select or add a block",
      language: "javascript",
      theme: "tokyo-night",
      automaticLayout: true,
      scrollBeyondLastLine: false,
      wordWrap: "on",
      minimap: {
        enabled: false,
      },
    });

    // Ctrl + Lでコードを実行するキーボードショートカットを追加
    document.addEventListener("keydown", function (e) {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        playCode();
      }
    });

    window.addEventListener("pywebviewready", function () {
      window.pywebview.api.get_all_blocks().then((data) => {
        blocks = data.blocks || [];
        selectedCodeId = data.selected_code_id;
        refreshBlockList();

        if (blocks.length > 0) {
          window.pywebview.api.load_first_block().then((res) => {
            selectedCodeId = res.selected_code_id;
            editor.setValue(res.code);
            refreshBlockList();
          });
        }
      });
    });

    // ウィンドウリサイズ時の処理
    let resizeTimeout;
    window.addEventListener("resize", function () {
      clearTimeout(resizeTimeout);
      resizeTimeout = setTimeout(function () {
        // リサイズ完了後にブロックリストを再描画
        if (blocks.length > 0) {
          refreshBlockList();
        }
      }, 100);
    });
  });
}
