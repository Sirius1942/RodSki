/* global acquireVsCodeApi */

const vscode = acquireVsCodeApi();
const SVG_NS = 'http://www.w3.org/2000/svg';
const NODE_WIDTH = 190;
const NODE_HEIGHT = 68;
const H_GAP = 110;
const V_GAP = 42;
const PADDING = 56;
const MAX_LABEL_LENGTH = 44;

let xmlDoc = null;
let currentFilePath = '';
let models = [];
let selectedModelIndex = 0;
let selectedFlowId = '';
let selectedElement = null;
let layout = null;
let zoom = 1;
let offsetX = 0;
let offsetY = 0;
let panState = null;

function directChildren(element, name) {
  if (!element) return [];
  return Array.from(element.children).filter(child => child.localName === name || child.tagName === name);
}

function firstChild(element, name) {
  return directChildren(element, name)[0] || null;
}

function childText(element, name) {
  return firstChild(element, name)?.textContent?.trim() || '';
}

function attr(element, name) {
  return element?.getAttribute(name) || '';
}

function parseBusinessXml(xml) {
  const doc = new DOMParser().parseFromString(xml, 'application/xml');
  if (doc.getElementsByTagName('parsererror').length > 0) {
    throw new Error('XML 解析失败，请检查业务模型文件格式。');
  }
  const root = doc.documentElement;
  if (!root || root.localName !== 'business_models') {
    throw new Error('根节点必须是 <business_models>。');
  }
  const modelElements = directChildren(root, 'business_model');
  if (!modelElements.length) {
    throw new Error('未找到 <business_model> 定义。');
  }

  const parsedModels = modelElements.map(parseModelElement);
  return { doc, models: parsedModels };
}

function parseModelElement(modelElement) {
  const modelId = attr(modelElement, 'id');
  if (!modelId) throw new Error('业务模型缺少 id 属性。');
  const nodesElement = firstChild(modelElement, 'nodes');
  const edgesElement = firstChild(modelElement, 'edges');
  const flowsElement = firstChild(modelElement, 'flows');
  if (!nodesElement || !edgesElement || !flowsElement) {
    throw new Error(`业务模型 ${modelId} 必须包含 nodes、edges 和 flows。`);
  }
  const nodeElements = directChildren(nodesElement, 'node');
  if (!nodeElements.length) throw new Error(`业务模型 ${modelId} 至少需要一个 node。`);
  if (nodeElements.some(nodeElement => !attr(nodeElement, 'id'))) {
    throw new Error(`业务模型 ${modelId} 的每个 node 都必须有 id。`);
  }
  const edgeElements = directChildren(edgesElement, 'edge');
  if (!edgeElements.length) throw new Error(`业务模型 ${modelId} 至少需要一条 edge。`);
  if (edgeElements.some(edgeElement => !attr(edgeElement, 'from') || !attr(edgeElement, 'to'))) {
    throw new Error(`业务模型 ${modelId} 的每条 edge 都必须有 from 和 to。`);
  }
  const flowElements = directChildren(flowsElement, 'flow');
  if (!flowElements.length) throw new Error(`业务模型 ${modelId} 至少需要一个 flow。`);
  if (flowElements.some(flowElement => !attr(flowElement, 'id') || !attr(flowElement, 'path'))) {
    throw new Error(`业务模型 ${modelId} 的每个 flow 都必须有 id 和 path。`);
  }
  const nodes = nodeElements.map(nodeElement => {
    const stepsElement = firstChild(nodeElement, 'steps');
    return {
      id: attr(nodeElement, 'id'),
      title: attr(nodeElement, 'title') || attr(nodeElement, 'id'),
      description: childText(nodeElement, 'description'),
      steps: directChildren(stepsElement, 'test_step').map(step => ({
        action: attr(step, 'action'),
        model: attr(step, 'model'),
        data: attr(step, 'data'),
      })),
    };
  }).filter(node => node.id);

  const edges = edgeElements.map(edgeElement => ({
    source: attr(edgeElement, 'from'),
    target: attr(edgeElement, 'to'),
    condition: attr(edgeElement, 'condition'),
    label: attr(edgeElement, 'label'),
  }));

  const flows = flowElements.map(flowElement => ({
    id: attr(flowElement, 'id'),
    type: attr(flowElement, 'type'),
    path: attr(flowElement, 'path').split('>').map(part => part.trim()).filter(Boolean),
  })).filter(flow => flow.id);

  return {
    id: modelId,
    name: attr(modelElement, 'name') || modelId,
    version: attr(modelElement, 'version'),
    lifecycle: attr(modelElement, 'lifecycle'),
    idempotent: attr(modelElement, 'idempotent'),
    description: childText(modelElement, 'description'),
    inputTable: modelId,
    verifyTable: `${modelId}_verify`,
    nodes,
    edges,
    flows,
  };
}

