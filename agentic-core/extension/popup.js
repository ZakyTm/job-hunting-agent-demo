// extension/popup.js
/**
 * Main logic for the AI Job Hunter Agent extension popup.
 * Handles job fetching, tab filtering, details expansion, CV retrieval, and manual approvals.
 */

const DEFAULT_FASTAPI_URL = "http://localhost:8000";
let jobsData = [];
let currentFilter = "pending";

document.addEventListener("DOMContentLoaded", () => {
  // Navigate to Settings Page
  document.getElementById("btn-settings").addEventListener("click", () => {
    chrome.tabs.create({ url: "settings.html" });
  });

  // Filter tab events
  const tabs = document.querySelectorAll(".filter-tab");
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      currentFilter = tab.dataset.filter;
      renderJobs();
    });
  });

  // Load jobs from API on open
  loadJobs();
});

// Fetch all jobs from FastAPI backend
function loadJobs() {
  const listContainer = document.getElementById("job-list");
  listContainer.innerHTML = '<div class="no-jobs">Loading jobs...</div>';

  chrome.storage.local.get(["fastapiUrl"], (result) => {
    const baseUrl = result.fastapiUrl || DEFAULT_FASTAPI_URL;
    const url = `${baseUrl}/jobs?limit=80`;

    console.log(`Fetching jobs from: ${url}`);

    fetch(url)
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Server returned status ${response.status}`);
        }
        return response.json();
      })
      .then((data) => {
        jobsData = data.jobs || [];
        renderJobs();
      })
      .catch((error) => {
        console.error("Error loading jobs:", error);
        listContainer.innerHTML = `
          <div class="no-jobs">
            <p style="color: #ef4444; font-weight: 600; margin-bottom: 6px;">Failed to connect to FastAPI.</p>
            <p style="font-size: 11px; margin: 0;">Verify your agent backend is running at:</p>
            <code style="display: block; background: #1a1a1a; padding: 4px; border-radius: 4px; margin-top: 4px; font-size: 11px;">${baseUrl}</code>
          </div>
        `;
      });
  });
}

// Render filtered job list
function renderJobs() {
  const listContainer = document.getElementById("job-list");
  listContainer.innerHTML = "";

  // Filter jobs based on active tab
  const filteredJobs = jobsData.filter((job) => {
    const status = (job.status || "").toLowerCase();
    if (currentFilter === "pending") {
      return status === "ready" || status === "maybe" || status === "new";
    } else if (currentFilter === "approved") {
      return status === "approved" || status === "completed";
    } else if (currentFilter === "ignored") {
      return status === "ignored" || status === "ignored_by_user";
    }
    return false;
  });

  if (filteredJobs.length === 0) {
    listContainer.innerHTML = `<div class="no-jobs">No ${currentFilter} jobs found.</div>`;
    return;
  }

  // Render cards
  filteredJobs.forEach((job) => {
    const card = document.createElement("div");
    card.className = "job-card";

    const score = job.match_score || 0;
    let scoreClass = "score-low";
    if (score >= 7) scoreClass = "score-high";
    else if (score >= 5) scoreClass = "score-medium";

    const formattedStatus = job.status === "ready" ? "pending" : job.status;
    const isCVAvailable = job.status === "completed" || job.status === "approved";

    card.innerHTML = `
      <div class="card-header">
        <h3 class="job-title">${escapeHtml(job.job_title || "Unknown Position")}</h3>
        <span class="badge-score ${scoreClass}">${score}/10</span>
      </div>
      <div class="company-name">${escapeHtml(job.company_name || "Unknown Company")}</div>
      
      <!-- Collapsible Detailed View -->
      <div class="job-details" style="display: none; border-top: 1px solid #2d2d2d; padding-top: 10px; margin-top: 8px; font-size: 11px; color: #cbd5e1;">
        <p style="margin: 0 0 8px 0; line-height: 1.4;"><strong>Reasoning:</strong> ${escapeHtml(job.match_reasoning || "No evaluation details available.")}</p>
        
        ${job.company_intel ? `
          <div style="background: rgba(0, 0, 0, 0.25); padding: 8px; border-radius: 6px; margin-top: 8px; border: 1px solid #282828;">
            <div style="color: #10B981; font-weight: 600; margin-bottom: 4px; text-transform: uppercase; font-size: 9px; letter-spacing: 0.5px;">Company Intel</div>
            <div style="margin-bottom: 4px; line-height: 1.3;"><strong>Size:</strong> ${escapeHtml(job.company_intel.company_size || "N/A")}</div>
            <div style="margin-bottom: 4px; line-height: 1.3;"><strong>Tech Stack:</strong> ${escapeHtml((job.company_intel.tech_stack || []).join(", ") || "N/A")}</div>
            <div style="margin-bottom: 0; line-height: 1.3;"><strong>Talking Point:</strong> ${escapeHtml(job.company_intel.talking_point || "N/A")}</div>
          </div>
        ` : ""}
      </div>

      <div class="card-meta">
        <span class="status-label status-${job.status}">${escapeHtml(formattedStatus)}</span>
        <div style="display: flex; gap: 8px; align-items: center;">
          ${job.source_channel ? `<span class="source-tag">📡 ${escapeHtml(job.source_channel)}</span>` : ""}
          <span>${formatDate(job.created_at)}</span>
        </div>
      </div>

      <div class="card-actions">
        <button class="btn btn-secondary btn-details">View Details</button>
        <button class="btn btn-secondary btn-cv" ${!isCVAvailable ? "disabled title='Tailored CV will be generated once approved.'" : ""}>Open CV</button>
      </div>

      ${(job.status === "ready" || job.status === "maybe" || job.status === "new") ? `
        <div class="card-actions" style="margin-top: 6px;">
          <button class="btn btn-primary btn-approve">Approve</button>
          <button class="btn btn-secondary btn-ignore" style="color: #ef4444; border-color: rgba(239, 68, 68, 0.25);">Ignore</button>
        </div>
      ` : ""}
    `;

    // Collapsible Detail Toggle
    const detailsPanel = card.querySelector(".job-details");
    const detailsBtn = card.querySelector(".btn-details");
    detailsBtn.addEventListener("click", () => {
      const isVisible = detailsPanel.style.display !== "none";
      detailsPanel.style.display = isVisible ? "none" : "block";
      detailsBtn.textContent = isVisible ? "View Details" : "Hide Details";
    });

    // Open Rendered CV page in new tab
    const cvBtn = card.querySelector(".btn-cv");
    cvBtn.addEventListener("click", () => {
      chrome.storage.local.get(["fastapiUrl"], (result) => {
        const baseUrl = result.fastapiUrl || DEFAULT_FASTAPI_URL;
        chrome.tabs.create({ url: `${baseUrl}/jobs/${job.id}/cv` });
      });
    });

    // Trigger API approval background task
    const approveBtn = card.querySelector(".btn-approve");
    if (approveBtn) {
      approveBtn.addEventListener("click", () => {
        approveBtn.disabled = true;
        approveBtn.textContent = "Approving...";
        chrome.storage.local.get(["fastapiUrl"], (result) => {
          const baseUrl = result.fastapiUrl || DEFAULT_FASTAPI_URL;
          fetch(`${baseUrl}/jobs/${job.id}/approve`, { method: "POST" })
            .then((resp) => {
              if (resp.ok) {
                loadJobs();
              } else {
                alert("Failed to approve job");
                approveBtn.disabled = false;
                approveBtn.textContent = "Approve";
              }
            })
            .catch((err) => {
              console.error(err);
              alert("Error connecting to FastAPI server.");
              approveBtn.disabled = false;
              approveBtn.textContent = "Approve";
            });
        });
      });
    }

    // Trigger ignore directly via Supabase REST API
    const ignoreBtn = card.querySelector(".btn-ignore");
    if (ignoreBtn) {
      ignoreBtn.addEventListener("click", () => {
        ignoreBtn.disabled = true;
        ignoreBtn.textContent = "Ignoring...";

        chrome.storage.local.get(["supabaseUrl", "supabaseAnonKey"], (result) => {
          const supabaseUrl = result.supabaseUrl;
          const supabaseKey = result.supabaseAnonKey;

          if (supabaseUrl && supabaseKey) {
            const url = `${supabaseUrl}/rest/v1/jobs?id=eq.${job.id}`;
            fetch(url, {
              method: "PATCH",
              headers: {
                "apikey": supabaseKey,
                "Authorization": `Bearer ${supabaseKey}`,
                "Content-Type": "application/json"
              },
              body: JSON.stringify({ status: "ignored_by_user" })
            })
            .then((resp) => {
              if (resp.ok) {
                loadJobs();
              } else {
                alert("Failed to ignore job in database");
                ignoreBtn.disabled = false;
                ignoreBtn.textContent = "Ignore";
              }
            })
            .catch((err) => {
              console.error(err);
              alert("Error connecting to Supabase database.");
              ignoreBtn.disabled = false;
              ignoreBtn.textContent = "Ignore";
            });
          } else {
            alert("Supabase credentials are required in Settings to update job status.");
            ignoreBtn.disabled = false;
            ignoreBtn.textContent = "Ignore";
          }
        });
      });
    }

    listContainer.appendChild(card);
  });
}

function escapeHtml(text) {
  if (typeof text !== "string") return text;
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function formatDate(dateStr) {
  if (!dateStr) return "";
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
  } catch (e) {
    return dateStr;
  }
}
