// Frontend logic: upload form submission, dashboard rendering,
// and the processed-document detail view. Connects to the deployed
// backend API (set API_BASE_URL below once deployed).

const API_BASE_URL = "https://document-intelligence-platform-regp.onrender.com/api";

const apiStatus = document.getElementById("api-status");
const uploadForm = document.getElementById("upload-form");
const uploadStatus = document.getElementById("upload-status");
const submitButton = document.getElementById("submit-button");
const dashboardBody = document.getElementById("dashboard-body");

const dropzone = document.getElementById("dropzone");
const dropzoneLabel = document.getElementById("dropzone-label");
const fileInput = document.getElementById("file");

const detailPanel = document.getElementById("detail-panel");
const detailTitle = document.getElementById("detail-title");
const detailFields = document.getElementById("detail-fields");
const detailValidation = document.getElementById("detail-validation");
const detailLineItems = document.getElementById("detail-line-items");
const detailRawJson = document.getElementById("detail-raw-json");

// --- API health indicator ---------------------------------------------
(async () => {
  try {
    const res = await fetch(`${API_BASE_URL}/health`);
    apiStatus.textContent = res.ok ? "API connected" : "API unreachable";
    apiStatus.className = res.ok ? "topbar-status ok" : "topbar-status down";
  } catch {
    apiStatus.textContent = "API unreachable";
    apiStatus.className = "topbar-status down";
  }
})();

// --- Dropzone interactions ----------------------------------------------
fileInput.addEventListener("change", () => {
  if (fileInput.files.length > 0) {
    dropzoneLabel.textContent = fileInput.files[0].name;
  }
});

["dragenter", "dragover"].forEach((evt) =>
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  })
);

["dragleave", "drop"].forEach((evt) =>
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
  })
);

dropzone.addEventListener("drop", (e) => {
  const files = e.dataTransfer.files;
  if (files.length > 0) {
    fileInput.files = files;
    dropzoneLabel.textContent = files[0].name;
  }
});

dropzone.addEventListener("keydown", (e) => {
  if (e.key === "Enter" || e.key === " ") {
    e.preventDefault();
    fileInput.click();
  }
});

// --- Upload / process ----------------------------------------------------
uploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(uploadForm);

  submitButton.disabled = true;
  submitButton.textContent = "Processing\u2026";
  uploadStatus.textContent = "Uploading and running OCR + extraction \u2014 this can take a few seconds.";
  uploadStatus.className = "status-line";

  try {
    const response = await fetch(`${API_BASE_URL}/documents/process`, {
      method: "POST",
      body: formData,
    });
    const result = await response.json();

    if (!response.ok) {
      uploadStatus.textContent = `Couldn't process this file: ${result.detail || "unknown error"}`;
      uploadStatus.className = "status-line error";
      return;
    }

    uploadStatus.textContent = `Processed ${result.document_name} \u2014 ${result.processing_status}`;
    uploadStatus.className = "status-line";
    dropzoneLabel.textContent = "Drop a file here, or click to browse";
    uploadForm.reset();
    await loadDashboard();
    renderDetail(result);
  } catch (err) {
    uploadStatus.textContent = `Couldn't reach the API: ${err.message}`;
    uploadStatus.className = "status-line error";
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = "Process document";
  }
});

