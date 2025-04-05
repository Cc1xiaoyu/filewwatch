// SSE 连接管理逻辑 初始化 SSE 连接
let eventSource;

function connectSSE() {
    // 创建 SSE 连接（指向后端端点）
    eventSource = new EventSource("/sse/time");

    // 监听消息事件
    eventSource.onmessage = function(event) {
        const timeElement = document.getElementById("time");
        if (timeElement) {
            timeElement.textContent = event.data;
        }
    };

    // 监听错误事件（自动重连）
    eventSource.onerror = function() {
        console.error("SSE 连接错误，尝试重新连接...");
        if (eventSource) {
            eventSource.close(); // 关闭旧连接
        }
        setTimeout(connectSSE, 3000);// 3秒后重连
    };
}

// 确保 DOM 加载完成后执行
document.addEventListener("DOMContentLoaded", function() {
    connectSSE();// 页面加载时启动连接
});
//// 页面加载时启动连接
//window.onload = connectSSE;