function layoutModel(model) {
  const nodeIds = model.nodes.map(node => node.id);
  const nodeSet = new Set(nodeIds);
  const outgoing = new Map(nodeIds.map(id => [id, []]));
  const incomingCount = new Map(nodeIds.map(id => [id, 0]));
  const validEdges = [];
  let invalidReferences = 0;

  model.edges.forEach(edge => {
    if (!nodeSet.has(edge.source) || !nodeSet.has(edge.target)) {
      invalidReferences += 1;
      return;
    }
    outgoing.get(edge.source).push(edge.target);
    incomingCount.set(edge.target, incomingCount.get(edge.target) + 1);
    validEdges.push(edge);
  });

  const queue = nodeIds.filter(id => incomingCount.get(id) === 0);
  const order = [];
  const remaining = new Map(incomingCount);
  while (queue.length) {
    const id = queue.shift();
    order.push(id);
    for (const target of outgoing.get(id)) {
      remaining.set(target, remaining.get(target) - 1);
      if (remaining.get(target) === 0) queue.push(target);
    }
  }

  const hasCycle = order.length !== nodeIds.length;
  const maxKnownLevel = new Map(nodeIds.map(id => [id, 0]));
  for (const id of order) {
    for (const target of outgoing.get(id)) {
      maxKnownLevel.set(target, Math.max(maxKnownLevel.get(target), maxKnownLevel.get(id) + 1));
    }
  }
  if (hasCycle) {
    const fallbackLevel = Math.max(...Array.from(maxKnownLevel.values()), 0) + 1;
    nodeIds.filter(id => !order.includes(id)).forEach((id, index) => {
      maxKnownLevel.set(id, fallbackLevel + index);
    });
  }

  const buckets = new Map();
  nodeIds.forEach(id => {
    const level = maxKnownLevel.get(id) || 0;
    if (!buckets.has(level)) buckets.set(level, []);
    buckets.get(level).push(id);
  });
  const positions = new Map();
  const maxLevel = Math.max(...Array.from(buckets.keys()), 0);
  const maxRows = Math.max(...Array.from(buckets.values()).map(items => items.length), 1);
  buckets.forEach((ids, level) => {
    ids.forEach((id, row) => {
      positions.set(id, {
        x: PADDING + level * (NODE_WIDTH + H_GAP),
        y: PADDING + row * (NODE_HEIGHT + V_GAP),
        level,
        row,
      });
    });
  });

  return {
    positions,
    validEdges,
    incomingCount,
    outgoing,
    width: PADDING * 2 + (maxLevel + 1) * NODE_WIDTH + maxLevel * H_GAP,
    height: PADDING * 2 + maxRows * NODE_HEIGHT + (maxRows - 1) * V_GAP,
    hasCycle,
    invalidReferences,
  };
}

function modelAtIndex() {
  return models[selectedModelIndex] || null;
}

function selectedFlow(model) {
  return model?.flows.find(flow => flow.id === selectedFlowId) || null;
}

function createSvgElement(tag, attributes = {}) {
  const element = document.createElementNS(SVG_NS, tag);
  Object.entries(attributes).forEach(([key, value]) => element.setAttribute(key, String(value)));
  return element;
}

