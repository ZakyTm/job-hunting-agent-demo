// extension/background.js
/**
 * Background Service Worker for the AI Job Hunter Agent extension.
 * Handles background polling of FastAPI to update the badge count.
 */

const DEFAULT_FASTAPI_URL = "http://localhost:8000";
const ALARM_NAME = "poll-jobs-alarm";
const POLL_INTERVAL_MINUTES = 10;

// Poll on installation
chrome.runtime.onInstalled.addListener(() => {
  console.log("AI Job Hunter Agent UI Extension Installed.");
  setupAlarm();
  pollAndUpdatesBadge();
});

// Poll on browser startup
chrome.runtime.onStartup.addListener(() => {
  pollAndUpdatesBadge();
});

// Handle alarm triggers
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === ALARM_NAME) {
    pollAndUpdatesBadge();
  }
});

// Set up Chrome alarm
function setupAlarm() {
  chrome.alarms.create(ALARM_NAME, {
    periodInMinutes: POLL_INTERVAL_MINUTES
  });
}

// Poll FastAPI endpoint and update badge count
function pollAndUpdatesBadge() {
  chrome.storage.local.get(["fastapiUrl"], (result) => {
    const baseUrl = result.fastapiUrl || DEFAULT_FASTAPI_URL;
    const url = `${baseUrl}/jobs?status=ready`;

    console.log(`Polling background jobs from: ${url}`);

    fetch(url)
      .then((response) => {
        if (!response.ok) {
          throw new Error(`API returned status ${response.status}`);
        }
        return response.json();
      })
      .then((data) => {
        const jobs = data.jobs || [];
        const count = jobs.length;

        if (count > 0) {
          chrome.action.setBadgeText({ text: count.toString() });
          chrome.action.setBadgeBackgroundColor({ color: "#10B981" }); // Vibrant green
          if (chrome.action.setBadgeTextColor) {
            chrome.action.setBadgeTextColor({ color: "#121212" }); // Dark text for contrast
          }
        } else {
          chrome.action.setBadgeText({ text: "" });
        }
      })
      .catch((error) => {
        console.error("Error polling jobs in background:", error);
        // Show "?" with red background to signal connection issue
        chrome.action.setBadgeText({ text: "?" });
        chrome.action.setBadgeBackgroundColor({ color: "#EF4444" });
        if (chrome.action.setBadgeTextColor) {
          chrome.action.setBadgeTextColor({ color: "#FFFFFF" });
        }
      });
  });
}
