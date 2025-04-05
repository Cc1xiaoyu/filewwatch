// SSE 连接管理逻辑 初始化 SSE 连接
let eventSource;

function connectSSE() {
    // 创建 SSE 连接（指向后端端点）
    eventSource = new EventSource("/sse/data");

    // 监听消息事件，并显示到网页
    eventSource.onmessage = function(event) {
        console.log("SSE 数据接收成功",event.data);
        try{
//            const data=JSON.parse(event.data);
            const data = JSON.parse(event.data);
            updateData(data);
        }
        catch(err){
            console.error("SSE 数据解析失败",err);
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

function updateData(data){
    //更新时间
    document.getElementById("timestamp").textContent=data['timestamp'];
    //更新业务数据：客户端状态
    const client_container=document.getElementById("client_list");
    client_container.innerHTML="";//清空旧内容

    Object.entries(data['clients_activeStatus']).forEach(([clientId, info]) => {//遍历data中的键值对
        const card = document.createElement("div");
        card.className = `client-card ${info.online ? "" : "offline"}`;//根据是否在线 选择classname

        card.innerHTML = `
            <h3>
                <span class="status-indicator ${info.online ? "status-online" : "status-offline"}"></span>
                ${info.hostname}
            </h3>
            <p>IP: ${info.ip}</p>
            <p>最后活跃: ${new Date(info.last_seen).toLocaleString()}</p>
            <p>状态: ${info.online ? "在线" : "离线"}</p>
        `;

        client_container.appendChild(card);//加入标签
    });

}



// 确保 DOM 加载完成后执行
document.addEventListener("DOMContentLoaded", function() {
    connectSSE();// 页面加载时启动连接
});
//// 页面加载时启动连接
//window.onload = connectSSE;