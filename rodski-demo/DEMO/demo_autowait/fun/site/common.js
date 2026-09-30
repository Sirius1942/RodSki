/* demo_autowait 测试站点公共脚本（v11.7.0 AutoWait 验收）
 * 每个页面通过查询参数 ?d=毫秒 控制延迟；d<0 表示"永不发生"。
 * 所有时间线都从页面脚本执行时刻开始计时。 */
(function () {
  var params = new URLSearchParams(window.location.search);
  window.AW = {
    /** 读取 ?name=毫秒，缺省返回 def */
    ms: function (name, def) {
      var v = params.get(name);
      if (v === null || v === '') return def;
      var n = parseInt(v, 10);
      return isNaN(n) ? def : n;
    },
    /** ms<0 永不执行；否则 ms 毫秒后执行 */
    at: function (ms, fn) {
      if (ms < 0) return;
      setTimeout(fn, ms);
    },
    $: function (id) { return document.getElementById(id); },
    set: function (id, text) { document.getElementById(id).textContent = text; },
    /** 创建元素并追加到容器 */
    add: function (parentId, tag, attrs, text) {
      var el = document.createElement(tag);
      Object.keys(attrs || {}).forEach(function (k) { el.setAttribute(k, attrs[k]); });
      if (text !== undefined) el.textContent = text;
      document.getElementById(parentId).appendChild(el);
      return el;
    }
  };
  // 页面上显示当前延迟，便于人工排查
  document.addEventListener('DOMContentLoaded', function () {
    var info = document.getElementById('delayInfo');
    if (info) info.textContent = 'd=' + (params.get('d') || '(默认)');
  });
})();