function truncate(text, max = MAX_LABEL_LENGTH) {
  if (!text || text.length <= max) return text || '';
  return `${text.slice(0, Math.max(0, max - 1))}…`;
}

function appendText(parent, tag, text, attributes = {}) {
  const element = document.createElementNS(SVG_NS, tag);
  Object.entries(attributes).forEach(([key, value]) => element.setAttribute(key, String(value)));
  element.textContent = text || '';
  parent.appendChild(element);
  return element;
}

function setStatus(text, kind = '') {
  const status = document.getElementById('status');
  if (!status) return;
  status.textContent = text;
  status.className = kind ? `status ${kind}` : 'status';
}

function clearElement(element) {
  while (element?.firstChild) element.removeChild(element.firstChild);
}

function renderSelectors() {
  const modelSelect = document.getElementById('model-select');
  const flowSelect = document.getElementById('flow-select');
  if (!modelSelect || !flowSelect) return;

  clearElement(modelSelect);
  models.forEach((model, index) => {
    const option = document.createElement('option');
    option.value = String(index);
    option.textContent = `${model.name} (${model.id})`;
    modelSelect.appendChild(option);
  });
  modelSelect.value = String(selectedModelIndex);

  const model = modelAtIndex();
  clearElement(flowSelect);
  const allOption = document.createElement('option');
  allOption.value = '';
  allOption.textContent = '全部路径';
  flowSelect.appendChild(allOption);
  (model?.flows || []).forEach(flow => {
    const option = document.createElement('option');
    option.value = flow.id;
    option.textContent = `${flow.id} · ${flow.type}`;
    flowSelect.appendChild(option);
  });
  flowSelect.value = selectedFlowId;
}

function renderModelMeta(model) {
  const meta = document.getElementById('model-meta');
  if (!meta || !model) return;
  clearElement(meta);
  const title = document.createElement('div');
  title.className = 'model-title';
  title.textContent = `${model.name}  [${model.id}]`;
  meta.appendChild(title);
  const detail = document.createElement('div');
  detail.className = 'model-detail';
  const parts = [
    `version ${model.version || '-'}`,
    `nodes ${model.nodes.length}`,
    `edges ${model.edges.length}`,
    `flows ${model.flows.length}`,
    `input: ${model.inputTable}`,
    `verify: ${model.verifyTable}`,
  ];
  detail.textContent = parts.join(' · ');
  meta.appendChild(detail);
}

function nodeKind(nodeId, graph) {
  const incoming = graph.incomingCount.get(nodeId) || 0;
  const outgoing = graph.outgoing.get(nodeId)?.length || 0;
  if (incoming === 0 && outgoing === 0) return 'start-end';
  if (incoming === 0) return 'start';
  if (outgoing > 1) return 'decision';
  if (outgoing === 0) return 'terminal';
  return 'normal';
}

function flowEdgeKeys(flow) {
  const keys = new Set();
  if (!flow) return keys;
  for (let i = 0; i < flow.path.length - 1; i += 1) {
    keys.add(`${flow.path[i]}->${flow.path[i + 1]}`);
  }
  return keys;
}

