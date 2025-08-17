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
    item.className = "block-item" + (isSelected ? " active" : "");
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
      addBlockToTrack(i);
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

    item.appendChild(handle);
    item.appendChild(nameSpan);
    item.appendChild(addTrackButton);
    item.appendChild(deleteButton);

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
 * 指定したインデックスのブロックをトラックに追加する
 * @param {number} index - 追加するブロックのインデックス
 */
function addBlockToTrack(index) {
  if (index >= 0 && index < blocks.length) {
    // Python側のAPIを呼び出してトラックに追加
    window.pywebview.api.add_block_to_track(index).then((result) => {
      if (result.status === "success") {
        console.log("Block added to track successfully");
      } else {
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
    editor = monaco.editor.create(document.getElementById("editor"), {
      value: "// Select or add a block",
      language: "javascript",
      theme: "vs-dark",
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
