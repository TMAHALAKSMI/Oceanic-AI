/* ═══════════════════════════════════════════════════════
   OceanWatch AI — Frontend Application
   ═══════════════════════════════════════════════════════ */

const API = "http://127.0.0.1:8000";

// ── Label colour palette ────────────────────────────────
const LABEL_COLORS = {
  "Plastic Bottle":      "#0050ff",
  "Plastic Bag":         "#ff8800",
  "Fishing Net":         "#ffdd00",
  "Metal Debris":        "#aaaaaa",
  "Organic Waste":       "#22cc44",
  "Foam/Styrofoam":      "#ffffff",
  "Rope/Twine":          "#ff4444",
  "Unidentified Debris": "#8844ff",
  "Plastic":             "#0088ff",
  "Metal":               "#bbbbbb",
  "Electronic Waste":    "#ff44aa",
};

const CHART_PALETTE = [
  "#00d4ff","#00ff9f","#ffb830","#ff4d6d",
  "#8a4fff","#ff7f50","#44eebb","#ff44aa",
];

/* ══════════════════════════════════════════════════════════
   ANIMATED BACKGROUND
══════════════════════════════════════════════════════════ */
(function initBg() {
  const canvas = document.getElementById("bg-canvas");
  const ctx = canvas.getContext("2d");
  let W, H, particles = [];

  function resize() {
    W = canvas.width  = window.innerWidth;
    H = canvas.height = window.innerHeight;
  }
  resize();
  window.addEventListener("resize", resize);

  for (let i = 0; i < 60; i++) {
    particles.push({
      x: Math.random() * 2000,
      y: Math.random() * 2000,
      r: Math.random() * 1.5 + 0.3,
      speed: Math.random() * 0.3 + 0.05,
      angle: Math.random() * Math.PI * 2,
      opacity: Math.random() * 0.5 + 0.1,
    });
  }

  function draw() {
    ctx.clearRect(0, 0, W, H);
    // Gradient overlay
    const grad = ctx.createRadialGradient(W / 2, H * 0.4, 0, W / 2, H * 0.4, W * 0.7);
    grad.addColorStop(0, "rgba(0, 60, 100, 0.25)");
    grad.addColorStop(1, "rgba(0, 0, 0, 0)");
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, W, H);

    // Floating dots
    particles.forEach(p => {
      p.x += Math.cos(p.angle) * p.speed;
      p.y += Math.sin(p.angle) * p.speed;
      p.angle += 0.005;
      if (p.x < 0) p.x = W; if (p.x > W) p.x = 0;
      if (p.y < 0) p.y = H; if (p.y > H) p.y = 0;

      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(0, 212, 255, ${p.opacity})`;
      ctx.fill();
    });

    // Grid lines
    ctx.strokeStyle = "rgba(0, 80, 120, 0.12)";
    ctx.lineWidth = 1;
    for (let x = 0; x < W; x += 80) {
      ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke();
    }
    for (let y = 0; y < H; y += 80) {
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke();
    }
    requestAnimationFrame(draw);
  }
  draw();
})();

/* ══════════════════════════════════════════════════════════
   NAVIGATION
══════════════════════════════════════════════════════════ */
const navBtns  = document.querySelectorAll(".nav__btn");
const views    = document.querySelectorAll(".view");

navBtns.forEach(btn => {
  btn.addEventListener("click", () => {
    navBtns.forEach(b => b.classList.remove("active"));
    views.forEach(v => v.classList.remove("active"));
    btn.classList.add("active");
    const id = "view-" + btn.dataset.view;
    document.getElementById(id).classList.add("active");
    if (btn.dataset.view === "dashboard") loadDashboard();
  });
});

/* ══════════════════════════════════════════════════════════
   HEALTH CHECK
══════════════════════════════════════════════════════════ */
async function checkHealth() {
  const dot  = document.getElementById("status-dot");
  const text = document.getElementById("status-text");
  try {
    const r = await fetch(`${API}/health`, { signal: AbortSignal.timeout(4000) });
    if (r.ok) {
      const d = await r.json();
      dot.className  = "status-dot online";
      text.textContent = d.detector_ready ? "Model ready" : "Rule-based mode";
    } else throw new Error();
  } catch {
    dot.className  = "status-dot offline";
    text.textContent = "API offline";
  }
}
checkHealth();
setInterval(checkHealth, 30_000);

/* ══════════════════════════════════════════════════════════
   TOAST NOTIFICATIONS
══════════════════════════════════════════════════════════ */
function toast(msg, type = "info", duration = 3500) {
  const wrap = document.getElementById("toast-container");
  const el   = document.createElement("div");
  el.className = `toast toast--${type}`;
  el.textContent = msg;
  wrap.appendChild(el);
  setTimeout(() => {
    el.classList.add("fade-out");
    el.addEventListener("animationend", () => el.remove());
  }, duration);
}

/* ══════════════════════════════════════════════════════════
   LIGHTBOX
══════════════════════════════════════════════════════════ */
function openLightbox(src) {
  const lb = document.getElementById("lightbox");
  document.getElementById("lightbox-img").src = src;
  lb.classList.remove("hidden");
}
document.getElementById("lightbox-backdrop").addEventListener("click", () =>
  document.getElementById("lightbox").classList.add("hidden"));
document.getElementById("lightbox-close").addEventListener("click", () =>
  document.getElementById("lightbox").classList.add("hidden"));

/* ══════════════════════════════════════════════════════════
   DETECT VIEW
══════════════════════════════════════════════════════════ */
const uploadZone  = document.getElementById("upload-zone");
const fileInput   = document.getElementById("file-input");
const progressWrap = document.getElementById("progress-wrap");
const progressBar  = document.getElementById("progress-bar");
const progressLabel = document.getElementById("progress-label");
const resultPanel  = document.getElementById("result-panel");
const uploadCard   = document.getElementById("upload-card");

// Drag & drop
["dragenter","dragover"].forEach(evt =>
  uploadZone.addEventListener(evt, e => { e.preventDefault(); uploadZone.classList.add("drag-over"); }));
["dragleave","drop"].forEach(evt =>
  uploadZone.addEventListener(evt, e => { e.preventDefault(); uploadZone.classList.remove("drag-over"); }));
uploadZone.addEventListener("drop", e => {
  const file = e.dataTransfer.files[0];
  if (file) handleDetect(file);
});
uploadZone.addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", () => fileInput.files[0] && handleDetect(fileInput.files[0]));
document.getElementById("reset-btn").addEventListener("click", resetDetect);

function setProgress(pct, label) {
  progressBar.style.width = pct + "%";
  progressLabel.textContent = label;
}

async function handleDetect(file) {
  if (!file.type.startsWith("image/")) { toast("Please upload an image file", "error"); return; }

  uploadCard.style.display = "none";
  progressWrap.classList.remove("hidden");
  resultPanel.classList.add("hidden");
  setProgress(10, "Uploading image…");

  const formData = new FormData();
  formData.append("file", file);

  try {
    setProgress(30, "Sending to AI engine…");
    const res = await fetch(`${API}/api/detect`, { method: "POST", body: formData });
    setProgress(70, "Running detection…");

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Detection failed");
    }
    const data = await res.json();
    setProgress(95, "Rendering results…");
    await new Promise(r => setTimeout(r, 300));
    setProgress(100, "Done!");

    renderResult(data, file);
  } catch (err) {
    toast("Error: " + err.message, "error");
    progressWrap.classList.add("hidden");
    uploadCard.style.display = "";
  }
}

function renderResult(data, originalFile) {
  progressWrap.classList.add("hidden");
  resultPanel.classList.remove("hidden");

  // Images
  const imgOriginal = document.getElementById("img-original");
  const imgResult   = document.getElementById("img-result");
  imgOriginal.src   = URL.createObjectURL(originalFile);
  imgResult.src     = API + data.result_url;
  imgOriginal.addEventListener("click", () => openLightbox(imgOriginal.src));
  imgResult.addEventListener("click", () => openLightbox(imgResult.src));

  // Stats
  const statsEl = document.getElementById("result-stats");
  const healthPct = Math.round(data.ocean_health_score * 100);
  const healthColor = healthPct > 70 ? "var(--c-clean)" : healthPct > 40 ? "var(--c-warn)" : "var(--c-danger)";
  const wasteList = Object.entries(data.waste_types).map(([k,v]) =>
    `<span class="badge" style="background:${LABEL_COLORS[k]||'#555'}22;color:${LABEL_COLORS[k]||'#aaa'};border:1px solid ${LABEL_COLORS[k]||'#aaa'}33">${v}× ${k}</span>`
  ).join(" ");

  statsEl.innerHTML = `
    <div class="stat-card">
      <div class="stat-card__value ${data.waste_detected ? 'danger' : 'clean'}">${data.total_detections}</div>
      <div class="stat-card__label">Objects Detected</div>
    </div>
    <div class="stat-card">
      <div class="stat-card__value">${(data.confidence_avg * 100).toFixed(1)}%</div>
      <div class="stat-card__label">Avg Confidence</div>
    </div>
    <div class="stat-card">
      <div class="stat-card__value" style="color:${healthColor}">${healthPct}%</div>
      <div class="stat-card__label">Ocean Health Score</div>
      <div class="health-bar-wrap"><div class="health-bar" style="width:${healthPct}%;background:${healthColor}"></div></div>
    </div>
    <div class="stat-card" style="grid-column: span 2">
      <div class="stat-card__label" style="margin-bottom:8px">Detected Categories</div>
      <div style="display:flex;flex-wrap:wrap;gap:6px">${wasteList || '<span style="color:var(--c-clean)">✓ No waste detected</span>'}</div>
    </div>
  `;

  // Table
  const tbody = document.getElementById("detections-tbody");
  if (!data.detections || data.detections.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" class="table-empty">No waste objects detected — ocean appears clean</td></tr>`;
  } else {
    tbody.innerHTML = data.detections.map((d, i) => {
      const color = LABEL_COLORS[d.label] || "#aaa";
      const pct = (d.confidence * 100).toFixed(1);
      return `<tr>
        <td style="font-family:var(--font-mono);color:var(--c-muted)">${i + 1}</td>
        <td><span class="badge" style="background:${color}22;color:${color};border:1px solid ${color}44">${d.label}</span></td>
        <td>
          <div class="conf-bar-wrap">
            <div class="conf-bar"><div class="conf-bar__fill" style="width:${pct}%;background:${color}"></div></div>
            <span class="conf-val">${pct}%</span>
          </div>
        </td>
        <td style="font-family:var(--font-mono);font-size:0.72rem;color:var(--c-muted)">[${d.x1},${d.y1} → ${d.x2},${d.y2}]</td>
        <td style="font-family:var(--font-mono);font-size:0.78rem">${d.area?.toLocaleString() ?? "—"}</td>
      </tr>`;
    }).join("");
  }

  toast(
    data.waste_detected
      ? `⚠ ${data.total_detections} waste object(s) detected`
      : "✓ Ocean appears clean",
    data.waste_detected ? "error" : "success"
  );
}

function resetDetect() {
  resultPanel.classList.add("hidden");
  uploadCard.style.display = "";
  fileInput.value = "";
}

/* ══════════════════════════════════════════════════════════
   DASHBOARD VIEW
══════════════════════════════════════════════════════════ */
let chartInstance = null;
let currentPage   = 0;
const PAGE_SIZE   = 8;

document.getElementById("refresh-history-btn").addEventListener("click", loadDashboard);

async function loadDashboard() {
  await Promise.all([loadStats(), loadHistory(currentPage)]);
}

async function loadStats() {
  try {
    const res = await fetch(`${API}/api/stats`);
    if (!res.ok) return;
    const d = await res.json();

    animateNumber("kpi-total",  d.total_analyses);
    animateNumber("kpi-waste",  d.total_waste_items);
    animateNumber("kpi-conf",   d.avg_confidence, "%");
    animateNumber("kpi-poll",   d.polluted_ocean_pct, "%");
    animateNumber("kpi-clean",  d.clean_ocean_pct, "%");
    document.getElementById("kpi-common").textContent = d.most_common_waste || "N/A";
  } catch {}
}

function animateNumber(id, target, suffix = "") {
  const el = document.getElementById(id);
  if (!el) return;
  let start = 0;
  const step = target / 40;
  const int = setInterval(() => {
    start = Math.min(start + step, target);
    el.textContent = Number.isInteger(target) ? Math.round(start) + suffix : start.toFixed(1) + suffix;
    if (start >= target) clearInterval(int);
  }, 20);
}

async function loadHistory(page = 0) {
  const offset = page * PAGE_SIZE;
  try {
    const res = await fetch(`${API}/api/history?limit=${PAGE_SIZE}&offset=${offset}`);
    if (!res.ok) return;
    const data = await res.json();
    renderHistory(data.records);
    renderPagination(data.total, page);
    updateChart(data.records);
  } catch {}
}

function renderHistory(records) {
  const tbody = document.getElementById("history-tbody");
  if (!records.length) {
    tbody.innerHTML = `<tr><td colspan="8" class="table-empty">No analyses yet. Upload an image to get started.</td></tr>`;
    return;
  }
  tbody.innerHTML = records.map(r => {
    const d   = new Date(r.timestamp);
    const dt  = d.toLocaleDateString() + " " + d.toLocaleTimeString([], {hour:"2-digit", minute:"2-digit"});
    const hp  = Math.round((r.ocean_health_score || 1) * 100);
    const hc  = hp > 70 ? "var(--c-clean)" : hp > 40 ? "var(--c-warn)" : "var(--c-danger)";
    const tag = r.waste_detected
      ? `<span class="tag tag--polluted">Polluted</span>`
      : `<span class="tag tag--clean">Clean</span>`;
    const conf = r.confidence_avg ? (r.confidence_avg * 100).toFixed(1) + "%" : "—";

    return `<tr>
      <td><img class="history-thumb" src="${API}/results/${r.result_path}" alt=""
           onclick="openLightbox('${API}/results/${r.result_path}')" /></td>
      <td style="max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${r.filename}">${r.filename}</td>
      <td style="font-family:var(--font-mono);font-size:0.72rem;color:var(--c-muted)">${dt}</td>
      <td style="font-family:var(--font-mono)">${r.total_detections}</td>
      <td style="font-family:var(--font-mono)">${conf}</td>
      <td>
        <div style="display:flex;align-items:center;gap:6px">
          <div style="flex:1;height:5px;background:rgba(255,255,255,.08);border-radius:99px;overflow:hidden">
            <div style="width:${hp}%;height:100%;background:${hc};border-radius:99px"></div>
          </div>
          <span style="font-family:var(--font-mono);font-size:0.72rem;color:${hc}">${hp}%</span>
        </div>
      </td>
      <td>${tag}</td>
      <td>
        <button class="btn btn--sm btn--ghost" onclick="deleteRecord('${r.id}')">✕</button>
      </td>
    </tr>`;
  }).join("");
}

async function deleteRecord(id) {
  if (!confirm("Delete this analysis record?")) return;
  try {
    const res = await fetch(`${API}/api/detection/${id}`, { method: "DELETE" });
    if (res.ok) { toast("Record deleted", "info"); loadDashboard(); }
  } catch { toast("Delete failed", "error"); }
}

function renderPagination(total, current) {
  const pages = Math.ceil(total / PAGE_SIZE);
  const wrap  = document.getElementById("pagination");
  if (pages <= 1) { wrap.innerHTML = ""; return; }
  wrap.innerHTML = Array.from({length: pages}, (_, i) =>
    `<button class="page-btn${i===current?' active':''}" onclick="gotoPage(${i})">${i+1}</button>`
  ).join("");
}

function gotoPage(p) {
  currentPage = p;
  loadHistory(p);
}

function updateChart(records) {
  const counts = {};
  records.forEach(r => {
    const wt = typeof r.waste_types === "string" ? JSON.parse(r.waste_types) : (r.waste_types || {});
    Object.entries(wt).forEach(([k, v]) => { counts[k] = (counts[k] || 0) + v; });
  });

  const labels = Object.keys(counts);
  const values = Object.values(counts);

  if (typeof Chart === "undefined" || !labels.length) {
    document.getElementById("chart-legend").innerHTML = "<p style='color:var(--c-muted);font-size:.8rem'>No data yet</p>";
    return;
  }

  const canvas = document.getElementById("waste-chart");
  if (chartInstance) chartInstance.destroy();
  chartInstance = new Chart(canvas, {
    type: "doughnut",
    data: {
      labels,
      datasets: [{
        data: values,
        backgroundColor: labels.map((_, i) => CHART_PALETTE[i % CHART_PALETTE.length] + "cc"),
        borderColor:     labels.map((_, i) => CHART_PALETTE[i % CHART_PALETTE.length]),
        borderWidth: 1.5,
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false }, tooltip: { callbacks: {
        label: ctx => ` ${ctx.label}: ${ctx.parsed} items`
      }}},
      cutout: "68%",
    }
  });

  const total = values.reduce((a, b) => a + b, 0);
  document.getElementById("chart-legend").innerHTML = labels.map((l, i) => {
    const pct = total ? ((values[i] / total) * 100).toFixed(1) : 0;
    return `<div class="legend-row">
      <div class="legend-dot" style="background:${CHART_PALETTE[i % CHART_PALETTE.length]}"></div>
      <span>${l}</span>
      <span class="legend-pct">${pct}%</span>
    </div>`;
  }).join("");
}

// Load Chart.js dynamically
const chartScript = document.createElement("script");
chartScript.src = "https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js";
chartScript.onload = () => { if (document.getElementById("view-dashboard").classList.contains("active")) loadDashboard(); };
document.head.appendChild(chartScript);

/* ══════════════════════════════════════════════════════════
   COMPARE VIEW
══════════════════════════════════════════════════════════ */
let cleanFile = null, pollutedFile = null;

function setupCompareSlot(inputId, previewId, dropId, onFile) {
  const input   = document.getElementById(inputId);
  const preview = document.getElementById(previewId);
  const drop    = document.getElementById(dropId);

  input.addEventListener("change", () => input.files[0] && onFile(input.files[0]));
  drop.addEventListener("click",   () => input.click());
  drop.addEventListener("dragover",  e => { e.preventDefault(); drop.style.borderColor = "var(--c-accent)"; });
  drop.addEventListener("dragleave", () => { drop.style.borderColor = ""; });
  drop.addEventListener("drop",      e => { e.preventDefault(); drop.style.borderColor = ""; const f = e.dataTransfer.files[0]; if (f) onFile(f); });

  function handle(file) {
    drop.style.display = "none";
    preview.src = URL.createObjectURL(file);
    preview.classList.remove("hidden");
    onFile(file);
  }
  input.addEventListener("change", () => input.files[0] && handle(input.files[0]));
  drop.addEventListener("click", () => input.click());
  drop.addEventListener("drop", e => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) handle(f); });
}

