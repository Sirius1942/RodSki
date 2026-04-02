// RodSki Web - Main JavaScript

// 全局工具函数
window.showToast = function(message, type = 'info') {
    let toast = document.getElementById('toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'toast';
        toast.className = 'toast';
        document.body.appendChild(toast);
    }
    
    toast.textContent = message;
    toast.className = `toast toast-${type}`;
    
    // 触发重绘
    toast.offsetHeight;
    toast.classList.add('show');
    
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
};

// 格式化时间戳
window.formatTime = function(timestamp) {
    if (!timestamp) return '-';
    const date = new Date(timestamp);
    return date.toLocaleString('zh-CN');
};

// 复制到剪贴板
window.copyToClipboard = function(text) {
    navigator.clipboard.writeText(text).then(() => {
        showToast('已复制到剪贴板', 'success');
    }).catch(err => {
        console.error('复制失败:', err);
    });
};

// 格式化 JSON 显示
window.formatJSON = function(obj) {
    try {
        return JSON.stringify(obj, null, 2);
    } catch (e) {
        return String(obj);
    }
};

// API 请求封装
window.apiRequest = async function(url, options = {}) {
    try {
        const response = await fetch(url, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API 请求失败:', error);
        throw error;
    }
};
