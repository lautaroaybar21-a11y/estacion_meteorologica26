const state = {
  page: 1,
  pages: 0,
  chart: null,
  chartData: [],
  activeMetric: "temperatura_bmp",
};

const numberFormat = new Intl.NumberFormat("es-AR", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const dateFormat = new Intl.DateTimeFormat("es-AR", {
  dateStyle: "medium",
  timeStyle: "medium",
});

const metrics = {
  temperatura_bmp: {
    label: "Temperatura BMP",
    color: "#de7754",
    unit: "°C",
  },
  temperatura_dht: {
    label: "Temperatura DHT",
    color: "#9677c7",
    unit: "°C",
  },
  humedad_aire: {
    label: "Humedad del aire",
    color: "#5497a5",
    unit: "%",
  },
  humedad_suelo_pct: {
    label: "Humedad del suelo",
    color: "#78976a",
    unit: "%",
  },
  presion_hpa: {
    label: "Presión atmosférica",
    color: "#c59b4f",
    unit: "hPa",
  },
};

function formatValue(value, suffix = "") {
  return value == null ? "--" : `${numberFormat.format(Number(value))}${suffix}`;
}

function parseDate(value) {
  return new Date(value.replace(" ", "T"));
}

function formatDate(value) {
  return dateFormat.format(parseDate(value));
}

async function fetchJson(url) {
  const response = await fetch(url);
  const body = await response.json();
  if (!response.ok) {
    throw new Error(body.error || "No se pudieron cargar los datos.");
  }
  return body;
}

function setDatabaseStatus(connected) {
  const status = document.getElementById("database-status");
  status.classList.toggle("is-offline", !connected);
  status.querySelector(".status-label").textContent = connected
    ? "MySQL conectado"
    : "MySQL sin conexión";
}

function updateCurrentReadings(reading) {
  const values = {
    "current-temperature-bmp": formatValue(reading?.temperatura_bmp, "°"),
    "current-temperature-dht": formatValue(reading?.temperatura_dht, "°"),
    "current-air-humidity": formatValue(reading?.humedad_aire, "%"),
    "current-pressure": formatValue(reading?.presion_hpa),
    "current-soil-humidity": formatValue(reading?.humedad_suelo_pct, "%"),
    "current-soil-raw": reading
      ? `RAW: ${reading.humedad_suelo_raw}`
      : "RAW: --",
  };
  for (const [id, value] of Object.entries(values)) {
    document.getElementById(id).textContent = value;
  }
  document.getElementById("last-updated").textContent = reading
    ? `Última lectura · ${formatDate(reading.medido_en)}`
    : "Todavía no hay lecturas";
}

function renderChart() {
  const message = document.getElementById("chart-message");
  const container = document.getElementById("chart-container");
  const footer = document.getElementById("chart-footer");
  const config = metrics[state.activeMetric];

  if (state.chart) {
    state.chart.destroy();
    state.chart = null;
  }

  if (state.chartData.length === 0) {
    container.hidden = true;
    footer.hidden = true;
    message.hidden = false;
    message.textContent =
      "Aún no hay mediciones en este período. Conectá la placa y las lecturas aparecerán aquí.";
    return;
  }

  if (typeof Chart === "undefined") {
    container.hidden = true;
    footer.hidden = true;
    message.hidden = false;
    message.textContent =
      "No se pudo cargar el componente del gráfico. Verificá la conexión a Internet.";
    return;
  }

  message.hidden = true;
  container.hidden = false;
  footer.hidden = false;

  const canvas = document.getElementById("measurements-chart");
  const context = canvas.getContext("2d");
  const gradient = context.createLinearGradient(0, 0, 0, 300);
  gradient.addColorStop(0, `${config.color}35`);
  gradient.addColorStop(1, `${config.color}00`);

  state.chart = new Chart(canvas, {
    type: "line",
    data: {
      labels: state.chartData.map((item) => formatDate(item.medido_en)),
      datasets: [
        {
          label: config.label,
          data: state.chartData.map((item) => item[state.activeMetric]),
          borderColor: config.color,
          backgroundColor: gradient,
          borderWidth: 2.5,
          pointRadius: state.chartData.length > 50 ? 0 : 3,
          pointHoverRadius: 5,
          pointBackgroundColor: "#fff",
          pointBorderWidth: 2,
          fill: true,
          tension: 0.32,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { intersect: false, mode: "index" },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: "#25332b",
          padding: 12,
          displayColors: false,
          callbacks: {
            title: (items) => (items.length ? items[0].label : ""),
            label: (item) =>
              `${config.label}: ${formatValue(item.raw, ` ${config.unit}`)}`,
          },
        },
      },
      scales: {
        x: {
          grid: { display: false },
          border: { display: false },
          ticks: { color: "#89928c", maxRotation: 0 },
        },
        y: {
          title: {
            display: true,
            text: config.unit,
            color: "#89928c",
            font: { family: "inherit", size: 11 },
          },
          grid: { color: "#edf0eb" },
          border: { display: false },
          ticks: { color: "#89928c", maxTicksLimit: 6 },
        },
      },
    },
  });

  document.getElementById("chart-series-label").textContent = config.label;
  document.getElementById("chart-points").textContent =
    `${state.chartData.length} ${state.chartData.length === 1 ? "lectura" : "lecturas"}`;
}

async function loadCharts() {
  try {
    const period = document.getElementById("periodo").value;
    const result = await fetchJson(
      `/api/mediciones/grafico?periodo=${encodeURIComponent(period)}`,
    );
    state.chartData = result.mediciones;
    renderChart();
  } catch (error) {
    state.chartData = [];
    const message = document.getElementById("chart-message");
    message.hidden = false;
    message.textContent = error.message;
    document.getElementById("chart-container").hidden = true;
    document.getElementById("chart-footer").hidden = true;
    if (error.message.includes("conectar a MySQL")) {
      setDatabaseStatus(false);
    }
  }
}

function addCell(row, value, className = "") {
  const cell = document.createElement("td");
  cell.textContent = value;
  if (className) {
    cell.className = className;
  }
  row.appendChild(cell);
}

async function loadHistory() {
  const message = document.getElementById("history-message");
  const body = document.getElementById("measurements-body");
  message.hidden = true;

  try {
    const result = await fetchJson(`/api/mediciones?pagina=${state.page}`);
    setDatabaseStatus(true);
    updateCurrentReadings(result.ultima);
    body.replaceChildren();
    result.mediciones.forEach((item) => {
      const row = document.createElement("tr");
      addCell(row, formatDate(item.medido_en), "date-cell");
      addCell(row, formatValue(item.temperatura_bmp, " °C"));
      addCell(row, formatValue(item.temperatura_dht, " °C"));
      addCell(row, formatValue(item.humedad_aire, " %"));
      addCell(row, formatValue(item.presion_hpa, " hPa"));
      addCell(row, String(item.humedad_suelo_raw));
      addCell(row, formatValue(item.humedad_suelo_pct, " %"));
      body.appendChild(row);
    });

    state.pages = result.paginas;
    document.getElementById("history-count").textContent =
      `${result.total} ${result.total === 1 ? "medición registrada" : "mediciones registradas"}`;
    document.getElementById("page-label").textContent =
      `Página ${result.pagina} de ${Math.max(result.paginas, 1)}`;
    document.getElementById("previous-page").disabled = state.page <= 1;
    document.getElementById("next-page").disabled =
      state.page >= result.paginas;
    if (result.total === 0) {
      message.textContent =
        "No hay mediciones guardadas todavía. Al conectar el puerto serial, cada lectura se agregará aquí automáticamente.";
      message.hidden = false;
    }
  } catch (error) {
    message.textContent = error.message;
    message.hidden = false;
    document.getElementById("history-count").textContent = "";
    updateCurrentReadings(null);
    if (error.message.includes("conectar a MySQL")) {
      setDatabaseStatus(false);
    }
  }
}

document.getElementById("periodo").addEventListener("change", loadCharts);
document.getElementById("refresh-button").addEventListener("click", () => {
  loadHistory();
  loadCharts();
});
document.getElementById("metric-selector").addEventListener("click", (event) => {
  const button = event.target.closest("[data-metric]");
  if (!button) {
    return;
  }

  state.activeMetric = button.dataset.metric;
  document.querySelectorAll(".metric-button").forEach((item) => {
    const selected = item === button;
    item.classList.toggle("is-active", selected);
    item.setAttribute("aria-pressed", String(selected));
  });
  renderChart();
});
document.getElementById("previous-page").addEventListener("click", () => {
  if (state.page > 1) {
    state.page -= 1;
    loadHistory();
  }
});
document.getElementById("next-page").addEventListener("click", () => {
  if (state.page < state.pages) {
    state.page += 1;
    loadHistory();
  }
});

loadHistory();
loadCharts();
window.setInterval(() => {
  loadHistory();
  loadCharts();
}, 30000);
