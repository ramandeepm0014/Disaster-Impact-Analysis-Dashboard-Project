const chartStore = {};
let map;
let markersLayer;

const ids = ["country", "city", "type", "severity", "start_year", "end_year"];
const getFilters = () => {
    const params = new URLSearchParams();
    ids.forEach(id => params.append(id, document.getElementById(id).value));
    return params.toString();
};

async function fetchJSON(url) {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`Request failed: ${url}`);
    return await response.json();
}

function makeChart(id, type, labels, values, label) {
    const ctx = document.getElementById(id);
    if (chartStore[id]) chartStore[id].destroy();

    chartStore[id] = new Chart(ctx, {
        type,
        data: {
            labels,
            datasets: [{
                label,
                data: values,
                borderWidth: 2,
                tension: 0.35,
                fill: type === "line",
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: "#dce9ff" } },
                tooltip: {
                    callbacks: {
                        label: context => `${context.dataset.label}: ${Number(context.raw).toLocaleString()}`
                    }
                }
            },
            scales: type === "doughnut" ? {} : {
                x: { ticks: { color: "#9fb0ca" }, grid: { color: "rgba(255,255,255,0.06)" } },
                y: { ticks: { color: "#9fb0ca" }, grid: { color: "rgba(255,255,255,0.06)" } }
            }
        }
    });
}

async function updateSummary() {
    const data = await fetchJSON(`/api/summary?${getFilters()}`);
    Object.entries(data).forEach(([key, value]) => {
        const el = document.getElementById(key);
        if (el) el.textContent = value;
    });
}

async function updateCharts() {
    const c = await fetchJSON(`/api/charts?${getFilters()}`);
    makeChart("yearlyDamageChart", "line", c.yearly_damage.labels, c.yearly_damage.values, "Economic Damage USD Millions");
    makeChart("typeChart", "bar", c.disaster_count_by_type.labels, c.disaster_count_by_type.values, "Disaster Count");
    makeChart("severityChart", "doughnut", c.severity_count.labels, c.severity_count.values, "Severity Count");
    makeChart("deathsChart", "bar", c.deaths_by_type.labels, c.deaths_by_type.values, "Deaths");
    makeChart("cityChart", "bar", c.affected_by_city.labels, c.affected_by_city.values, "Affected Population");
    makeChart("fundingGapChart", "bar", c.funding_gap_by_type.labels, c.funding_gap_by_type.values, "Funding Gap USD Millions");
}

function initMap() {
    map = L.map("map").setView([22.9734, 78.6569], 5);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 18,
        attribution: "&copy; OpenStreetMap contributors"
    }).addTo(map);
    markersLayer = L.layerGroup().addTo(map);
}

async function updateMap() {
    if (!map) initMap();
    markersLayer.clearLayers();
    const data = await fetchJSON(`/api/map?${getFilters()}`);
    const bounds = [];

    data.forEach(item => {
        const radius = Math.max(5, Math.min(28, item.affected / 450000));
        const marker = L.circleMarker([item.lat, item.lon], {
            radius,
            fillOpacity: 0.65,
            opacity: 0.95,
            weight: 1
        }).bindPopup(`
            <strong>${item.city}, ${item.country}</strong><br>
            Type: ${item.type}<br>
            Severity: ${item.severity}<br>
            Deaths: ${item.deaths.toLocaleString()}<br>
            Affected: ${item.affected.toLocaleString()}
        `);
        marker.addTo(markersLayer);
        bounds.push([item.lat, item.lon]);
    });

    if (bounds.length > 0) map.fitBounds(bounds, { padding: [30, 30] });
}

async function updateTable() {
    const rows = await fetchJSON(`/api/records?${getFilters()}`);
    const table = document.getElementById("recordsTable");
    if (!rows.length) {
        table.innerHTML = "<tr><td>No records found for selected filters.</td></tr>";
        return;
    }

    const headers = Object.keys(rows[0]);
    const thead = `<thead><tr>${headers.map(h => `<th>${h}</th>`).join("")}</tr></thead>`;
    const tbody = `<tbody>${rows.map(row => `<tr>${headers.map(h => `<td>${formatCell(row[h])}</td>`).join("")}</tr>`).join("")}</tbody>`;
    table.innerHTML = thead + tbody;
}

function formatCell(value) {
    if (typeof value === "number") return Number(value).toLocaleString();
    return value ?? "";
}

async function refreshDashboard() {
    await Promise.all([updateSummary(), updateCharts(), updateMap(), updateTable()]);
}

ids.forEach(id => document.getElementById(id).addEventListener("change", refreshDashboard));

document.getElementById("resetBtn").addEventListener("click", () => {
    document.getElementById("country").value = "All";
    document.getElementById("city").value = "All";
    document.getElementById("type").value = "All";
    document.getElementById("severity").value = "All";
    document.getElementById("start_year").value = document.getElementById("start_year").min;
    document.getElementById("end_year").value = document.getElementById("end_year").max;
    refreshDashboard();
});

refreshDashboard();