document.getElementById("compare-clean-input").addEventListener("change", function() {
  if (this.files[0]) { cleanFile = this.files[0]; updateCompareBtn(); previewCompare("compare-clean-drop", "compare-clean-preview", cleanFile); }
});
document.getElementById("compare-polluted-input").addEventListener("change", function() {
  if (this.files[0]) { pollutedFile = this.files[0]; updateCompareBtn(); previewCompare("compare-polluted-drop", "compare-polluted-preview", pollutedFile); }
});
document.getElementById("compare-clean-drop").addEventListener("click", () => document.getElementById("compare-clean-input").click());
document.getElementById("compare-polluted-drop").addEventListener("click", () => document.getElementById("compare-polluted-input").click());

function previewCompare(dropId, previewId, file) {
  document.getElementById(dropId).style.display = "none";
  const p = document.getElementById(previewId);
  p.src = URL.createObjectURL(file);
  p.classList.remove("hidden");
}
function updateCompareBtn() {
  document.getElementById("compare-btn").disabled = !(cleanFile && pollutedFile);
}

document.getElementById("compare-btn").addEventListener("click", async () => {
  if (!cleanFile || !pollutedFile) return;
  const btn = document.getElementById("compare-btn");
  btn.textContent = "Processing…"; btn.disabled = true;
  try {
    const fd = new FormData();
    fd.append("clean_image", cleanFile);
    fd.append("polluted_image", pollutedFile);
    const res = await fetch(`${API}/api/compare`, { method: "POST", body: fd });
    if (!res.ok) throw new Error("Compare failed");
    const data = await res.json();

    const result = document.getElementById("compare-result");
    result.classList.remove("hidden");
    document.getElementById("compare-output").src = API + data.comparison_url;
    document.getElementById("compare-summary").innerHTML =
      `Detected <strong>${data.detections}</strong> waste object(s) in polluted image. ` +
      (data.detections > 0
        ? `Categories: ${Object.keys(data.waste_types).join(", ")}`
        : "No waste detected.");
    toast("Comparison generated", "success");
  } catch (e) {
    toast("Error: " + e.message, "error");
  } finally {
    btn.textContent = "Generate Comparison →"; btn.disabled = false;
    updateCompareBtn();
  }
});

