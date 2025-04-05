// 初始化 SSE 连接
let eventSource;

function connectSSE() {
    // 创建 SSE 连接（指向后端端点）
    eventSource = new EventSource("/sse/time");

    // 监听消息事件
    eventSource.onmessage = function(event) {
        document.getElementById("liveTime").textContent = event.data;
    };

    // 监听错误事件（自动重连）
    eventSource.onerror = function() {
        console.error("SSE 连接错误，尝试重新连接...");
        eventSource.close();  // 关闭旧连接
        setTimeout(connectSSE, 3000);  // 3秒后重连
    };
}

// 页面加载时启动连接
window.onload = connectSSE;















//// 自动刷新逻辑
//function createDynamicElements(data) {
//    const container = document.getElementById('client-status');
//    container.innerHTML = '';  // 清空现有内容
//
//    if (Object.keys(data).length === 0) {
//        container.innerHTML = '<tr><td colspan="3">无客户端在线</td></tr>';
//        return;
//    }
//
//    for (const [key, value] of Object.entries(data)) {
//        const tr1 = document.createElement('tr');
//
//        const td1 = document.createElement('td');
//        td1.className = 'client_ip';
//        td1.textContent = value['ip'];
//
//        const td2 = document.createElement('td');
//        td2.className = 'client_online';
//        td2.id = value['online'];
//
//        const td3 = document.createElement('td');
//        td3.className = 'client_last_heartbeat';
//        td3.id = value['last_heartbeat'];
//
//        tr1.appendChild(td1);
//        tr1.appendChild(td2);
//        tr1.appendChild(td3);
//        container.appendChild(tr1);
//    }
//}
//
//function updateData() {
//    fetch('/api/data')
//        .then(response => response.json())
//        .then(data => createDynamicElements(data))
//        .catch(error => console.error('Error:', error));
//}
//setInterval(updateData, 1000);//每1秒刷新数据
//updateData();
//
//
////
////// 初始化ECharts
////const clientChart = echarts.init(document.getElementById('client-chart'));
////
////function updateClientChart(clients) {
////    const option = {
////        tooltip: { trigger: 'item' },
////        series: [{
////            type: 'pie',
////            data: Object.entries(clients).map(([name, info]) => ({
////                name: `${name} (${info.online ? '在线' : '离线'})`,
////                value: info.online ? 1 : 0
////            }))
////        }]
////    };
////    clientChart.setOption(option);
////}
////
////function updateEventList(events) {
////    const list = document.getElementById('events-list');
////    list.innerHTML = events.map(event => `
////        <div class="event-item">
////            <span class="time">${event.timestamp}</span>
////            <span class="host">${event.host}</span>
////            <span class="type ${event.event_type}">${event.event_type}</span>
////            <span class="path">${event.path}</span>
////        </div>
////    `).join('');
////}