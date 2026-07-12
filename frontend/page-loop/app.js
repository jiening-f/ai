/**
 * ═══════════════════════════════════════════
 *  全能脚本 — 循环节点页 前端逻辑
 * ═══════════════════════════════════════════
 */
(() => {
  "use strict";

  const API  = "http://127.0.0.1:8765";
  const POLL = 2000;

  /* ── DOM refs ── */
  const $  = s => document.querySelector(s);

  const dom = {
    statusDot:    $(".status-dot"),
    statusText:   $(".status-text"),
    tabBasic:     $("#tab-basic"),

    mapList:      $("#map-list"),
    mapCount:     $("#map-count"),
    btnAddMap:    $("#btn-add-map"),

    editorTitle:  $("#editor-title"),
    mapNameRow:   $("#map-name-row"),
    mapNameInput: $("#map-name-input"),
    btnDelMap:    $("#btn-del-map"),
    featuresGrid: $("#features-grid"),
    featuresEmpty:$("#features-empty"),
    btnAddFeatWrap:$("#btn-add-feature-wrap"),
    btnAddFeature:$("#btn-add-feature"),

    toggleLoop:   $("#toggle-loop"),
    maxLoops:     $("#max-loops"),
    btnRun:       $("#btn-run"),
    btnStop:      $("#btn-stop"),
    btnSave:      $("#btn-save"),

    logArea:      $("#log-area"),
    btnClearLog:  $("#btn-clear-log"),

    toast:        $("#toast"),
  };

  /* ── State ── */
  let maps        = [];
  let loopEnabled = true;
  let maxLoops    = 0;
  let selectedId  = null;
  let pollTimer   = null;

  /* ── Helpers ── */
  const uid = () => "map_" + Date.now() + "_" + Math.random().toString(36).slice(2, 6);
  const fid = () => "f"   + Date.now() + "_" + Math.random().toString(36).slice(2, 6);

  function escapeHTML(s) {
    const el = document.createElement("span");
    el.textContent = s;
    return el.innerHTML;
  }

  function escapeAttr(s) {
    return (s || "").replace(/&/g, "&amp;").replace(/"/g, "&quot;")
      .replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  /* ── Toast ── */
  let toastTimer = null;
  function toast(msg, cls) {
    dom.toast.textContent = msg;
    dom.toast.className = "toast show " + (cls || "");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => dom.toast.classList.remove("show"), 2500);
  }

  /* ── Log ── */
  function log(msg, cls) {
    const time = new Date().toLocaleTimeString("zh-CN", { hour12: false });
    const div = document.createElement("div");
    div.className = "log-line " + (cls || "");
    div.textContent = "[" + time + "] " + msg;
    dom.logArea.appendChild(div);
    dom.logArea.scrollTop = dom.logArea.scrollHeight;
    if (dom.logArea.children.length > 300) {
      dom.logArea.removeChild(dom.logArea.firstChild);
    }
  }

  /* ── API ── */
  async function api(method, path, body) {
    const opts = { method, headers: { "Content-Type": "application/json" } };
    if (body !== undefined) opts.body = JSON.stringify(body);
    const res = await fetch(API + path, opts);
    if (!res.ok) {
      let msg;
      try { msg = (await res.json()).error || res.statusText; } catch (_) { msg = res.statusText; }
      throw new Error(msg || (method + " " + path + " 失败 (" + res.status + ")"));
    }
    return res.json();
  }

  /* ═══════════════════════════════════════
     Load / Save
     ═══════════════════════════════════════ */
  async function loadConfig() {
    try {
      const data = await api("GET", "/api/nodes");
      maps        = data.maps || [];
      loopEnabled = data.loop_enabled !== false;
      maxLoops    = data.max_loops ?? 0;

      dom.toggleLoop.checked = loopEnabled;
      dom.maxLoops.value = maxLoops;

      renderMapList();
      if (selectedId && maps.some(m => m.id === selectedId)) {
        renderFeatures();
      } else {
        selectedId = null;
        clearEditor();
      }
      log("配置已加载");
    } catch (e) {
      log("加载配置失败: " + e.message, "error");
      toast("无法加载配置", "error");
    }
  }

  async function saveConfig() {
    try {
      await api("POST", "/api/nodes", {
        maps: maps,
        loop_enabled: loopEnabled,
        max_loops: maxLoops
      });
      toast("配置已保存", "success");
      log("配置已保存");
    } catch (e) {
      toast("保存失败: " + e.message, "error");
      log("保存失败: " + e.message, "error");
    }
  }

  /* ═══════════════════════════════════════
     Map List
     ═══════════════════════════════════════ */
  function renderMapList() {
    dom.mapCount.textContent = maps.length;
    if (maps.length === 0) {
      dom.mapList.innerHTML = '<li class="map-item empty">暂无地图，点击上方按钮添加</li>';
      return;
    }

    dom.mapList.innerHTML = maps.map(m => {
      const featCount = (m.features || []).length;
      const active = m.id === selectedId ? " active" : "";
      return (
        '<li class="map-item' + active + '" data-id="' + m.id + '">' +
        '  <input type="checkbox" class="map-item-check"' +
        '    ' + (m.enabled !== false ? "checked" : "") +
        '    data-action="toggle" data-id="' + m.id + '" title="启用/禁用">' +
        '  <span class="map-item-label">' + escapeHTML(m.name || "未命名") + '</span>' +
        '  <span class="map-item-badge">' + featCount + ' 个特征</span>' +
        '  <button class="map-item-del" data-action="delete" data-id="' + m.id + '" title="删除地图">&#10005;</button>' +
        '</li>'
      );
    }).join("");

    // Click to select
    dom.mapList.querySelectorAll(".map-item").forEach(li => {
      li.addEventListener("click", (e) => {
        if (e.target.closest("[data-action]")) return;
        selectMap(li.dataset.id);
      });
    });

    // Toggle enabled
    dom.mapList.querySelectorAll("[data-action='toggle']").forEach(cb => {
      cb.addEventListener("change", (e) => {
        e.stopPropagation();
        const m = maps.find(m => m.id === cb.dataset.id);
        if (m) {
          m.enabled = cb.checked;
          log('地图 "' + m.name + '" ' + (cb.checked ? "已启用" : "已禁用"));
        }
      });
    });

    // Delete
    dom.mapList.querySelectorAll("[data-action='delete']").forEach(btn => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        deleteMap(btn.dataset.id);
      });
    });
  }

  /* ═══════════════════════════════════════
     Map Ops
     ═══════════════════════════════════════ */
  function addMap() {
    const m = {
      id: uid(),
      name: "新地图 " + (maps.length + 1),
      enabled: true,
      features: []
    };
    maps.push(m);
    selectedId = m.id;
    renderMapList();
    renderFeatures();
    log('已添加地图: ' + m.name);
  }

  function selectMap(id) {
    selectedId = id;
    renderMapList();
    renderFeatures();
  }

  function getSelectedMap() {
    return maps.find(m => m.id === selectedId) || null;
  }

  function deleteMap(id) {
    const m = maps.find(m => m.id === id);
    if (!m) return;
    if (!confirm('确定删除地图 "' + m.name + '" 及其所有特征？')) return;
    maps = maps.filter(m => m.id !== id);
    if (selectedId === id) {
      selectedId = null;
      clearEditor();
    }
    renderMapList();
    log('已删除地图: ' + m.name);
  }

  /* ═══════════════════════════════════════
     Feature Rendering
     ═══════════════════════════════════════ */
  function clearEditor() {
    dom.editorTitle.textContent = "特征编辑 — 请选择一个地图";
    dom.mapNameRow.style.display = "none";
    dom.btnDelMap.style.display = "none";
    dom.btnAddFeatWrap.style.display = "none";
    dom.featuresGrid.innerHTML =
      '<div class="features-empty">' +
      '  <div class="features-empty-icon">&#x1F4CB;</div>' +
      '  <div class="features-empty-text">选择左侧地图查看特征</div>' +
      '</div>';
  }

  function detectTypeIcon(t) {
    if (t === "image") return "&#x1F5BC;";
    if (t === "key")   return "&#x2328;";
    return "&#x1F4DD;";
  }
  function detectTypeLabel(t) {
    if (t === "image") return "图像";
    if (t === "key")   return "按键";
    return "文本";
  }

  function renderFeatures() {
    const map = getSelectedMap();
    if (!map) { clearEditor(); return; }

    dom.editorTitle.textContent = "特征编辑 — " + map.name;
    dom.mapNameRow.style.display = "";
    dom.mapNameInput.value = map.name;
    dom.btnDelMap.style.display = "";
    dom.btnAddFeatWrap.style.display = "";

    const feats = map.features || [];
    if (feats.length === 0) {
      dom.featuresGrid.innerHTML =
        '<div class="features-empty">' +
        '  <div class="features-empty-icon">&#x1F50D;</div>' +
        '  <div class="features-empty-text">暂无特征，点击下方按钮新增</div>' +
        '</div>';
      return;
    }

    dom.featuresGrid.innerHTML = feats.map((f, idx) => {
      const tc = "type-" + (f.detect_type || "text");
      const icon = detectTypeIcon(f.detect_type);
      const label = detectTypeLabel(f.detect_type);
      return (
        '<div class="feature-card" data-fid="' + f.id + '">' +
        '  <div class="feature-card-header ' + tc + '">' +
        '    <span class="feature-type-icon ' + tc + '">' + icon + '</span>' +
        '    <span class="feature-type-label">' + label + '</span>' +
        '    <input type="checkbox" ' + (f.enabled !== false ? "checked" : "") +
        '      data-action="toggle-feat" data-id="' + f.id + '" title="启用/禁用">' +
        '    <button class="feature-card-del" data-action="delete-feat" data-id="' + f.id + '" title="删除特征">&#10005;</button>' +
        '  </div>' +
        '  <div class="feature-card-body">' +
        '    <div class="feature-card-row">' +
        '      <label>检测值</label>' +
        '      <input type="text" value="' + escapeAttr(f.detect_value) + '"' +
        '        data-action="change-value" data-id="' + f.id + '" placeholder="输入检测值">' +
        '    </div>' +
        '    <div class="feature-card-row">' +
        '      <label>匹配 →</label>' +
        '      <select data-action="change-match" data-id="' + f.id + '">' +
        '        <option value="continue"' + (f.on_match === "continue" ? " selected" : "") + '>继续</option>' +
        '        <option value="restart"'  + (f.on_match === "restart"  ? " selected" : "") + '>重开</option>' +
        '      </select>' +
        '      <label>不匹配 →</label>' +
        '      <select data-action="change-mismatch" data-id="' + f.id + '">' +
        '        <option value="continue"' + (f.on_mismatch === "continue" ? " selected" : "") + '>继续</option>' +
        '        <option value="restart"'  + (f.on_mismatch === "restart"  ? " selected" : "") + '>重开</option>' +
        '      </select>' +
        '    </div>' +
        '    <div class="feature-card-row">' +
        '      <label>类型</label>' +
        '      <select data-action="change-type" data-id="' + f.id + '">' +
        '        <option value="text"'  + (f.detect_type === "text"  ? " selected" : "") + '>文本</option>' +
        '        <option value="image"' + (f.detect_type === "image" ? " selected" : "") + '>图像</option>' +
        '        <option value="key"'   + (f.detect_type === "key"   ? " selected" : "") + '>按键</option>' +
        '      </select>' +
        '    </div>' +
        '  </div>' +
        '</div>'
      );
    }).join("");

    bindFeatureEvents(map);
  }

  function findFeat(map, id) {
    return (map.features || []).find(f => f.id === id);
  }

  function bindFeatureEvents(map) {
    dom.featuresGrid.querySelectorAll("[data-action='toggle-feat']").forEach(cb => {
      cb.addEventListener("change", () => {
        const f = findFeat(map, cb.dataset.id);
        if (f) f.enabled = cb.checked;
      });
    });

    dom.featuresGrid.querySelectorAll("[data-action='change-value']").forEach(inp => {
      inp.addEventListener("input", () => {
        const f = findFeat(map, inp.dataset.id);
        if (f) f.detect_value = inp.value;
      });
    });

    dom.featuresGrid.querySelectorAll("[data-action='change-match']").forEach(sel => {
      sel.addEventListener("change", () => {
        const f = findFeat(map, sel.dataset.id);
        if (f) f.on_match = sel.value;
      });
    });

    dom.featuresGrid.querySelectorAll("[data-action='change-mismatch']").forEach(sel => {
      sel.addEventListener("change", () => {
        const f = findFeat(map, sel.dataset.id);
        if (f) f.on_mismatch = sel.value;
      });
    });

    dom.featuresGrid.querySelectorAll("[data-action='change-type']").forEach(sel => {
      sel.addEventListener("change", () => {
        const f = findFeat(map, sel.dataset.id);
        if (f) {
          f.detect_type = sel.value;
          renderFeatures(); // re-render for color change
        }
      });
    });

    dom.featuresGrid.querySelectorAll("[data-action='delete-feat']").forEach(btn => {
      btn.addEventListener("click", () => {
        const f = findFeat(map, btn.dataset.id);
        if (f && confirm('确定删除特征 "' + (f.detect_value || "(空)") + '"？')) {
          map.features = map.features.filter(ff => ff.id !== f.id);
          renderFeatures();
          renderMapList();
          log('已删除特征: ' + (f.detect_value || "(空)"));
        }
      });
    });
  }

  function addFeature() {
    const map = getSelectedMap();
    if (!map) { toast("请先选择一个地图", "warn"); return; }
    if (!map.features) map.features = [];
    map.features.push({
      id: fid(),
      detect_type: "text",
      detect_value: "",
      on_match: "continue",
      on_mismatch: "continue",
      enabled: true
    });
    renderFeatures();
    renderMapList();
    log('已添加特征到 "' + map.name + '"');
  }

  /* ═══════════════════════════════════════
     Event Bindings
     ═══════════════════════════════════════ */
  dom.mapNameInput.addEventListener("input", () => {
    const map = getSelectedMap();
    if (map) {
      map.name = dom.mapNameInput.value || "未命名";
      dom.editorTitle.textContent = "特征编辑 — " + map.name;
      renderMapList();
    }
  });

  dom.toggleLoop.addEventListener("change", () => {
    loopEnabled = dom.toggleLoop.checked;
  });

  dom.maxLoops.addEventListener("input", () => {
    maxLoops = parseInt(dom.maxLoops.value, 10) || 0;
  });

  dom.btnSave.addEventListener("click", () => saveConfig());
  dom.btnAddMap.addEventListener("click", () => addMap());
  dom.btnAddFeature.addEventListener("click", () => addFeature());
  dom.btnDelMap.addEventListener("click", () => {
    if (selectedId) deleteMap(selectedId);
  });
  dom.btnClearLog.addEventListener("click", () => {
    dom.logArea.innerHTML = "";
    log("日志已清空");
  });

  /* ═══════════════════════════════════════
     Run / Stop
     ═══════════════════════════════════════ */
  async function doRun() {
    try {
      await saveConfig();
      const res = await api("POST", "/api/nodes/run");
      log("▶ 启动节点流程" + (res.message ? ": " + res.message : ""));
      startPolling();
    } catch (e) {
      toast("启动失败: " + e.message, "error");
      log("启动失败: " + e.message, "error");
    }
  }

  async function doStop() {
    try {
      const res = await api("POST", "/api/nodes/stop");
      toast(res.message || "已停止");
      log("■ 已停止");
      stopPolling();
    } catch (e) {
      toast("停止失败: " + e.message, "error");
    }
  }

  dom.btnRun.addEventListener("click", doRun);
  dom.btnStop.addEventListener("click", doStop);

  /* ═══════════════════════════════════════
     Status Polling
     ═══════════════════════════════════════ */
  function startPolling() {
    if (pollTimer) return;
    pollStatus();
    pollTimer = setInterval(pollStatus, POLL);
  }

  function stopPolling() {
    if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
    dom.statusDot.classList.remove("running", "error");
    dom.statusDot.classList.add("idle");
    dom.statusText.textContent = "待命";
  }

  async function pollStatus() {
    try {
      const s = await api("GET", "/api/status");
      dom.statusDot.classList.remove("idle", "running", "error");

      if (s.status === "运行中" || s.running) {
        dom.statusDot.classList.add("running");
        if (s.round !== undefined) {
          dom.statusText.textContent = "运行中 (第 " + s.round + " 轮)";
        } else {
          dom.statusText.textContent = "运行中";
        }

        if (s.log_lines && s.log_lines.length) {
          s.log_lines.forEach(l => log(l.line || l, l.level || ""));
        }
        if (s.message && !s.log_lines) {
          log(s.message);
        }
      } else if (s.error) {
        dom.statusDot.classList.add("error");
        dom.statusText.textContent = "错误: " + s.error;
      } else if (s.status === "已停止" || s.status === "stopped") {
        dom.statusDot.classList.add("idle");
        dom.statusText.textContent = "待命";
        stopPolling();
      } else {
        dom.statusDot.classList.add("idle");
        dom.statusText.textContent = s.status || "待命";
        stopPolling();
      }
    } catch (_) {
      dom.statusDot.classList.remove("running");
      dom.statusDot.classList.add("error");
      dom.statusText.textContent = "无法连接";
      stopPolling();
    }
  }

  /* ═══════════════════════════════════════
     Tab Switching
     ═══════════════════════════════════════ */
  dom.tabBasic.addEventListener("click", () => {
    try { stopPolling(); } catch (_) {}
    window.location.href = "../page-basic/index.html";
  });

  /* ═══════════════════════════════════════
     Init
     ═══════════════════════════════════════ */
  async function init() {
    log("循环节点页已加载");
    await loadConfig();
    log("就绪 — API: " + API + "  |  地图数: " + maps.length);
  }

  init();
})();
