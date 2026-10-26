// DataQuality.ai Single-Page Application Client Logic

let currentDatasetId = null;
let currentRunId = null;
let eventSource = null;

// DOM Elements
const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("fileInput");
const datasetDetails = document.getElementById("datasetDetails");
const datasetName = document.getElementById("datasetName");
const datasetStats = document.getElementById("datasetStats");
const previewHead = document.getElementById("previewHead");
const previewBody = document.getElementById("previewBody");
const maxIterSelect = document.getElementById("maxIterSelect");
const startRunBtn = document.getElementById("startRunBtn");

const pipelineSection = document.getElementById("pipelineSection");
const pipelineStatusText = document.getElementById("pipelineStatusText");
const activeIterationBadge = document.getElementById("activeIterationBadge");

const resultsSection = document.getElementById("resultsSection");
const initialScoreNum = document.getElementById("initialScoreNum");
const finalScoreNum = document.getElementById("finalScoreNum");
const scoreDeltaBadge = document.getElementById("scoreDeltaBadge");
const scoreComponentsList = document.getElementById("scoreComponentsList");

const narrativeSummary = document.getElementById("narrativeSummary");
const narrativeDecisions = document.getElementById("narrativeDecisions");
const manualChecksList = document.getElementById("manualChecksList");

const issuesTableBody = document.getElementById("issuesTableBody");
const issuesCount = document.getElementById("issuesCount");
const logTableBody = document.getElementById("logTableBody");
const opsCount = document.getElementById("opsCount");
const chartsGrid = document.getElementById("chartsGrid");

const downloadCsvBtn = document.getElementById("downloadCsvBtn");
const downloadXlsxBtn = document.getElementById("downloadXlsxBtn");
const cleanedHead = document.getElementById("cleanedHead");
const cleanedBody = document.getElementById("cleanedBody");

const themeToggleBtn = document.getElementById("themeToggleBtn");
const sunIcon = document.getElementById("sunIcon");
const moonIcon = document.getElementById("moonIcon");

const runsDrawerBtn = document.getElementById("runsDrawerBtn");
const runsDrawer = document.getElementById("runsDrawer");
const drawerBackdrop = document.getElementById("drawerBackdrop");
const closeDrawerBtn = document.getElementById("closeDrawerBtn");
const runsHistoryList = document.getElementById("runsHistoryList");
const runsCountBadge = document.getElementById("runsCountBadge");

// ========================
// 1. Theme Management
// ========================
function initTheme() {
  const savedTheme = localStorage.getItem("theme") || "dark";
  document.documentElement.setAttribute("data-theme", savedTheme);
  updateThemeIcons(savedTheme);
}

function updateThemeIcons(theme) {
  if (theme === "dark") {
    sunIcon.style.display = "none";
    moonIcon.style.display = "block";
  } else {
    sunIcon.style.display = "block";
    moonIcon.style.display = "none";
  }
}

themeToggleBtn.addEventListener("click", () => {
  const current = document.documentElement.getAttribute("data-theme");
  const next = current === "dark" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", next);
  localStorage.setItem("theme", next);
  updateThemeIcons(next);
});

// ========================
// 2. Upload & Sample Data
// ========================
dropzone.addEventListener("click", () => fileInput.click());

dropzone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropzone.classList.add("dragover");
});

dropzone.addEventListener("dragleave", () => {
  dropzone.classList.remove("dragover");
});

dropzone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropzone.classList.remove("dragover");
  if (e.dataTransfer.files && e.dataTransfer.files[0]) {
    uploadFile(e.dataTransfer.files[0]);
  }
});

fileInput.addEventListener("change", (e) => {
  if (e.target.files && e.target.files[0]) {
    uploadFile(e.target.files[0]);
  }
});