/* ══════════════════════════════════════════════════════════
   THERMAL VIEW
══════════════════════════════════════════════════════════ */
const thermalZone  = document.getElementById("thermal-zone");
const thermalInput = document.getElementById("thermal-input");

thermalZone.addEventListener("click",    () => thermalInput.click());
thermalZone.addEventListener("dragover", e => { e.preventDefault(); thermalZone.classList.add("drag-over"); });
thermalZone.addEventListener("dragleave",() => thermalZone.classList.remove("drag-over"));
thermalZone.addEventListener("drop",     e => { e.preventDefault(); thermalZone.classList.remove("drag-over"); const f = e.dataTransfer.files[0]; if (f) handleThermal(f); });
thermalInput.addEventListener("change",  () => thermalInput.files[0] && handleThermal(thermalInput.files[0]));

async function handleThermal(file) {
  toast("Generating thermal simulation…", "info");
  const fd = new FormData();
  fd.append("file", file);
  try {
    const res = await fetch(`${API}/api/thermal`, { method: "POST", body: fd });
    if (!res.ok) throw new Error("Thermal processing failed");
    const data = await res.json();
    document.getElementById("thermal-original").src = URL.createObjectURL(file);
    document.getElementById("thermal-output").src   = API + data.thermal_url;
    document.getElementById("thermal-result").classList.remove("hidden");
    toast("Thermal simulation complete", "success");
  } catch (e) {
    toast("Error: " + e.message, "error");
  }
}