function drawEdge(svg, edge, graph, activeEdges, flow) {
  const source = graph.positions.get(edge.source);
  const target = graph.positions.get(edge.target);
  if (!source || !target) return;
  const x1 = source.x + NODE_WIDTH;
  const y1 = source.y + NODE_HEIGHT / 2;
  const x2 = target.x;
  const y2 = target.y + NODE_HEIGHT / 2;
  const curve = Math.max(30, Math.abs(x2 - x1) * 0.42);
  const path = createSvgElement('path', {
    d: `M ${x1} ${y1} C ${x1 + curve} ${y1}, ${x2 - curve} ${y2}, ${x2} ${y2}`,
    class: `business-edge ${activeEdges.size && !activeEdges.has(`${edge.source}->${edge.target}`) ? 'dimmed' : ''} ${activeEdges.has(`${edge.source}->${edge.target}`) ? 'active' : ''} ${selectedElement?.kind === 'edge' && selectedElement.source === edge.source && selectedElement.target === edge.target ? 'selected' : ''}`,
    'data-source': edge.source,
    'data-target': edge.target,
    'marker-end': 'url(#arrow)',
  });
  path.addEventListener('click', event => {
    event.stopPropagation();
    selectedElement = { kind: 'edge', source: edge.source, target: edge.target };
    renderGraph(modelAtIndex());
    showEdgeDetails(edge, flow);
  });
  svg.appendChild(path);

  const label = edge.label || edge.condition;
  if (label) {
    const labelText = createSvgElement('text', {
      x: (x1 + x2) / 2,
      y: (y1 + y2) / 2 - 7,
      class: 'edge-label',
      'text-anchor': 'middle',
    });
    labelText.textContent = truncate(label, 38);
    svg.appendChild(labelText);
  }
}

function drawNode(svg, node, graph, activeNodes) {
  const position = graph.positions.get(node.id);
  if (!position) return;
  const kind = nodeKind(node.id, graph);
  const isActive = !activeNodes.size || activeNodes.has(node.id);
  const group = createSvgElement('g', {
    class: `business-node node-${kind} ${isActive ? 'active' : 'dimmed'} ${selectedElement?.kind === 'node' && selectedElement.id === node.id ? 'selected' : ''}`,
    transform: `translate(${position.x} ${position.y})`,
    tabindex: '0',
    role: 'button',
    'aria-label': `${node.title} (${node.id})`,
  });
  group.dataset.nodeId = node.id;

  if (kind === 'decision') {
    group.appendChild(createSvgElement('polygon', {
      points: `${NODE_WIDTH / 2},0 ${NODE_WIDTH},${NODE_HEIGHT / 2} ${NODE_WIDTH / 2},${NODE_HEIGHT} 0,${NODE_HEIGHT / 2}`,
    }));
  } else {
    group.appendChild(createSvgElement('rect', {
      x: 0,
      y: 0,
      width: NODE_WIDTH,
      height: NODE_HEIGHT,
      rx: kind === 'terminal' || kind === 'start' || kind === 'start-end' ? 18 : 5,
    }));
  }
  appendText(group, 'text', truncate(node.title, 27), {
    x: NODE_WIDTH / 2,
    y: 28,
    class: 'node-title',
    'text-anchor': 'middle',
  });
  appendText(group, 'text', truncate(node.id, 31), {
    x: NODE_WIDTH / 2,
    y: 49,
    class: 'node-id',
    'text-anchor': 'middle',
  });
  group.addEventListener('click', event => {
    event.stopPropagation();
    selectedElement = { kind: 'node', id: node.id };
    renderGraph(modelAtIndex());
    showNodeDetails(node, kind);
  });
  group.addEventListener('keydown', event => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      selectedElement = { kind: 'node', id: node.id };
      renderGraph(modelAtIndex());
      showNodeDetails(node, kind);
    }
  });
  svg.appendChild(group);
}

