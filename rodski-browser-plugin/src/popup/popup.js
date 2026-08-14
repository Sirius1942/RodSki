/**
 * Popup 逻辑 - 自动截图开关 + 本地保存（不依赖 rodski-web）
 */

function $(id) { return document.getElementById(id); }

function showToast(msg, type = 'success', duration = 2500) {
  const el = $('toast');
  el.textContent = msg;
  el.className = type;
  el.style.display = 'block';
  clearTimeout(el.__timer);
  el.__timer = setTimeout(() => { el.style.display = 'none'; }, duration);
}

function sendBg(type, payload = {}) {
  return chrome.runtime.sendMessage({ type, payload });
}

// ---- 状态 ----
let state = {
  recording: false,
  pickerActive: false,
  stepCount: 0,
  screenshotCount: 0,
  webOnline: false,
  currentEnv: null,
  autoScreenshot: false,
};

// ---- 初始化 ----
async function init() {
  await refreshStatus();
  await loadEnvs();
  await loadAutoShotToggle();
  setupListeners();
}

async function refreshStatus() {
  try {
    const status = await sendBg('GET_STATUS');
    if (!status) return;
    state.webOnline = status.webOnline;
    state.recording = status.recording;
    state.stepCount = status.stepCount || 0;
    state.screenshotCount = status.screenshotCount || 0;
    state.currentEnv = status.currentEnv;
    state.autoScreenshot = status.autoScreenshot || false;

    // Web 状态
    const dot = $('webStatusDot');
    const txt = $('webStatusText');
    dot.className = status.webOnline ? 'status-dot online' : 'status-dot offline';
    txt.textContent = status.webOnline ? 'web 在线' : 'web 离线';

    updateRecUI();
  } catch (e) {}
}

// ---- 自动截图开关 ----
async function loadAutoShotToggle() {
  const result = await sendBg('GET_AUTO_SCREENSHOT');
  state.autoScreenshot = result?.autoScreenshot || false;
  $('autoShotToggle').checked = state.autoScreenshot;
}

// ---- 环境 ----
async function loadEnvs() {
  try {
    const result = await sendBg('GET_ENVS');
    if (!result?.ok) return;
    const select = $('envSelect');
    select.innerHTML = '<option value="">-- 选择 --</option>';
    (result.envs || []).forEach(env => {
      const opt = document.createElement('option');
      opt.value = env; opt.textContent = env;
      if (env === (result.currentEnv || state.currentEnv)) opt.selected = true;
      select.appendChild(opt);
    });
    if (result.currentEnv) { select.value = result.currentEnv; state.currentEnv = result.currentEnv; }
  } catch (e) {}
}

// ---- 录制 UI ----
function updateRecUI() {
  const btn = $('btnRecordToggle');
  const dot = $('recDot');
  const txt = $('recBtnText');
  const badge = $('recBadge');
  const shotBadge = $('shotBadge');
  const screenshotBtn = $('btnScreenshot');
  const saveBtn = $('btnSave');

  if (state.recording) {
    btn.className = 'btn active';
    dot.className = 'rec-dot pulsing';
    txt.textContent = '停止录制';
    badge.className = 'btn-badge live';
    screenshotBtn.disabled = false;
  } else {
    btn.className = 'btn';
    dot.className = 'rec-dot';
    txt.textContent = '开始录制';
    badge.className = 'btn-badge';
    screenshotBtn.disabled = true;
  }

  badge.textContent = `${state.stepCount} 步`;
  shotBadge.textContent = `${state.screenshotCount} 张`;
  saveBtn.disabled = state.stepCount === 0;
}

function showSaveResult(dir, stepCount, screenshotCount) {
  const el = $('saveResult');
  el.className = 'save-result visible';
  $('saveDir').textContent = dir;
  $('saveStats').textContent = `${stepCount} 步  ·  ${screenshotCount} 张截图  ·  manifest.json + case_draft.xml + model_draft.xml`;
}

// ---- 截图缩略图（从内存 state 渲染，实时更新）----
let _thumbDataUrls = [];

function updateThumbs(dataUrls) {
  _thumbDataUrls = dataUrls || [];
  const grid = $('screenshotsGrid');
  grid.innerHTML = '';
  _thumbDataUrls.slice(-8).forEach((item, i) => {
    if (!item?.dataUrl) return;
    const thumb = document.createElement('div');
    thumb.className = 'screenshot-thumb';
    thumb.title = item.label || `步骤 ${item.seq}`;
    thumb.innerHTML = `<img src="${item.dataUrl}"><div class="thumb-seq">${item.seq || i + 1}</div>`;
    thumb.addEventListener('click', () => chrome.tabs.create({ url: item.dataUrl }));
    grid.appendChild(thumb);
  });
}

// ---- 轮询（录制中更新步骤数和截图缩略图）----
let poller = null;
function startPoller() {
  clearInterval(poller);
  poller = setInterval(async () => {
    if (!state.recording) { clearInterval(poller); return; }
    const status = await sendBg('GET_STATUS');
    if (!status) return;
    state.stepCount = status.stepCount || 0;
    state.screenshotCount = status.screenshotCount || 0;
    $('recBadge').textContent = `${state.stepCount} 步`;
    $('shotBadge').textContent = `${state.screenshotCount} 张`;
    // 刷新截图缩略图
    const stored = await chrome.storage.local.get(['rodski_screenshots']);
    const shots = stored['rodski_screenshots'] || [];
    updateThumbs(shots);
  }, 800);
}

