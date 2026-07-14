/**
 * ═══════════════════════════════════════════
 *  全能脚本 — 基础操作页 前端逻辑
 * ═══════════════════════════════════════════
 */
(() => {
  "use strict";

  const API  = "http://127.0.0.1:8765";
  const POLL = 2000; // 状态轮询间隔 ms

  /* ── DOM refs ── */
  const $  = s => document.querySelector(s);
  const $$ = s => document.querySelectorAll(s);

  const dom = {
    statusDot:    $(".status-dot"),
    statusText:   $(".status-text"),
    tabBasic:     $("#tab-basic"),
    tabLoop:      $("#tab-loop"),
    pageBasic:    $("#page-basic"),
    pageLoop:     $("#page-loop"),
    presetList:   $("#preset-list"),
    presetSelect: $("#preset-select"),
    btnLoad:      $("#btn-load"),
    btnSave:      $("#btn-save"),
    btnDelete:    $("#btn-delete"),
    maxRuns:      $("#max-runs"),
    interval:     $("#round-interval"),
    btnRun:       $("#btn-run"),
    btnStop:      $("#btn-stop"),
    tbody:        $("#step-tbody"),
    btnAdd:       $("#btn-add"),
    btnDelStep:   $("#btn-del-step"),
    btnUp:        $("#btn-up"),
    btnDown:      $("#btn-down"),
    logArea:      $("#log-area"),
    toast:        $("#toast"),
    modal:        $("#modal"),
    modalTitle:   $("#modal-title"),
    modalBody:    $("#modal-body"),
    modalConfirm: $("#modal-confirm"),
    modalCancel:  $("#modal-cancel"),
  };

  /* ── State ── */
  let presets    = [];
  let curPreset  = null;
  let curName    = "";
  let editIdx    = -1;
  let pollTimer  = null;

  /* ── Toast ── */
  let toastTimer = null;
  function toast(msg) {
    dom.toast.textContent = msg;
    dom.toast.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => dom.toast.classList.remove("show"), 2500);
  }

  /* ── Log ── */
  function log(msg, cls = "") {
    const time = new Date().toLocaleTimeString("zh-CN", { hour12: false });
    const div = document.createElement("div");
    div.className = `log-line ${cls}`;
    div.textContent = `[${time}] ${msg}`;
    dom.logArea.appendChild(div);
    dom.logArea.scrollTop = dom.logArea.scrollHeight;
    if (dom.logArea.children.length > 200) {
      dom.logArea.removeChild(dom.logArea.firstChild);
    }
  }

  /* ── Modal ── */
  let modalResolve = null;
  function openModal(title, bodyHTML) {
    return new Promise(resolve => {
      dom.modalTitle.textContent = title;
      dom.modalBody.innerHTML = bodyHTML;
      dom.modal.classList.add("open");
      modalResolve = resolve;
    });
  }
  function closeModal(confirmed, getValue = null) {
    dom.modal.classList.remove("open");
    if (modalResolve) {
      modalResolve(confirmed ? (getValue ? getValue() : true) : null);
      modalResolve = null;
    }
  }
  dom.modalConfirm.onclick = () => closeModal(true);
  dom.modalCancel.onclick  = () => closeModal(false);
  dom.modal.addEventListener("click", e => {
    if (e.target === dom.modal) closeModal(false);
  });
  /* ═══════════════════════════════════════
     API helpers
     ═══════════════════════════════════════ */
  async function api(method, path, body = null) {
    const opts = { method, headers: { "Content-Type": "application/json" } };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(API + path, opts);
    if (!res.ok) {
      const err = await res.text();
      throw new Error(err || `${method} ${path} 失败 (${res.status})`);
    }
    return res.json();
  }

  /* ═══════════════════════════════════════
     Preset Management
     ═══════════════════════════════════════ */
  async function loadPresetList() {
    try {
      presets = await api("GET", "/api/presets");
    } catch (e) {
      log(`加载预设列表失败: ${e.message}`, "error");
      presets = [];
    }
    renderPresetList();
    renderPresetSelect();
  }

  function renderPresetList() {
    dom.presetList.innerHTML = "";
    presets.forEach(p => {
      const li = document.createElement("li");
      li.className = "preset-item";
      if (curName === p.name) li.classList.add("active");
      li.textContent = p.name;
      li.addEventListener("click", () => selectPreset(p.name));
      dom.presetList.appendChild(li);
    });
  }

  function renderPresetSelect() {
    dom.presetSelect.innerHTML = "";
    presets.forEach(p => {
      const opt = document.createElement("option");
      opt.value = p.name;
      opt.textContent = p.name;
      dom.presetSelect.appendChild(opt);
    });
    dom.presetSelect.value = curName || "";
  }

  async function selectPreset(name) {
    try {
      curPreset = await api("GET", `/api/presets/${encodeURIComponent(name)}`);
      curName = name;
      dom.maxRuns.value = curPreset.max_runs ?? 0;
      dom.interval.value = curPreset.round_interval ?? 0;
      renderPresetList();
      renderPresetSelect();
      renderSteps();
      log(`已加载预设: ${name}`);
    } catch (e) {
      toast(`加载预设失败: ${e.message}`);
    }
  }

  async function savePreset() {
    if (!curPreset) {
      curPreset = newPreset("默认预设");
    }
    curPreset.max_runs = parseInt(dom.maxRuns.value) || 0;
    curPreset.round_interval = parseInt(dom.interval.value) || 0;
    curPreset.name = curName || "默认预设";
    try {
      await api("POST", "/api/presets", curPreset);
      toast("已保存");
      log(`已保存预设: ${curPreset.name}`);
      await loadPresetList();
    } catch (e) {
      toast(`保存失败: ${e.message}`);
    }
  }

  async function deletePreset() {
    if (!curName) { toast("请先选择一个预设"); return; }
    if (!confirm(`确认删除预设 "${curName}" ?`)) return;
    try {
      await api("DELETE", `/api/presets/${encodeURIComponent(curName)}`);
      curPreset = null;
      curName = "";
      dom.maxRuns.value = 0;
      dom.interval.value = 0;
      toast("已删除");
      log(`已删除预设: ${curName}`);
      await loadPresetList();
      renderSteps();
    } catch (e) {
      toast(`删除失败: ${e.message}`);
    }
  }

  function newPreset(name) {
    return {
      name,
      game: "二重螺旋",
      steps: [],
      max_runs: 0,
      round_interval: 0,
      chain: true,
    };
  }

  dom.presetSelect.addEventListener("change", () => {
    const v = dom.presetSelect.value;
    if (v) selectPreset(v);
  });
  dom.btnLoad.addEventListener("click", () => {
    const v = dom.presetSelect.value;
    if (v) selectPreset(v);
  });
  dom.btnSave.addEventListener("click", savePreset);
  dom.btnDelete.addEventListener("click", deletePreset);
  /* ═══════════════════════════════════════
     Steps Table
     ═══════════════════════════════════════ */
  const COND_MAP = {
    none: "直接执行", text: "文字识别", image: "模板识别",
  };
  const ACT_MAP = {
    press_key: "按下按键", click_text: "点击识别文字",
    click_image: "点击识别图片", click_near_image: "点击图片附近坐标",
    mouse_swipe: "鼠标滑动",
  };
  const ACT_CN = {
    press_key: "按键", click_text: "点文字", click_image: "点图",
    click_near_image: "图偏移", mouse_swipe: "滑动",
  };

  function fmtCond(ct, cv) {
    if (ct === "none" || !cv) return "直接执行";
    if (ct === "image") return `图\u00AB${cv}\u00BB`;
    return `文\u00AB${cv}\u00BB`;
  }
  function fmtAct(at, av) {
    const prefix = ACT_CN[at] || at;
    return `${prefix}\u00AB${av}\u00BB`;
  }

  function renderSteps() {
    dom.tbody.innerHTML = "";
    const steps = curPreset?.steps || [];
    if (!steps.length) {
      dom.tbody.innerHTML = `<tr><td colspan="5" class="empty-row">暂无步骤，点击"添加"创建</td></tr>`;
      return;
    }
    steps.forEach((s, i) => {
      const tr = document.createElement("tr");
      tr.className = "step-row";
      const ct = s.condition_type || "none";
      const cv = s.condition_value || "";
      const at = s.action_type || "press_key";
      const av = s.action_value || "";
      tr.innerHTML = `
        <td>${s.count ?? 0}</td>
        <td>${fmtCond(ct, cv)}</td>
        <td>${fmtAct(at, av)}</td>
        <td>${s.duration ?? 0.2}s</td>
        <td>${s.delay ?? 0}s</td>
      `;
      tr.addEventListener("click", () => editStep(i));
      dom.tbody.appendChild(tr);
    });
  }

  /* ═══════════════════════════════════════
     Step Editing (Modal)
     ═══════════════════════════════════════ */
  function newStepData() {
    return {
      condition_type: "none", condition_value: "",
      action_type: "press_key", action_value: "",
      duration: 0.2, delay: 0, count: 0, enabled: true, verify_text: "",
    };
  }

  async function addStep() {
    if (!curPreset) {
      curPreset = newPreset(curName || "默认预设");
    }
    const result = await openStepEditor(newStepData(), "添加步骤");
    if (result) {
      if (!curPreset.steps) curPreset.steps = [];
      curPreset.steps.push(result);
      renderSteps();
      log("已添加步骤");
    }
  }

  async function editStep(idx) {
    if (!curPreset?.steps) return;
    const old = curPreset.steps[idx];
    if (!old) return;
    const result = await openStepEditor({ ...old }, `编辑步骤 ${idx + 1}`);
    if (result) {
      curPreset.steps[idx] = result;
      renderSteps();
      log(`已编辑步骤 ${idx + 1}`);
    }
  }

  async function openStepEditor(data, title) {
    const ct = data.condition_type || "none";
    const cv = data.condition_value || "";
    const at = data.action_type || "press_key";
    const av = data.action_value || "";
    const dur = data.duration ?? 0.2;
    const dly = data.delay ?? 0;
    const cnt = data.count ?? 0;

    const html = `
      <div class="edit-section">
        <label class="edit-label">执行条件</label>
        <div class="radio-row">
          ${["直接执行","文字识别","模板识别"].map(v => `
            <label class="radio-item">
              <input type="radio" name="cond" value="${v}" ${COND_MAP[ct] === v ? "checked" : ""}>
              <span>${v}</span>
            </label>
          `).join("")}
        </div>
        <div class="edit-field" id="cond-detail">
          ${COND_MAP[ct] === "文字识别" ? `
            <label>识别文字:</label>
            <input type="text" id="cond-val" value="${esc(cv)}" placeholder="输入要识别的文字">
          ` : COND_MAP[ct] === "模板识别" ? `
            <label>模板名称:</label>
            <input type="text" id="cond-val" value="${esc(cv)}" placeholder="输入模板名称">
          ` : ""}
        </div>
      </div>
      <div class="edit-section">
        <label class="edit-label">执行命令</label>
        <div class="radio-row" style="flex-wrap:wrap">
          ${["按下按键","点击识别文字","点击识别图片","点击图片附近坐标","鼠标滑动"].map(v => `
            <label class="radio-item">
              <input type="radio" name="act" value="${v}" ${ACT_MAP[at] === v ? "checked" : ""}>
              <span>${v}</span>
            </label>
          `).join("")}
        </div>
        <div class="edit-field" id="act-detail">
          <label>命令参数:</label>
          <input type="text" id="act-val" value="${esc(av)}" placeholder="${ACT_MAP[at] === '按下按键' ? '按键名，如 r / space / w' : '参数值'}">
          ${ACT_MAP[at] === "按下按键" ? '<span class="edit-hint">空格=space</span>' : ""}
        </div>
      </div>
      <div class="edit-row">
        <div class="edit-field">
          <label>执行次数:</label>
          <input type="number" id="step-count" value="${cnt}" min="0" style="width:80px">
          <span class="edit-hint">0=不限</span>
        </div>
        <div class="edit-field">
          <label>按键时长 (s):</label>
          <input type="number" id="step-dur" value="${dur}" min="0" step="0.1" style="width:80px">
        </div>
        <div class="edit-field">
          <label>延迟 (s):</label>
          <input type="number" id="step-dly" value="${dly}" min="0" step="0.1" style="width:80px">
        </div>
      </div>
    `;

    const confirmed = await openModal(title, html);

    if (confirmed) {
      // Read values from modal form
      const m = document.getElementById.bind(document);
      const condCN = m("cond-val")?.closest("#cond-detail")?.parentElement
        ?.querySelector('input[name="cond"]:checked')?.value || "直接执行";
      const condKey = { "直接执行":"none","文字识别":"text","模板识别":"image" }[condCN] || "none";
      const condVal = m("cond-val")?.value || "";

      const actCN = m("act-val")?.closest("#act-detail")?.parentElement
        ?.querySelector('input[name="act"]:checked')?.value || "按下按键";
      const actKey = {
        "按下按键":"press_key","点击识别文字":"click_text",
        "点击识别图片":"click_image","点击图片附近坐标":"click_near_image",
        "鼠标滑动":"mouse_swipe"
      }[actCN] || "press_key";
      const actVal = m("act-val")?.value || "";

      const stepCount = parseInt(m("step-count")?.value) || 0;
      const stepDur = parseFloat(m("step-dur")?.value) || 0.2;
      const stepDly = parseFloat(m("step-dly")?.value) || 0;

      return {
        condition_type: condKey, condition_value: condVal,
        action_type: actKey, action_value: actVal,
        duration: stepDur, delay: stepDly, count: stepCount,
        enabled: true, verify_text: "",
      };
    }
    return null;
  }

  // Bind radio changes in modal after render (delegation)
  document.addEventListener("change", e => {
    if (!dom.modal.classList.contains("open")) return;

    // Condition radio change
    if (e.target.name === "cond") {
      const v = e.target.value;
      const detail = document.getElementById("cond-detail");
      if (!detail) return;
      if (v === "文字识别") {
        detail.innerHTML = `<label>识别文字:</label><input type="text" id="cond-val" placeholder="输入要识别的文字">`;
      } else if (v === "模板识别") {
        detail.innerHTML = `<label>模板名称:</label><input type="text" id="cond-val" placeholder="输入模板名称">`;
      } else {
        detail.innerHTML = "";
      }
    }

    // Action radio change
    if (e.target.name === "act") {
      const v = e.target.value;
      const detail = document.getElementById("act-detail");
      if (!detail) return;
      if (v === "按下按键") {
        detail.innerHTML = `<label>命令参数:</label><input type="text" id="act-val" placeholder="按键名，如 r / space / w"><span class="edit-hint">空格=space</span>`;
      } else {
        detail.innerHTML = `<label>命令参数:</label><input type="text" id="act-val" placeholder="参数值">`;
      }
    }
  });

  function esc(s) {
    return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
  }

  function deleteStep() {
    if (!curPreset?.steps?.length) { toast("没有可删除的步骤"); return; }
    // Use a simple prompt-like approach via the last selected or the first
    const idx = editIdx >= 0 && editIdx < curPreset.steps.length ? editIdx : 0;
    if (!confirm(`删除步骤 ${idx + 1}?`)) return;
    curPreset.steps.splice(idx, 1);
    if (editIdx >= curPreset.steps.length) editIdx = -1;
    renderSteps();
    log(`已删除步骤 ${idx + 1}`);
  }

  function moveStep(dir) {
    if (!curPreset?.steps?.length) { toast("列表为空"); return; }
    const idx = editIdx >= 0 && editIdx < curPreset.steps.length ? editIdx : -1;
    if (idx < 0) { toast("请先点击选中一个步骤"); return; }
    const si = idx + dir;
    if (si < 0 || si >= curPreset.steps.length) return;
    [curPreset.steps[idx], curPreset.steps[si]] = [curPreset.steps[si], curPreset.steps[idx]];
    editIdx = si;
    renderSteps();
    // Highlight moved
    const row = dom.tbody.children[si];
    if (row) row.classList.add("highlight-row");
  }

  // Track clicked row index
  dom.tbody.addEventListener("click", e => {
    const row = e.target.closest("tr");
    if (!row) return;
    const rows = [...dom.tbody.children].filter(r => !r.querySelector(".empty-row"));
    editIdx = rows.indexOf(row);
  });

  dom.btnAdd.addEventListener("click", addStep);
  dom.btnDelStep.addEventListener("click", deleteStep);
  dom.btnUp.addEventListener("click", () => moveStep(-1));
  dom.btnDown.addEventListener("click", () => moveStep(1));
  /* ═══════════════════════════════════════
     Run / Stop
     ═══════════════════════════════════════ */
  async function doRun() {
    if (!curName) { toast("请先选择一个预设"); return; }
    try {
      const res = await api("POST", "/api/run", { preset_name: curName });
      toast(res.message || "已启动");
      log(`▶ 启动运行: ${curName}`);
      startPolling();
    } catch (e) {
      toast(`启动失败: ${e.message}`);
    }
  }

  async function doStop() {
    try {
      const res = await api("POST", "/api/stop");
      toast(res.message || "已停止");
      log("■ 已停止");
    } catch (e) {
      toast(`停止失败: ${e.message}`);
    }
  }

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
      dom.statusText.textContent = s.status || "待命";

      dom.statusDot.classList.remove("idle", "running", "error");
      if (s.status === "运行中") {
        dom.statusDot.classList.add("running");
        const info = [];
        if (s.total) info.push(`共${s.total}步`);
        if (s.step) info.push(`第${s.step}步`);
        if (s.action) info.push(s.action);
        dom.statusText.textContent = info.length ? `运行中 (${info.join(" / ")})` : "运行中";
      } else if (s.error) {
        dom.statusDot.classList.add("error");
        dom.statusText.textContent = `错误: ${s.error}`;
      } else if (s.status === "已停止") {
        dom.statusDot.classList.add("idle");
        stopPolling();
      } else {
        dom.statusDot.classList.add("idle");
        stopPolling();
      }
    } catch (e) {
      // Backend may be down — gracefully degrade
      dom.statusDot.classList.remove("running");
      dom.statusDot.classList.add("error");
      dom.statusText.textContent = "无法连接";
      stopPolling();
    }
  }

  dom.btnRun.addEventListener("click", doRun);
  dom.btnStop.addEventListener("click", doStop);
  /* ═══════════════════════════════════════
     Tab Switching
     ═══════════════════════════════════════ */
  function switchTab(tab) {
    if (tab === "loop") {
      dom.tabBasic.classList.remove("active");
      dom.tabLoop.classList.add("active");
      dom.pageBasic.style.display = "none";
      dom.pageLoop.style.display = "flex";
    } else {
      dom.tabLoop.classList.remove("active");
      dom.tabBasic.classList.add("active");
      dom.pageBasic.style.display = "flex";
      dom.pageLoop.style.display = "none";
    }
  }

  dom.tabBasic.addEventListener("click", () => switchTab("basic"));
  dom.tabLoop.addEventListener("click", () => switchTab("loop"));

  /* ═══════════════════════════════════════
     Init
     ═══════════════════════════════════════ */
  async function init() {
    log("页面已加载，正在连接后端...");
    await loadPresetList();
    if (presets.length > 0) {
      await selectPreset(presets[0].name);
    }
    log("就绪 — API: " + API);
  }

  init();

  // Secondary cancel button in modal footer
  const cancel2 = document.getElementById("modal-cancel2");
  if (cancel2) cancel2.addEventListener("click", () => closeModal(false));

  // Clear log button
  const btnClearLog = document.getElementById("btn-clear-log");
  if (btnClearLog) btnClearLog.addEventListener("click", () => {
    dom.logArea.innerHTML = "";
    log("日志已清空");
  });
})();