async function uploadFile(file) {
  const formData = new FormData();
  formData.append("file", file);

  try {
    dropzone.style.opacity = "0.5";
    const res = await fetch("/api/datasets/upload", {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Upload failed");
    }

    const data = await res.json();
    handleDatasetLoaded(data);
  } catch (err) {
    alert("Error uploading file: " + err.message);
  } finally {
    dropzone.style.opacity = "1";
    fileInput.value = "";
  }
}

// Sample buttons
document.querySelectorAll(".btn-sample").forEach((btn) => {
  btn.addEventListener("click", async (e) => {
    e.stopPropagation();
    const sample = btn.getAttribute("data-sample");
    try {
      btn.textContent = "Loading...";
      const res = await fetch(`/api/datasets/load-sample?sample_name=${sample}`, {
        method: "POST",
      });
      if (!res.ok) throw new Error("Failed to load sample dataset");
      const data = await res.json();
      handleDatasetLoaded(data);
    } catch (err) {
      alert(err.message);
    } finally {
      btn.textContent = `⚡ Messy ${sample.charAt(0).toUpperCase() + sample.slice(1)}`;
    }
  });
});

function handleDatasetLoaded(data) {
  currentDatasetId = data.dataset_id;
  datasetName.textContent = data.filename;
  datasetStats.textContent = `${data.rows} rows · ${data.columns} cols · ${(data.file_size_bytes / 1024).toFixed(1)} KB`;
  datasetDetails.style.display = "block";
  resultsSection.style.display = "none";
  pipelineSection.style.display = "none";

  renderTable(previewHead, previewBody, data.column_names, data.preview);
}

function renderTable(headEl, bodyEl, columns, rows) {
  headEl.innerHTML = `<tr>${columns.map((c) => `<th>${c}</th>`).join("")}</tr>`;
  bodyEl.innerHTML = rows
    .map(
      (r) =>
        `<tr>${columns
          .map((c) => {
            const val = r[c];
            return `<td>${val === null || val === undefined ? '<span style="color:var(--text-muted);font-style:italic;">null</span>' : val}</td>`;
          })
          .join("")}</tr>`
    )
    .join("");
}

// ========================
// 3. Pipeline Execution & SSE
// ========================
const STAGE_ORDER = ["profiler", "detector", "planner", "cleaner", "validator", "reporter"];

startRunBtn.addEventListener("click", async () => {
  if (!currentDatasetId) return;

  const maxIter = parseInt(maxIterSelect.value) || 3;
  startRunBtn.disabled = true;
  startRunBtn.innerHTML = `<div class="spinner"></div> Running Agents...`;

  try {
    const res = await fetch("/api/runs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ dataset_id: currentDatasetId, max_iterations: maxIter }),
    });

    if (!res.ok) throw new Error("Failed to initiate run");
    const data = await res.json();
    currentRunId = data.run_id;

    // Reset UI for execution
    pipelineSection.style.display = "block";
    resultsSection.style.display = "none";
    STAGE_ORDER.forEach((s) => {
      const el = document.getElementById(`step-${s}`);
      el.className = "timeline-step";
    });

    listenToStream(currentRunId);
    refreshHistoryList();
  } catch (err) {
    alert("Error starting pipeline: " + err.message);
    startRunBtn.disabled = false;
    startRunBtn.innerHTML = `<span>Start Autonomous Pipeline</span>`;
  }
});

function listenToStream(runId) {
  if (eventSource) eventSource.close();

  eventSource = new EventSource(`/api/runs/${runId}/stream`);

  eventSource.addEventListener("progress", (e) => {
    const data = JSON.parse(e.data);
    updatePipelineUI(data.stage, data.iteration, data.message);
  });

  eventSource.addEventListener("complete", async (e) => {
    eventSource.close();
    pipelineStatusText.textContent = "Pipeline completed successfully.";
    STAGE_ORDER.forEach((s) => {
      document.getElementById(`step-${s}`).className = "timeline-step completed";
    });
    startRunBtn.disabled = false;
    startRunBtn.innerHTML = `<span>Start Autonomous Pipeline</span>`;

    await loadRunResults(runId);
  });

  eventSource.addEventListener("error", (e) => {
    eventSource.close();
    pipelineStatusText.textContent = "Error during execution. Inspect logs.";
    startRunBtn.disabled = false;
    startRunBtn.innerHTML = `<span>Start Autonomous Pipeline</span>`;
  });
}

