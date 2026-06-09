// extension/settings.js
/**
 * Handles saving and retrieving extension configurations to/from chrome.storage.local
 */

document.addEventListener("DOMContentLoaded", () => {
  // Load saved settings
  chrome.storage.local.get(
    [
      "fastapiUrl",
      "supabaseUrl",
      "supabaseAnonKey",
      "telegramBotToken",
      "telegramChatId",
      "geminiApiKey"
    ],
    (result) => {
      document.getElementById("fastapi-url").value = result.fastapiUrl || "http://localhost:8000";
      document.getElementById("supabase-url").value = result.supabaseUrl || "";
      document.getElementById("supabase-key").value = result.supabaseAnonKey || "";
      document.getElementById("telegram-token").value = result.telegramBotToken || "";
      document.getElementById("telegram-chat-id").value = result.telegramChatId || "";
      document.getElementById("gemini-key").value = result.geminiApiKey || "";
    }
  );

  // Close settings tab on back click
  document.getElementById("btn-back").addEventListener("click", (e) => {
    e.preventDefault();
    chrome.tabs.getCurrent((tab) => {
      if (tab) {
        chrome.tabs.remove(tab.id);
      }
    });
  });

  // Save settings on submit
  document.getElementById("btn-save").addEventListener("click", () => {
    const fastapiUrl = document.getElementById("fastapi-url").value.trim();
    const supabaseUrl = document.getElementById("supabase-url").value.trim();
    const supabaseAnonKey = document.getElementById("supabase-key").value.trim();
    const telegramBotToken = document.getElementById("telegram-token").value.trim();
    const telegramChatId = document.getElementById("telegram-chat-id").value.trim();
    const geminiApiKey = document.getElementById("gemini-key").value.trim();

    chrome.storage.local.set(
      {
        fastapiUrl,
        supabaseUrl,
        supabaseAnonKey,
        telegramBotToken,
        telegramChatId,
        geminiApiKey
      },
      () => {
        // Show success alert
        const alertBox = document.getElementById("alert-success");
        alertBox.style.display = "block";

        // Hide alert after 3 seconds
        setTimeout(() => {
          alertBox.style.display = "none";
        }, 3000);

        // Notify background.js to re-poll jobs using new endpoints immediately
        chrome.runtime.sendMessage({ action: "settings-updated" }, (response) => {
          // Ignore response, handles scenario where background script is inactive
          if (chrome.runtime.lastError) {
            console.log("Background script not ready, ignoring runtime message error.");
          }
        });
      }
    );
  });
});
