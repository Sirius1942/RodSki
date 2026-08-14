/**
 * 操作录制器 - 捕获用户操作并转发给 background，不在本地维护步骤序列
 *
 * 修复说明：
 * - 步骤序列的唯一权威来源是 service_worker.js 的 recordingState.steps。
 *   content script 每次页面导航都会被销毁重建（recording 状态归零），
 *   所以绝不能让"本地 steps 数组"成为权威数据，否则跨页面操作会丢失
 *   （这正是"切换页面后动作丢失/停止时报错"的根因）。
 * - background 通过 chrome.webNavigation 监听导航，导航完成后主动发送
 *   RESUME_RECORDING 消息，让新页面的 content script 恢复事件监听。
 */

(function() {
  if (window.__rodski_recorder_loaded) return;
  window.__rodski_recorder_loaded = true;

  let recording = false;
  let localStepCount = 0; // 仅用于本地 UI 显示（录制条步数），不作为权威数据
  let screenshotPending = false;

  // ---- 事件采集：捕获后立即转发给 background，不在本地攒数组 ----

  function onClickCapture(e) {
    if (!recording) return;
    const target = e.target;
    if (!target || target.closest('#__rodski_locator_tooltip') || target.closest('#__rodski_rec_bar')) return;

    const locators = window.__rodski.getLocators(target);
    const step = {
      action: 'click',
      url: location.href,
      target: {
        tag: target.tagName.toLowerCase(),
        description: window.__rodski.describeElement(target),
        locators: locators.slice(0, 3),
      },
    };
    sendStep(step, `🖱️ click ${target.tagName.toLowerCase()}`);
  }

  function onInputCapture(e) {
    if (!recording) return;
    const target = e.target;
    if (!target || !['input', 'textarea'].includes(target.tagName.toLowerCase())) return;
    if (target.type === 'password') return; // 不录制密码字段

    clearTimeout(target.__rodski_input_timer);
    target.__rodski_input_timer = setTimeout(() => {
      const locators = window.__rodski.getLocators(target);
      const step = {
        action: 'input',
        url: location.href,
        value: target.value?.slice(0, 200) || '',
        target: {
          tag: target.tagName.toLowerCase(),
          description: window.__rodski.describeElement(target),
          locators: locators.slice(0, 3),
        },
      };
      sendStep(step, `⌨️ input "${step.value.slice(0, 20)}"`);
    }, 300);
  }

  /** 发送步骤到 background；background 负责编号、去重、追加、触发自动截图 */
  function sendStep(step, feedbackMsg) {
    chrome.runtime.sendMessage({ type: 'RECORD_STEP', payload: step }, (resp) => {
      if (resp?.ok) {
        localStepCount = resp.stepCount ?? (localStepCount + 1);
        showStepFeedback(feedbackMsg, localStepCount);
      }
    });
  }

  // ---- 截图（手动） ----

  function captureScreenshot(label) {
    if (screenshotPending) return;
    screenshotPending = true;
    chrome.runtime.sendMessage({
      type: 'CAPTURE_SCREENSHOT',
      payload: { label: label || 'manual', url: location.href, title: document.title },
    }, () => { screenshotPending = false; });
  }

  // ---- 录制控制条 ----

  let recBar = null;

  function createRecBar() {
    if (recBar) return; // 恢复录制时若已存在（不太可能，但防御）
    recBar = document.createElement('div');
    recBar.id = '__rodski_rec_bar';
    recBar.style.cssText = `
      position: fixed;
      bottom: 20px;
      right: 20px;
      z-index: 2147483647;
      background: #1a1a2e;
      border: 1.5px solid #e74c3c;
      border-radius: 10px;
      padding: 8px 14px;
      font-family: 'SF Mono', monospace;
      font-size: 12px;
      color: #e0e0e0;
      display: flex;
      align-items: center;
      gap: 10px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.5);
      cursor: default;
      user-select: none;
    `;
    recBar.innerHTML = `
      <span style="color:#e74c3c;font-size:16px">●</span>
      <span id="__rodski_rec_status">录制中</span>
      <span id="__rodski_rec_count" style="color:#888">${localStepCount} 步</span>
      <button id="__rodski_rec_screenshot" style="
        background:#2c3e50;border:1px solid #4a90d9;color:#4a90d9;
        padding:3px 8px;border-radius:4px;cursor:pointer;font-size:11px;
      ">📷 截图</button>
      <button id="__rodski_rec_stop" style="
        background:#e74c3c;border:none;color:#fff;
        padding:3px 8px;border-radius:4px;cursor:pointer;font-size:11px;
      ">停止</button>
    `;
    document.body.appendChild(recBar);

    document.getElementById('__rodski_rec_screenshot').addEventListener('click', () => {
      captureScreenshot('manual');
      showStepFeedback('📷 截图已保存', localStepCount);
    });
    document.getElementById('__rodski_rec_stop').addEventListener('click', () => {
      stopRecording();
    });
  }

  function updateRecBarCount(count) {
    const el = document.getElementById('__rodski_rec_count');
    if (el) el.textContent = `${count} 步`;
  }

  function removeRecBar() {
    if (recBar) {
      recBar.remove();
      recBar = null;
    }
  }

  // ---- 步骤反馈提示 ----

  let feedbackTimer = null;
  function showStepFeedback(msg, stepCount) {
    let fb = document.getElementById('__rodski_step_feedback');
    if (!fb) {
      fb = document.createElement('div');
      fb.id = '__rodski_step_feedback';
      fb.style.cssText = `
        position: fixed;
        bottom: 80px;
        right: 20px;
        z-index: 2147483646;
        background: rgba(26,26,46,0.92);
        color: #7ec8a4;
        padding: 6px 12px;
        border-radius: 6px;
        font-family: 'SF Mono', monospace;
        font-size: 11px;
        pointer-events: none;
        transition: opacity 0.3s;
      `;
      document.body.appendChild(fb);
    }
    fb.textContent = `步骤${stepCount}：${msg}`;
    fb.style.opacity = '1';
    clearTimeout(feedbackTimer);
    feedbackTimer = setTimeout(() => { if (fb) fb.style.opacity = '0'; }, 2000);
    updateRecBarCount(stepCount);
  }

  // ---- 录制生命周期 ----

  function bindListeners() {
    document.addEventListener('click', onClickCapture, true);
    document.addEventListener('input', onInputCapture, true);
  }

  function unbindListeners() {
    document.removeEventListener('click', onClickCapture, true);
    document.removeEventListener('input', onInputCapture, true);
  }

  /** 由 popup 触发：本页面开始录制（这是本次录制的第一个页面） */
  function startRecording() {
    if (recording) return;
    recording = true;
    localStepCount = 0;
    bindListeners();
    createRecBar();
    console.log('[RodSki] 录制已开始');
  }

  /**
   * 由 background 在导航完成后触发：恢复录制状态。
   * 与 startRecording 的区别：不重置 localStepCount（background 已经维护了
   * 跨页面的真实步数，这里用 background 传来的 stepCount 同步显示）。
   */
  function resumeRecording(stepCount) {
    if (recording) return; // 同一上下文已在录制中（SPA 导航），无需处理
    recording = true;
    localStepCount = stepCount ?? localStepCount;
    bindListeners();
    createRecBar();
    updateRecBarCount(localStepCount);
    console.log('[RodSki] 导航后已恢复录制，当前步数:', localStepCount);
  }

  function stopRecording() {
    if (!recording) return;
    recording = false;
    unbindListeners();
    removeRecBar();

    // 只带上 finalSnapshot；步骤序列以 background 的累积结果为准
    const snapshot = window.__rodski.getPageSnapshot();
    chrome.runtime.sendMessage({
      type: 'STOP_RECORDING',
      payload: { finalSnapshot: snapshot },
    });
    console.log('[RodSki] 录制已停止');
  }

  // ---- 监听 service worker 消息 ----

  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg.type === 'START_RECORDING') {
      startRecording();
      sendResponse({ ok: true });
    } else if (msg.type === 'RESUME_RECORDING') {
      resumeRecording(msg.payload?.stepCount);
      sendResponse({ ok: true });
    } else if (msg.type === 'STOP_RECORDING_CMD') {
      stopRecording();
      sendResponse({ ok: true });
    } else if (msg.type === 'MANUAL_SCREENSHOT') {
      captureScreenshot('manual');
      sendResponse({ ok: true });
    }
    return true;
  });

  window.__rodski.startRecording = startRecording;
  window.__rodski.stopRecording = stopRecording;
  window.__rodski.isRecording = () => recording;

  console.log('[RodSki] recorder.js 已加载');
})();