// ---- 事件绑定 ----
function setupListeners() {
  // 自动截图开关
  $('autoShotToggle').addEventListener('change', async (e) => {
    const enabled = e.target.checked;
    await sendBg('SET_AUTO_SCREENSHOT', { enabled });
    state.autoScreenshot = enabled;
    showToast(enabled ? '📷 每步自动截图已开启' : '自动截图已关闭', 'info');
  });

  // 录制开关
  $('btnRecordToggle').addEventListener('click', async () => {
    if (state.recording) {
      // 停止
      await sendBg('STOP_RECORDING_CMD');
      state.recording = false;
      showToast('录制已停止，正在保存...', 'saving', 4000);
      updateRecUI();
      clearInterval(poller);

      // 等待 background 完成保存
      setTimeout(async () => {
        const exp = await sendBg('GET_LAST_EXPORT');
        if (exp?.ok) {
          state.stepCount = exp.stepCount;
          $('btnSave').disabled = false;
          updateRecUI();
        }
      }, 1500);
    } else {
      // 开始
      const result = await sendBg('START_RECORDING');
      if (result?.ok) {
        state.recording = true;
        state.stepCount = 0;
        state.screenshotCount = 0;
        state.autoScreenshot = result.autoScreenshot;
        $('saveResult').className = 'save-result';
        updateRecUI();
        showToast(
          state.autoScreenshot ? '录制已开始（每步自动截图）' : '录制已开始',
          'info'
        );
        startPoller();
        window.close(); // 关闭 popup，让用户去操作页面
      } else {
        showToast('启动录制失败', 'error');
      }
    }
  });

  // 手动截图
  $('btnScreenshot').addEventListener('click', async () => {
    const result = await sendBg('CAPTURE_SCREENSHOT', {
      label: 'manual',
      seq: state.stepCount,
    });
    if (result?.ok) {
      state.screenshotCount++;
      $('shotBadge').textContent = `${state.screenshotCount} 张`;
      showToast('📷 截图已保存', 'success');
      const stored = await chrome.storage.local.get(['rodski_screenshots']);
      updateThumbs(stored['rodski_screenshots'] || []);
    } else {
      showToast('截图失败', 'error');
    }
  });

  // 保存到本地
  $('btnSave').addEventListener('click', async () => {
    showToast('💾 正在保存...', 'saving', 6000);
    $('btnSave').disabled = true;
    const result = await sendBg('EXPORT_NOW');
    $('btnSave').disabled = false;
    if (result?.ok) {
      showSaveResult(result.dir, result.stepCount, result.screenshotCount);
      showToast(`✅ 已保存：${result.stepCount} 步，${result.screenshotCount} 张截图`, 'success', 4000);
    } else {
      showToast(result?.error || '保存失败', 'error');
    }
  });

  // 定位器 Picker
  $('btnPickerToggle').addEventListener('click', async () => {
    if (state.pickerActive) {
      await sendBg('DEACTIVATE_PICKER');
      state.pickerActive = false;
      $('btnPickerToggle').className = 'btn';
      $('pickerBtnText').textContent = '启动定位器 Picker';
    } else {
      await sendBg('ACTIVATE_PICKER');
      state.pickerActive = true;
      $('btnPickerToggle').className = 'btn success';
      $('pickerBtnText').textContent = '停用 Picker（Esc 退出）';
      showToast('Picker 已启动，悬停元素查看定位器 (Alt+C 复制)', 'info', 3000);
      window.close();
    }
  });

  // 页面快照
  $('btnPageSnapshot').addEventListener('click', async () => {
    const result = await sendBg('GET_PAGE_SNAPSHOT');
    if (result?.ok && result.data) {
      const content = JSON.stringify(result.data, null, 2);
      try {
        await navigator.clipboard.writeText(content);
        showToast(`✅ 已复制（${result.data.interactive_elements?.length || 0} 个元素）`, 'success');
      } catch (e) {
        showToast('复制失败', 'error');
      }
    } else {
      showToast('获取快照失败', 'error');
    }
  });

  // 失败诊断
  $('btnFetchFailure').addEventListener('click', async () => {
    if (!state.webOnline) {
      showToast('rodski-web 离线', 'error'); return;
    }
    const result = await sendBg('FETCH_LAST_FAILURE');
    if (result?.ok) {
      showToast('已加载失败诊断，查看页面高亮', 'info', 3000);
      window.close();
    } else {
      showToast('暂无失败记录', 'info');
    }
  });

  // 清除高亮
  $('btnClearHighlights').addEventListener('click', async () => {
    await sendBg('CLEAR_HIGHLIGHTS');
    showToast('已清除高亮', 'info');
  });

  // 环境切换
  $('btnEnvSwitch').addEventListener('click', async () => {
    const env = $('envSelect').value;
    if (!env) { showToast('请先选择环境', 'error'); return; }
    const btn = $('btnEnvSwitch');
    btn.disabled = true; btn.textContent = '...';
    const result = await sendBg('SWITCH_ENV', { env });
    btn.disabled = false; btn.textContent = '切换';
    if (result?.ok) {
      state.currentEnv = env;
      showToast(`✅ 已切换到 ${env}`, 'success');
    } else {
      showToast('切换失败', 'error');
    }
  });
}

// ---- 启动 ----
document.addEventListener('DOMContentLoaded', () => {
  init().catch(console.error);
});