function updatePipelineUI(currentStage, iteration, msg) {
  pipelineStatusText.textContent = msg || `Agent '${currentStage}' executing...`;
  activeIterationBadge.textContent = `Iteration ${iteration}`;

  let stageFound = false;
  STAGE_ORDER.forEach((s) => {
    const el = document.getElementById(`step-${s}`);
    if (s === currentStage) {
      el.className = "timeline-step active";
      stageFound = true;
    } else if (!stageFound) {
      el.className = "timeline-step completed";
    } else {
      el.className = "timeline-step";
    }
  });
}

// ========================
// 4. Results & Dashboard
// ========================
async function loadRunResults(runId) {
  try {
    const [reportRes, logRes, issuesRes] = await Promise.all([
      fetch(`/api/runs/${runId}/report`),
      fetch(`/api/runs/${runId}/log`),
      fetch(`/api/runs/${runId}/issues`),
    ]);

    if (!reportRes.ok) throw new Error("Could not fetch final report");

    const report = await reportRes.json();
    const logs = logRes.ok ? await logRes.json() : [];
    const issues = issuesRes.ok ? await issuesRes.json() : [];

    displayReportDashboard(runId, report, logs, issues);
  } catch (err) {
    console.error("Error loading results:", err);
  }
}

function displayReportDashboard(runId, report, logs, issues) {
  resultsSection.style.display = "block";

  // Score Hero
  initialScoreNum.textContent = Number(report.initial_score).toFixed(1);
  finalScoreNum.textContent = Number(report.final_score).toFixed(1);
  const delta = Number(report.score_improvement);
  scoreDeltaBadge.textContent = `${delta >= 0 ? "+" : ""}${delta.toFixed(1)} pts`;

  // Dimension breakdown
  const comp = report.score_components || {};
  scoreComponentsList.innerHTML = Object.entries(comp)
    .map(
      ([key, val]) => `
      <div style="background: var(--bg-surface); padding: 8px 10px; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle); display: flex; justify-content: space-between;">
        <span style="text-transform: capitalize; color: var(--text-secondary);">${key.replace("_", " ")}</span>
        <span style="font-weight: 600; font-family: var(--font-mono);">${Number(val).toFixed(0)}%</span>
      </div>`
    )
    .join("");

  // Narrative
  narrativeSummary.textContent = report.executive_summary || "Automated cleaning pipeline completed.";
  narrativeDecisions.textContent = report.decisions_explanation || "Applied rule-based standardization and median imputation.";
  manualChecksList.innerHTML = (report.recommended_manual_checks || [])
    .map((check) => `<li>${check}</li>`)
    .join("");

  // Issues Table
  issuesCount.textContent = issues.length;
  issuesTableBody.innerHTML = issues
    .map((i) => {
      const sevClass = `badge-${i.severity || "medium"}`;
      return `
      <tr>
        <td><span class="badge ${sevClass}">${(i.severity || "medium").toUpperCase()}</span></td>
        <td><code>${i.column || "Dataset-Level"}</code></td>
        <td>${i.issue_type}</td>
        <td>${i.description}</td>
        <td>${i.affected_count || 0}</td>
        <td><small style="color:var(--text-secondary);">${(i.examples || []).slice(0, 3).join(", ") || "-"}</small></td>
      </tr>`;
    })
    .join("");

  // Operations Log Table
  opsCount.textContent = logs.length;
  logTableBody.innerHTML = logs
    .map((l) => `
      <tr>
        <td><span class="badge ${l.status === "success" ? "badge-low" : "badge-critical"}">${l.status.toUpperCase()}</span></td>
        <td><code>${l.column || "-"}</code></td>
        <td>${l.action}</td>
        <td><strong>${l.records_changed || 0}</strong></td>
        <td><small style="color:var(--text-secondary);">${l.before_sample || "-"}</small></td>
        <td><small style="color:var(--badge-green-text);">${l.after_sample || "-"}</small></td>
        <td><small style="color:var(--text-muted);">${l.timestamp ? l.timestamp.split("T")[1]?.slice(0, 8) : "-"}</small></td>
      </tr>`)
    .join("");

  // Charts
  chartsGrid.innerHTML = Object.entries(report.charts || {})
    .map(([chartName, chartPath]) => `
      <div class="chart-card">
        <h4 style="font-size: 13px; font-weight: 600; text-transform: capitalize; margin-bottom: 0.5rem; color: var(--text-secondary);">
          ${chartName.replace(/_/g, " ")}
        </h4>
        <img src="/api/runs/${runId}/charts/${chartName}?t=${Date.now()}" alt="${chartName}" loading="lazy">
      </div>`)
    .join("");

  // Download links
  downloadCsvBtn.href = `/api/runs/${runId}/download?format=csv`;
  downloadXlsxBtn.href = `/api/runs/${runId}/download?format=xlsx`;

  // Render cleaned preview table if available
  const overview = report.dataset_overview || {};
  renderTable(
    cleanedHead,
    cleanedBody,
    overview.column_names || [],
    logs.slice(0, 5).map((l) => ({ [l.column]: l.after_sample }))
  );

  resultsSection.scrollIntoView({ behavior: "smooth" });
}

