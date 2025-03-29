// 初始化ECharts
const clientChart = echarts.init(document.getElementById('client-chart'));

// SSE实时连接
const eventSource = new EventSource('/sse/updates');

eventSource.onmessage = (e) => {
    const data = JSON.parse(e.data);
    updateClientChart(data.clients);
    updateEventList(data.recent_events);
};

function updateClientChart(clients) {
    const option = {
        tooltip: { trigger: 'item' },
        series: [{
            type: 'pie',
            data: Object.entries(clients).map(([name, info]) => ({
                name: `${name} (${info.online ? '在线' : '离线'})`,
                value: info.online ? 1 : 0
            }))
        }]
    };
    clientChart.setOption(option);
}

function updateEventList(events) {
    const list = document.getElementById('events-list');
    list.innerHTML = events.map(event => `
        <div class="event-item">
            <span class="time">${event.timestamp}</span>
            <span class="host">${event.host}</span>
            <span class="type ${event.event_type}">${event.event_type}</span>
            <span class="path">${event.path}</span>
        </div>
    `).join('');
}