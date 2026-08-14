/**
 * Service Worker - 录制状态管理、截图、本地保存（不依赖 rodski-web）
 *
 * 架构要点（修复"切页面丢动作"和"停止保存报错"两个 bug 后）：
 * - background 是步骤序列（recordingState.steps）的唯一权威来源，content script
 *   只负责捕获原始 DOM 事件并转发，不再自行维护会跨页面失效的本地步骤数组。
 * - 所有录制期间的消息目标锁定 recordingState.tabId（录制开始时的标签页），
 *   不再用 chrome.tabs.query({active, currentWindow}) 动态找“当前标签”，
 *   避免用户切换标签页后指令发错对象。
 * - 通过 chrome.webNavigation 监听整页导航（onCompleted）和 SPA 软导航
 *   （onHistoryStateUpdated），导航发生时：
 *     1) background 自己补一条 navigate 步骤（不依赖新页面的 content script）
 *     2) 向新页面的 content script 发 RESUME_RECORDING，恢复事件监听
 */

const STORAGE_KEY_RECORDING    = 'rodski_recording';
const STORAGE_KEY_ENV          = 'rodski_env';
const STORAGE_KEY_STEPS        = 'rodski_steps';
const STORAGE_KEY_SCREENSHOTS  = 'rodski_screenshots';
const STORAGE_KEY_AUTO_SHOT    = 'rodski_auto_screenshot';

// rodski-web 地址（可选，仅失败诊断用）
const RODSKI_WEB_BASE = 'http://localhost:5002';

// ---- 录制状态（background 为唯一权威来源） ----

let recordingState = {
  active: false,
  tabId: null,
  windowId: null,
  steps: [],
  screenshots: [],   // { label, seq, timestamp, url, title, dataUrl }
  startTime: null,
  autoScreenshot: false,
  stepSeq: 0,
};

function addStep(stepPartial) {
  recordingState.stepSeq += 1;
  const step = { seq: recordingState.stepSeq, timestamp: new Date().toISOString(), ...stepPartial };
  recordingState.steps.push(step);
  return step;
}

async function sendToRecordingTab(message, { retries = 0, delayMs = 300 } = {}) {
  if (!recordingState.tabId) return null;
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      return await chrome.tabs.sendMessage(recordingState.tabId, message);
    } catch (e) {
      if (attempt === retries) {
        console.warn('[RodSki] 发送消息到录制标签页失败:', message.type, e.message);
        return null;
      }
      await new Promise(r => setTimeout(r, delayMs));
    }
  }
  return null;
}

// ---- rodski-web（可选，仅失败诊断用） ----