function renderGraph(model) {
  const svg = document.getElementById('diagram');
  if (!svg || !model) return;
  layout = layoutModel(model);
  clearElement(svg);
  svg.setAttribute('viewBox', `0 0 ${layout.width} ${layout.height}`);
  svg.setAttribute('aria-label', `${model.name} business model diagram`);

  const defs = createSvgElement('defs');
  const marker = createSvgElement('marker', {
    id: 'arrow',
    viewBox: '0 0 10 10',
    refX: '9',
    refY: '5',
    markerWidth: '7',
    markerHeight: '7',
    orient: 'auto-start-reverse',
  });
  marker.appendChild(createSvgElement('path', { d: 'M 0 0 L 10 5 L 0 10 z' }));
  defs.appendChild(marker);
  svg.appendChild(defs);

  const canvas = createSvgElement('g', { id: 'diagram-canvas' });
  svg.appendChild(canvas);
  const flow = selectedFlow(model);
  const activeNodes = flow ? new Set(flow.path) : new Set();
  const activeEdges = flowEdgeKeys(flow);
  layout.validEdges.forEach(edge => drawEdge(canvas, edge, layout, activeEdges, flow));
  model.nodes.forEach(node => drawNode(canvas, node, layout, activeNodes));
  applyTransform();

  renderModelMeta(model);
  if (layout.hasCycle) {
    setStatus('图包含环，当前按兜底布局显示；请运行 business validate。', 'warning');
  } else if (layout.invalidReferences) {
    setStatus(`发现 ${layout.invalidReferences} 条指向未知节点的边，请检查 XML。`, 'warning');
  } else {
    setStatus(flow ? `当前高亮路径：${flow.id}` : '未选择路径，显示全部节点和边。');
  }
  if (!selectedElement) {
    showModelDetails(model);
  }
}

function addDetailRow(container, label, value) {
  const row = document.createElement('div');
  row.className = 'detail-row';
  const key = document.createElement('span');
  key.className = 'detail-key';
  key.textContent = label;
  const content = document.createElement('span');
  content.className = 'detail-value';
  content.textContent = value || '-';
  row.appendChild(key);
  row.appendChild(content);
  container.appendChild(row);
}

function showModelDetails(model) {
  const details = document.getElementById('details');
  if (!details || !model) return;
  clearElement(details);
  const heading = document.createElement('h3');
  heading.textContent = '业务模型';
  details.appendChild(heading);
  addDetailRow(details, '说明', model.description);
  addDetailRow(details, '输入表', model.inputTable);
  addDetailRow(details, '期望表', model.verifyTable);
  const hint = document.createElement('p');
  hint.className = 'hint';
  hint.textContent = '选择节点或边查看流程细节。选中 flow 只用于评审和路径断言，不改变业务执行条件。';
  details.appendChild(hint);
}

function showNodeDetails(node, kind) {
  const details = document.getElementById('details');
  if (!details) return;
  clearElement(details);
  const heading = document.createElement('h3');
  heading.textContent = node.title;
  details.appendChild(heading);
  addDetailRow(details, '节点 ID', node.id);
  addDetailRow(details, '节点类型', kind);
  addDetailRow(details, '说明', node.description);

  const stepsHeading = document.createElement('div');
  stepsHeading.className = 'detail-section-title';
  stepsHeading.textContent = `执行步骤 (${node.steps.length})`;
  details.appendChild(stepsHeading);
  if (!node.steps.length) {
    const empty = document.createElement('p');
    empty.className = 'hint';
    empty.textContent = '此节点没有 test_step，通常表示结构、判断或终止节点。';
    details.appendChild(empty);
    return;
  }
  const list = document.createElement('ul');
  list.className = 'step-list';
  node.steps.forEach(step => {
    const item = document.createElement('li');
    item.textContent = [step.action, step.model, step.data].filter(Boolean).join(' · ');
    list.appendChild(item);
  });
  details.appendChild(list);
}

function showEdgeDetails(edge, flow) {
  const details = document.getElementById('details');
  if (!details) return;
  clearElement(details);
  const heading = document.createElement('h3');
  heading.textContent = '业务条件边';
  details.appendChild(heading);
  addDetailRow(details, '来源节点', edge.source);
  addDetailRow(details, '目标节点', edge.target);
  addDetailRow(details, '标签', edge.label);
  addDetailRow(details, '条件', edge.condition);
  if (flow) {
    addDetailRow(details, '当前 flow', flow.id);
  }
}

function renderModel() {
  const model = modelAtIndex();
  if (!model) return;
  renderSelectors();
  renderGraph(model);
}