// --- Dashboard ------------------------------------------------------------
async function loadDashboard() {
  try {
    const response = await fetch(`${API_BASE_URL}/documents`);
    const rows = await response.json();

    if (!response.ok) {
      dashboardBody.innerHTML = `<tr><td colspan="4" class="empty-state">Couldn't load documents: ${escapeHtml(rows.detail || "unknown error")}</td></tr>`;
      return;
    }
    if (rows.length === 0) {
      dashboardBody.innerHTML = `<tr><td colspan="4" class="empty-state">No documents processed yet \u2014 upload one above to get started.</td></tr>`;
      return;
    }

    dashboardBody.innerHTML = "";
    for (const row of rows) {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${escapeHtml(row.document_name)}</td>
        <td>${escapeHtml(row.document_type)}</td>
        <td>${statusPill(row.processing_status)}</td>
        <td>${row.created_at ? formatDate(row.created_at) : ""}</td>
      `;
      tr.addEventListener("click", () => loadDetail(row.document_name));
      dashboardBody.appendChild(tr);
    }
  } catch (err) {
    dashboardBody.innerHTML = `<tr><td colspan="4" class="empty-state">Couldn't reach the API: ${escapeHtml(err.message)}</td></tr>`;
  }
}

async function loadDetail(documentName) {
  try {
    const response = await fetch(`${API_BASE_URL}/documents/${encodeURIComponent(documentName)}`);
    const result = await response.json();
    if (!response.ok) {
      uploadStatus.textContent = `Couldn't load ${documentName}: ${result.detail || "unknown error"}`;
      uploadStatus.className = "status-line error";
      return;
    }
    renderDetail(result);
  } catch (err) {
    uploadStatus.textContent = `Couldn't reach the API: ${err.message}`;
    uploadStatus.className = "status-line error";
  }
}

// --- Detail rendering ------------------------------------------------------
function renderDetail(result) {
  detailPanel.hidden = false;
  detailTitle.textContent = `${result.document_name} (${result.document_type})`;
  detailRawJson.textContent = JSON.stringify(result, null, 2);

  detailFields.innerHTML = renderExtractedFields(result.extracted_data);
  detailValidation.innerHTML = renderValidation(result.validation);
  detailLineItems.innerHTML = renderLineItems(result.extracted_data?.line_items);

  detailPanel.scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderExtractedFields(extractedData) {
  if (!extractedData || Object.keys(extractedData).length === 0) {
    return `<p class="empty-state">No fields extracted.</p>`;
  }

  const rows = Object.entries(extractedData)
    .filter(([name]) => name !== "line_items")
    .map(([name, field]) => {
      const value = field && typeof field === "object" ? field.value : field;
      const isMissing = value === null || value === undefined;
      const displayValue = isMissing ? "not found" : escapeHtml(String(value));
      const hint = field?.source_text
        ? ` <span class="evidence-hint" title="${escapeHtml(field.source_text)}${field.page_number ? ` (page ${field.page_number})` : ""}">source</span>`
        : "";
      return `<div class="field-row">
        <span class="field-name">${escapeHtml(name)}</span>
        <span class="field-value ${isMissing ? "missing" : ""}">${displayValue}${hint}</span>
      </div>`;
    })
    .join("");

  return rows;
}

function renderLineItems(lineItems) {
  if (!Array.isArray(lineItems) || lineItems.length === 0) return "";

  const rows = lineItems
    .map(
      (item) => `<tr>
        <td>${escapeHtml(item.description ?? "\u2014")}</td>
        <td>${item.quantity ?? "\u2014"}</td>
        <td>${item.unit_price ?? "\u2014"}</td>
        <td>${item.amount ?? "\u2014"}</td>
      </tr>`
    )
    .join("");

  return `<div class="line-items">
    <h3>Line items</h3>
    <table>
      <thead><tr><th>Description</th><th>Qty</th><th>Unit price</th><th>Amount</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
  </div>`;
}

function renderValidation(validation) {
  if (!validation || !validation.checks || validation.checks.length === 0) {
    return `<p class="empty-state">No applicable checks for this document.</p>`;
  }

  return validation.checks
    .map((check) => {
      const icon = check.status === "PASS" ? "\u2713" : check.status === "FAIL" ? "\u2715" : "\u2013";
      const iconClass = check.status === "PASS" ? "pass" : check.status === "FAIL" ? "fail" : "na";
      const numbers =
        check.status === "NOT_APPLICABLE"
          ? "not enough fields present to check"
          : `${check.calculated_value} calculated vs. ${check.reported_value} reported`;
      const numbersClass = check.status === "FAIL" ? "fail-number" : "";

      return `<div class="check-row">
        <div class="check-head">
          <span class="check-icon ${iconClass}">${icon}</span>
          <span>${escapeHtml(check.name)}</span>
        </div>
        <p class="check-formula">${escapeHtml(check.formula)}</p>
        <p class="check-numbers"><span class="${numbersClass}">${numbers}</span></p>
      </div>`;
    })
    .join("");
}

function statusPill(status) {
  const cls = status === "PASS" ? "pill-pass" : status === "FAIL" ? "pill-fail" : "pill-na";
  return `<span class="pill ${cls}">${escapeHtml(status)}</span>`;
}

function formatDate(iso) {
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" }) + " " +
    d.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

loadDashboard();