async function fetchRodskiWeb(path, options = {}) {
  try {
    const res = await fetch(`${RODSKI_WEB_BASE}${path}`, {
      headers: { 'Content-Type': 'application/json', ...options.headers },
      ...options,
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (e) {
    console.warn(`[RodSki] rodski-web 不可用 ${path}:`, e.message);
    return null;
  }
}

async function getRodskiWebStatus() {
  return (await fetchRodskiWeb('/health')) !== null;
}

async function getLastFailure() {
  return await fetchRodskiWeb('/api/plugin/last-failure');
}

// ---- 截图 ----

/**
 * 截取录制标签页的可见区域。
 * 注意：chrome.tabs.captureVisibleTab 只能截取“当前窗口的活动标签”，
 * 如果用户已经切换到别的标签页，直接截图会截错对象。
 * 这里先校验 recordingState.tabId 当前是否为活动标签，不是则跳过并提示，
 * 而不是静默截一张错误的图。
 */
async function captureTab(label, seq, meta) {
  if (!recordingState.tabId) return null;
  try {
    const tab = await chrome.tabs.get(recordingState.tabId);
    if (!tab.active) {
      console.warn(`[RodSki] 跳过截图：录制标签页当前不是活动标签（label=${label}）`);
      return null;
    }
    const dataUrl = await chrome.tabs.captureVisibleTab(tab.windowId, { format: 'png', quality: 90 });
    const entry = {
      label: label || `step_${seq}`,
      seq,
      timestamp: new Date().toISOString(),
      url: meta?.url || tab.url || '',
      title: meta?.title || tab.title || '',
      dataUrl,
    };
    recordingState.screenshots.push(entry);
    // storage 只缓存缩略图元信息（截断 dataUrl），避免超出 storage 配额
    const forStorage = recordingState.screenshots.slice(-30).map(s => ({ ...s, dataUrl: s.dataUrl?.slice(0, 200) + '...' }));
    await chrome.storage.local.set({ [STORAGE_KEY_SCREENSHOTS]: forStorage });
    return entry;
  } catch (e) {
    console.warn('[RodSki] 截图失败:', e.message);
    return null;
  }
}

// ---- 草稿用例生成 ----

function generateCaseDraft(steps) {
  const caseId = `TC_${Date.now()}`;
  const lines = [];
  lines.push(`<?xml version="1.0" encoding="UTF-8"?>`);
  lines.push(`<!-- RodSki 草稿用例 - 由浏览器插件录制生成，需人工/AI 修正 -->`);
  lines.push(`<!-- 录制时间: ${new Date().toISOString()} -->`);
  lines.push(`<cases>`);
  lines.push(`    <case execute="是" id="${caseId}" title="录制草稿" component_type="界面">`);
  lines.push(`        <test_case>`);

  const currentModel = 'RecordedPage';
  let typeDataRows = [];

  function flushTypeRows() {
    if (typeDataRows.length === 0) return;
    lines.push(`            <!-- input 步骤 - 需补充 data 表数据 -->`);
    typeDataRows.forEach(r => {
      lines.push(`            <test_step action="type" model="${currentModel}" data="${r.dataId}"/>`);
    });
    typeDataRows = [];
  }

  steps.forEach((step, i) => {
    if (step.action === 'navigate') {
      flushTypeRows();
      lines.push(`            <test_step action="navigate" model="" data="${step.url}"/>`);
    } else if (step.action === 'input') {
      const dataId = `D${String(i + 1).padStart(3, '0')}`;
      typeDataRows.push({ dataId, step });
    } else if (step.action === 'click') {
      flushTypeRows();
      const bestLoc = step.target?.locators?.[0];
      const locStr = bestLoc ? `${bestLoc.type}=${bestLoc.value}` : step.target?.description || '?';
      lines.push(`            <!-- click: ${locStr} -->`);
      lines.push(`            <test_step action="type" model="${currentModel}" data="C${String(i + 1).padStart(3, '0')}"/>`);
    }
  });

  flushTypeRows();
  lines.push(`            <test_step action="screenshot" model="" data="result.png"/>`);
  lines.push(`        </test_case>`);
  lines.push(`    </case>`);
  lines.push(`</cases>`);
  return lines.join('\n');
}

function generateModelDraft(steps) {
  const lines = [];
  lines.push(`<?xml version="1.0" encoding="UTF-8"?>`);
  lines.push(`<!-- RodSki 草稿模型 - 由浏览器插件录制生成，需人工/AI 修正 -->`);
  lines.push(`<models>`);
  lines.push(`    <model name="RecordedPage" type="ui">`);

  const seen = new Set();
  steps.forEach((step, i) => {
    if (!step.target?.locators?.length) return;
    const best = step.target.locators[0];
    const key = `${best.type}:${best.value}`;
    if (seen.has(key)) return;
    seen.add(key);
    const elName = best.type === 'id' ? best.value
      : best.type === 'text' ? best.value.replace(/\s+/g, '_').slice(0, 20)
      : `element_${i + 1}`;
    lines.push(`        <!-- ${step.action}: ${step.target.description || ''} -->`);
    lines.push(`        <element name="${elName}" type="ui">`);
    lines.push(`            <location type="${best.type}">${best.value}</location>`);
    lines.push(`        </element>`);
  });

  lines.push(`    </model>`);
  lines.push(`</models>`);
  return lines.join('\n');
}

// ---- 本地保存：chrome.downloads ----

async function downloadDataUrl(dataUrl, filename) {
  return new Promise((resolve) => {
    chrome.downloads.download({ url: dataUrl, filename, saveAs: false }, (id) => resolve(id));
  });
}

async function downloadText(content, filename, mimeType = 'application/json') {
  const b64 = btoa(unescape(encodeURIComponent(content)));
  const dataUrl = `data:${mimeType};base64,${b64}`;
  return downloadDataUrl(dataUrl, filename);
}

/**
 * 将整个录制结果保存到本地 Downloads 文件夹。
 * steps 必须传入 recordingState.steps（background 累积的完整跨页面序列），
 * 不能再用 content script 本地的局部步骤数组，否则会丢失导航前的操作记录。
 */
async function saveRecordingLocally(steps, screenshots, finalSnapshot) {
  const ts = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
  const dir = `RodSki_录制_${ts}`;

  const manifest = {
    rodski_plugin_version: '1.0.0',
    recorded_at: recordingState.startTime || new Date().toISOString(),
    exported_at: new Date().toISOString(),
    base_url: steps[0]?.url || '',
    total_steps: steps.length,
    total_screenshots: screenshots.length,
    steps,
    screenshots: screenshots.map(s => ({
      label: s.label,
      seq: s.seq,
      timestamp: s.timestamp,
      url: s.url,
      title: s.title,
      filename: `screenshots/${String(s.seq).padStart(3, '0')}_${s.label}.png`,
    })),
    final_page_snapshot: finalSnapshot || null,
    ai_hint: `这是一份 RodSki 测试录制素材包。
请基于 steps（操作序列，含跨页面导航）和 final_page_snapshot（最终页面元素）生成符合 RodSki 格式的 case XML 和 model.xml。
参考 case_draft.xml / model_draft.xml（已自动生成草稿），在此基础上修正即可。
注意：
1. type 关键字支持批量数据，合并连续 input 步骤为单行
2. 在关键断言点补充 verify 步骤
3. 定位器优先使用 id，其次 xpath
4. 输出格式参考 rodski/docs/TEST_CASE_WRITING_GUIDE.md`,
  };
  await downloadText(JSON.stringify(manifest, null, 2), `${dir}/manifest.json`);

  const caseDraft = generateCaseDraft(steps);
  await downloadText(caseDraft, `${dir}/case_draft.xml`, 'application/xml');

  const modelDraft = generateModelDraft(steps);
  await downloadText(modelDraft, `${dir}/model_draft.xml`, 'application/xml');

  for (const sc of screenshots) {
    if (!sc.dataUrl) continue;
    const fname = `${dir}/screenshots/${String(sc.seq).padStart(3, '0')}_${sc.label}.png`;
    await downloadDataUrl(sc.dataUrl, fname);
  }

  return { dir, stepCount: steps.length, screenshotCount: screenshots.length };
}

// ---- 导航监听：修复"切页面后动作丢失" ----

// 整页导航完成（服务端渲染跳转 / 表单提交跳转等，会重建 content script 上下文）
chrome.webNavigation.onCompleted.addListener(async (details) => {
  if (!recordingState.active) return;
  if (details.tabId !== recordingState.tabId) return;
  if (details.frameId !== 0) return; // 只关心主 frame

  // 由 background 直接补一条 navigate 步骤，不依赖新页面的 content script
  addStep({ action: 'navigate', url: details.url, title: '' });

  // 新页面的 content script 是全新上下文（recording=false），主动恢复
  await sendToRecordingTab(
    { type: 'RESUME_RECORDING', payload: { stepCount: recordingState.steps.length } },
    { retries: 4, delayMs: 300 }
  );
});

// SPA 软导航（history.pushState / replaceState），同一 JS 上下文不会重建，
// content script 的 recording 状态天然保留，这里只需补一条 navigate 步骤
chrome.webNavigation.onHistoryStateUpdated.addListener((details) => {
  if (!recordingState.active) return;
  if (details.tabId !== recordingState.tabId) return;
  if (details.frameId !== 0) return;
  addStep({ action: 'navigate', url: details.url, title: '' });
});

// 录制中标签页被关闭：自动停止并保存已采集的内容，避免状态卡死
chrome.tabs.onRemoved.addListener(async (tabId) => {
  if (recordingState.active && tabId === recordingState.tabId) {
    console.warn('[RodSki] 录制标签页被关闭，自动停止并保存');
    recordingState.active = false;
    await saveRecordingLocally(recordingState.steps, recordingState.screenshots, null);
    await chrome.storage.local.set({
      [STORAGE_KEY_STEPS]: recordingState.steps,
      [STORAGE_KEY_RECORDING]: { active: false },
    });
  }
});

// ---- 消息处理 ----

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  handleMessage(msg, sender).then(sendResponse).catch(err => {
    console.error('[RodSki] 消息处理错误:', err);
    sendResponse({ ok: false, error: err.message });
  });
  return true;
});

async function handleMessage(msg, sender) {
  switch (msg.type) {

    // ---- 录制控制 ----
    case 'START_RECORDING': {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      const stored = await chrome.storage.local.get([STORAGE_KEY_AUTO_SHOT]);
      recordingState = {
        active: true,
        tabId: tab.id,
        windowId: tab.windowId,
        steps: [],
        screenshots: [],
        startTime: new Date().toISOString(),
        autoScreenshot: !!stored[STORAGE_KEY_AUTO_SHOT],
        stepSeq: 0,
      };
      // 初始 navigate 步骤由 background 直接记录（可靠，不依赖 content script 竞态）
      addStep({ action: 'navigate', url: tab.url || '', title: tab.title || '' });

      await sendToRecordingTab({ type: 'START_RECORDING' });
      await chrome.storage.local.set({
        [STORAGE_KEY_RECORDING]: { active: true, startTime: recordingState.startTime, tabId: tab.id },
      });
      return { ok: true, autoScreenshot: recordingState.autoScreenshot, tabId: tab.id };
    }

    case 'STOP_RECORDING_CMD': {
      if (!recordingState.active) return { ok: false, error: '未在录制' };
      await sendToRecordingTab({ type: 'STOP_RECORDING_CMD' });
      return { ok: true };
    }

    case 'STOP_RECORDING': {
      // content script 只带来 finalSnapshot，步骤序列完全以 background 的累积结果为准
      const { finalSnapshot } = msg.payload || {};
      recordingState.active = false;

      const saveResult = await saveRecordingLocally(recordingState.steps, recordingState.screenshots, finalSnapshot);

      await chrome.storage.local.set({
        [STORAGE_KEY_STEPS]: recordingState.steps,
        [STORAGE_KEY_RECORDING]: { active: false },
      });

      return {
        ok: true,
        saved: true,
        dir: saveResult.dir,
        stepCount: saveResult.stepCount,
        screenshotCount: saveResult.screenshotCount,
      };
    }

    case 'RECORD_STEP': {
      if (!recordingState.active) return { ok: false, error: '未在录制' };
      // 只接受录制标签页发来的步骤，避免用户切到其他标签操作污染录制序列
      if (sender.tab && recordingState.tabId && sender.tab.id !== recordingState.tabId) {
        return { ok: false, error: '非录制标签页，已忽略' };
      }
      const step = addStep(msg.payload);

      if (recordingState.autoScreenshot) {
        setTimeout(async () => {
          await captureTab(`auto_${step.action}_${step.seq}`, step.seq, { url: step.url });
        }, 400);
      }

      return { ok: true, stepCount: recordingState.steps.length };
    }

    case 'CAPTURE_SCREENSHOT': {
      const result = await captureTab(msg.payload?.label, recordingState.stepSeq, msg.payload);
      return { ok: !!result, screenshot: result ? { label: result.label, timestamp: result.timestamp } : null };
    }

    // ---- 自动截图开关 ----
    case 'SET_AUTO_SCREENSHOT': {
      const { enabled } = msg.payload;
      await chrome.storage.local.set({ [STORAGE_KEY_AUTO_SHOT]: enabled });
      recordingState.autoScreenshot = enabled;
      return { ok: true, autoScreenshot: enabled };
    }

    case 'GET_AUTO_SCREENSHOT': {
      const stored = await chrome.storage.local.get([STORAGE_KEY_AUTO_SHOT]);
      return { ok: true, autoScreenshot: !!stored[STORAGE_KEY_AUTO_SHOT] };
    }

    // ---- 手动导出（不停止录制，随时导出当前已采集内容） ----
    case 'EXPORT_NOW': {
      const stored = await chrome.storage.local.get([STORAGE_KEY_STEPS]);
      const steps = recordingState.steps.length > 0 ? recordingState.steps : (stored[STORAGE_KEY_STEPS] || []);
      if (steps.length === 0) return { ok: false, error: '暂无录制数据' };
      const result = await saveRecordingLocally(steps, recordingState.screenshots, null);
      return { ok: true, ...result };
    }

    // ---- 定位器 Picker（非录制态，作用于当前活动标签，行为不变） ----
    case 'ACTIVATE_PICKER': {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      await chrome.tabs.sendMessage(tab.id, { type: 'ACTIVATE_PICKER' });
      return { ok: true };
    }

    case 'DEACTIVATE_PICKER': {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      await chrome.tabs.sendMessage(tab.id, { type: 'DEACTIVATE_PICKER' });
      return { ok: true };
    }

    case 'PICKER_DEACTIVATED':
      return { ok: true };

    case 'GET_PAGE_SNAPSHOT': {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      return await chrome.tabs.sendMessage(tab.id, { type: 'GET_PAGE_SNAPSHOT' });
    }

    // ---- 失败诊断（仍走 rodski-web，可选） ----
    case 'SHOW_DIAGNOSTIC': {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      await chrome.tabs.sendMessage(tab.id, { type: 'SHOW_DIAGNOSTIC', payload: msg.payload });
      return { ok: true };
    }

    case 'FETCH_LAST_FAILURE': {
      const failure = await getLastFailure();
      if (failure?.failure) {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        await chrome.tabs.sendMessage(tab.id, { type: 'SHOW_DIAGNOSTIC', payload: failure.failure });
      }
      return { ok: !!failure?.failure, failure: failure?.failure || null };
    }

    case 'CLEAR_HIGHLIGHTS': {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      await chrome.tabs.sendMessage(tab.id, { type: 'CLEAR_HIGHLIGHTS' });
      return { ok: true };
    }

    // ---- 环境管理（本地存储，不依赖 rodski-web） ----
    case 'GET_ENVS': {
      const stored = await chrome.storage.local.get([STORAGE_KEY_ENV, 'rodski_env_list']);
      const envList = stored['rodski_env_list'] || ['local', 'beta', 'staging', 'prod'];
      return { ok: true, envs: envList, currentEnv: stored[STORAGE_KEY_ENV] || null };
    }

    case 'SWITCH_ENV': {
      const { env } = msg.payload;
      await chrome.storage.local.set({ [STORAGE_KEY_ENV]: env });
      await fetchRodskiWeb('/api/plugin/env/switch', { method: 'POST', body: JSON.stringify({ env }) });
      return { ok: true, env };
    }

    // ---- 状态查询 ----
    case 'GET_STATUS': {
      const webOnline = await getRodskiWebStatus();
      const stored = await chrome.storage.local.get([STORAGE_KEY_ENV, STORAGE_KEY_AUTO_SHOT]);
      return {
        ok: true,
        webOnline,
        recording: recordingState.active,
        stepCount: recordingState.steps.length,
        screenshotCount: recordingState.screenshots.length,
        currentEnv: stored[STORAGE_KEY_ENV] || null,
        autoScreenshot: !!stored[STORAGE_KEY_AUTO_SHOT],
      };
    }

    case 'GET_LAST_EXPORT': {
      const stored = await chrome.storage.local.get([STORAGE_KEY_STEPS]);
      const steps = recordingState.steps.length > 0 ? recordingState.steps : (stored[STORAGE_KEY_STEPS] || []);
      return { ok: true, stepCount: steps.length };
    }

    default:
      return { ok: false, error: `未知消息类型: ${msg.type}` };
  }
}

// ---- 安装/启动 ----
chrome.runtime.onInstalled.addListener(() => {
  console.log('[RodSki] 浏览器插件已安装 v1.0.0');
});

console.log('[RodSki] service_worker.js 已加载');