// ========================
// 5. Tabs
// ========================
document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".tab-pane").forEach((p) => (p.style.display = "none"));

    btn.classList.add("active");
    const target = document.getElementById(`tab-${btn.getAttribute("data-tab")}`);
    if (target) target.style.display = "block";
  });
});

// ========================
// 6. Run History Drawer
// ========================
runsDrawerBtn.addEventListener("click", () => {
  runsDrawer.classList.add("open");
  drawerBackdrop.classList.add("open");
  refreshHistoryList();
});

closeDrawerBtn.addEventListener("click", closeDrawer);
drawerBackdrop.addEventListener("click", closeDrawer);

function closeDrawer() {
  runsDrawer.classList.remove("open");
  drawerBackdrop.classList.remove("open");
}

async function refreshHistoryList() {
  try {
    const res = await fetch("/api/runs?limit=30");
    if (!res.ok) return;
    const runs = await res.json();
    runsCountBadge.textContent = runs.length;

    if (!runs || runs.length === 0) {
      runsHistoryList.innerHTML = `<div style="font-size: 13px; color: var(--text-muted); text-align: center; margin-top: 2rem;">No past runs found.</div>`;
      return;
    }

    runsHistoryList.innerHTML = runs
      .map((r) => {
        const timeStr = r.created_at ? new Date(r.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "";
        const scoreBadge = r.final_score !== null && r.final_score !== undefined
          ? `<span class="score-delta-badge" style="font-size: 11px; padding: 2px 6px;">Score: ${Number(r.final_score).toFixed(1)}</span>`
          : `<span class="badge badge-medium">${r.status}</span>`;

        return `
        <div class="card" style="padding: 12px; margin-bottom: 0; cursor: pointer;" onclick="inspectHistoricalRun('${r.run_id}')">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
            <strong style="font-size: 13px; font-family: var(--font-mono);">${r.run_id}</strong>
            ${scoreBadge}
          </div>
          <div style="font-size: 11px; color: var(--text-secondary); display: flex; justify-content: space-between;">
            <span>Dataset: ${r.dataset_id}</span>
            <span>${timeStr}</span>
          </div>
        </div>`;
      })
      .join("");
  } catch (err) {
    console.error("Error refreshing runs:", err);
  }
}

window.inspectHistoricalRun = async function (runId) {
  closeDrawer();
  pipelineSection.style.display = "none";
  await loadRunResults(runId);
};

// Check backend health on boot
async function checkHealth() {
  try {
    const res = await fetch("/health");
    if (res.ok) {
      document.getElementById("backendStatus").textContent = "Backend Online";
    }
  } catch {
    document.getElementById("backendStatus").textContent = "Backend Offline";
  }
}

// Initial boot
initTheme();
checkHealth();
refreshHistoryList();
