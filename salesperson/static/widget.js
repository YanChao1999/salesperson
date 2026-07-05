(function () {
  "use strict";

  var script = document.currentScript;
  if (!script) {
    return;
  }

  var apiKey = script.getAttribute("data-api-key");
  var apiBase = (script.getAttribute("data-api-base") || window.location.origin).replace(/\/$/, "");

  if (!apiKey) {
    console.warn("[salesperson] Missing data-api-key on embed script.");
    return;
  }

  function createLauncher() {
    var button = document.createElement("button");
    button.type = "button";
    button.textContent = "Chat with sales";
    button.setAttribute("aria-label", "Open sales chat");
    button.style.position = "fixed";
    button.style.right = "20px";
    button.style.bottom = "20px";
    button.style.zIndex = "9999";
    button.style.padding = "12px 16px";
    button.style.borderRadius = "999px";
    button.style.border = "none";
    button.style.background = "#111827";
    button.style.color = "#fff";
    button.style.cursor = "pointer";
    button.style.boxShadow = "0 8px 24px rgba(0,0,0,0.2)";
    return button;
  }

  function sendMessage(content) {
    return fetch(apiBase + "/v1/chat/completions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: "Bearer " + apiKey,
      },
      body: JSON.stringify({
        messages: [{ role: "user", content: content }],
        channel: "website-widget",
      }),
    }).then(function (response) {
      if (!response.ok) {
        throw new Error("Chat request failed: " + response.status);
      }
      return response.json();
    });
  }

  var launcher = createLauncher();
  launcher.addEventListener("click", function () {
    var question = window.prompt("Ask our sales assistant:");
    if (!question) {
      return;
    }
    launcher.disabled = true;
    sendMessage(question)
      .then(function (payload) {
        window.alert(payload.message.content);
      })
      .catch(function (error) {
        console.error("[salesperson]", error);
        window.alert("Sorry, the assistant is unavailable right now.");
      })
      .finally(function () {
        launcher.disabled = false;
      });
  });

  document.body.appendChild(launcher);
})();