function loadXml(xml, filePath) {
  currentFilePath = filePath || currentFilePath;
  const filepath = document.getElementById('filepath');
  if (filepath) filepath.textContent = currentFilePath;
  selectedElement = null;
  try {
    const parsed = parseBusinessXml(xml);
    xmlDoc = parsed.doc;
    models = parsed.models;
    selectedModelIndex = Math.min(selectedModelIndex, models.length - 1);
    selectedFlowId = '';
    renderModel();
  } catch (error) {
    xmlDoc = null;
    models = [];
    clearElement(document.getElementById('diagram'));
    clearElement(document.getElementById('model-select'));
    clearElement(document.getElementById('flow-select'));
    setStatus(error instanceof Error ? error.message : '业务模型加载失败。', 'error');
    const details = document.getElementById('details');
    if (details) {
      clearElement(details);
      const message = document.createElement('p');
      message.className = 'error-text';
      message.textContent = error instanceof Error ? error.message : '业务模型加载失败。';
      details.appendChild(message);
    }
  }
}

function applyTransform() {
  const canvas = document.getElementById('diagram-canvas');
  if (canvas) canvas.setAttribute('transform', `translate(${offsetX} ${offsetY}) scale(${zoom})`);
  const zoomLabel = document.getElementById('zoom-label');
  if (zoomLabel) zoomLabel.textContent = `${Math.round(zoom * 100)}%`;
}

function setZoom(nextZoom) {
  zoom = Math.max(0.45, Math.min(2.5, nextZoom));
  applyTransform();
}

function resetView() {
  zoom = 1;
  offsetX = 0;
  offsetY = 0;
  applyTransform();
}

function fitView() {
  resetView();
}

function setupInteractions() {
  document.getElementById('model-select')?.addEventListener('change', event => {
    selectedModelIndex = Number(event.target.value) || 0;
    selectedFlowId = '';
    selectedElement = null;
    renderModel();
  });
  document.getElementById('flow-select')?.addEventListener('change', event => {
    selectedFlowId = event.target.value || '';
    selectedElement = null;
    renderModel();
  });
  document.getElementById('zoom-in')?.addEventListener('click', () => setZoom(zoom + 0.15));
  document.getElementById('zoom-out')?.addEventListener('click', () => setZoom(zoom - 0.15));
  document.getElementById('reset-view')?.addEventListener('click', resetView);
  document.getElementById('fit-view')?.addEventListener('click', fitView);
  document.getElementById('open-source')?.addEventListener('click', () => vscode.postMessage({ command: 'openSource' }));

  const svg = document.getElementById('diagram');
  if (!svg) return;
  svg.addEventListener('click', event => {
    if (event.target === svg) {
      selectedElement = null;
      renderGraph(modelAtIndex());
    }
  });
  svg.addEventListener('wheel', event => {
    event.preventDefault();
    setZoom(zoom + (event.deltaY < 0 ? 0.1 : -0.1));
  }, { passive: false });
  svg.addEventListener('pointerdown', event => {
    if (event.target !== svg) return;
    panState = { x: event.clientX, y: event.clientY, offsetX, offsetY };
    svg.classList.add('panning');
    if (svg.setPointerCapture) svg.setPointerCapture(event.pointerId);
  });
  svg.addEventListener('pointermove', event => {
    if (!panState) return;
    offsetX = panState.offsetX + event.clientX - panState.x;
    offsetY = panState.offsetY + event.clientY - panState.y;
    applyTransform();
  });
  const endPan = () => {
    panState = null;
    svg.classList.remove('panning');
  };
  svg.addEventListener('pointerup', endPan);
  svg.addEventListener('pointercancel', endPan);
}

window.addEventListener('message', event => {
  if (event.data?.command === 'loadXml') loadXml(event.data.xml, event.data.filePath);
});

setupInteractions();
if (window.__BUSINESS_DATA__) {
  loadXml(window.__BUSINESS_DATA__.xml, window.__BUSINESS_DATA__.filePath);
}
vscode.postMessage({ command: 'ready' });

// Exported for the Webview tests and useful for future embedded views.
window.parseBusinessXml = parseBusinessXml;
window.layoutBusinessModel = layoutModel;
window.loadBusinessXml = loadXml;
