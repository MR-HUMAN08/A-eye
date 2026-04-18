const chartCache = new Map();

const defaultTextColor = "#94A3B8";
const gridColor = "rgba(148, 163, 184, 0.08)";

function cleanChart(key) {
  if (chartCache.has(key)) {
    chartCache.get(key).destroy();
    chartCache.delete(key);
  }
}

function baseOptions() {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { labels: { color: defaultTextColor } },
      tooltip: { enabled: true },
    },
    scales: {
      x: { ticks: { color: defaultTextColor }, grid: { color: gridColor } },
      y: { ticks: { color: defaultTextColor }, grid: { color: gridColor } },
    },
  };
}

export function renderDonut(id, labels, data, colors) {
  const canvas = document.getElementById(id);
  if (!canvas) return;
  cleanChart(id);
  const chart = new Chart(canvas, {
    type: "doughnut",
    data: { labels, datasets: [{ data, backgroundColor: colors, borderWidth: 0 }] },
    options: {
      animation: { animateRotate: true, duration: 900 },
      plugins: {
        legend: { labels: { color: defaultTextColor } },
        tooltip: {
          callbacks: {
            label: (ctx) => {
              const total = data.reduce((sum, val) => sum + val, 0) || 1;
              const pct = ((ctx.parsed / total) * 100).toFixed(1);
              return `${ctx.label}: Rs ${ctx.parsed.toLocaleString()} (${pct}% of income)`;
            },
          },
        },
      },
    },
  });
  chartCache.set(id, chart);
}

export function renderLine(id, labels, datasets) {
  const canvas = document.getElementById(id);
  if (!canvas) return;
  cleanChart(id);
  const chart = new Chart(canvas, {
    type: "line",
    data: { labels, datasets },
    options: baseOptions(),
  });
  chartCache.set(id, chart);
}

export function renderBar(id, labels, datasets) {
  const canvas = document.getElementById(id);
  if (!canvas) return;
  cleanChart(id);
  const chart = new Chart(canvas, {
    type: "bar",
    data: { labels, datasets },
    options: baseOptions(),
  });
  chartCache.set(id, chart);
}

export function renderPie(id, labels, data, colors) {
  const canvas = document.getElementById(id);
  if (!canvas) return;
  cleanChart(id);
  const chart = new Chart(canvas, {
    type: "pie",
    data: { labels, datasets: [{ data, backgroundColor: colors, borderWidth: 0 }] },
    options: {
      plugins: {
        legend: { labels: { color: defaultTextColor } },
      },
    },
  });
  chartCache.set(id, chart);
}
