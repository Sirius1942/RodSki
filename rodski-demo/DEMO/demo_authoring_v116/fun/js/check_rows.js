// v11.6.0 C3：evaluate 通过 file: 引用脚本，脚本内可直接写 && < 等字符，无需 XML 转义
(() => {
  const rows = document.querySelectorAll('#orderBody tr.order-row');
  if (rows.length === 10 && rows[0].innerText.trim() === 'ORD1') {
    return rows.length;
  }
  throw new Error('期望 10 行且首行为 ORD1，实际 ' + rows.length + ' 行');
})()
