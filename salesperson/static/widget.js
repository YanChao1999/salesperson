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

  var style = document.createElement("style");
  style.textContent =
    ".spw-launcher{position:fixed;right:20px;bottom:20px;z-index:9999;padding:12px 16px;border:none;border-radius:999px;background:#111827;color:#fff;font-weight:600;cursor:pointer;box-shadow:0 8px 24px rgba(0,0,0,.2)}" +
    ".spw-panel{position:fixed;right:20px;bottom:84px;z-index:9999;width:min(320px,calc(100vw - 40px));max-height:min(420px,calc(100vh - 120px));border:1px solid rgba(0,0,0,.12);border-radius:16px;background:#fff;color:#111;box-shadow:0 16px 48px rgba(0,0,0,.18);display:flex;flex-direction:column;overflow:hidden;font:14px/1.45 system-ui,sans-serif}" +
    ".spw-panel[hidden]{display:none}" +
    ".spw-header{display:flex;justify-content:space-between;gap:8px;padding:12px 14px;border-bottom:1px solid rgba(0,0,0,.08);background:#f8fafc;font-weight:600}" +
    ".spw-header span{font-weight:400;color:#64748b;font-size:12px}" +
    ".spw-messages{display:grid;gap:10px;flex:1;min-height:0;overflow-y:auto;padding:14px;background:#fff}" +
    ".spw-bubble{max-width:88%;padding:10px 12px;border-radius:14px;white-space:pre-wrap;word-break:break-word}" +
    ".spw-user{justify-self:end;background:#2563eb;color:#fff;border-bottom-right-radius:4px}" +
    ".spw-assistant{justify-self:start;background:#f1f5f9;color:#111;border-bottom-left-radius:4px}" +
    ".spw-form{display:flex;gap:8px;padding:12px;border-top:1px solid rgba(0,0,0,.08)}" +
    ".spw-form input{flex:1;min-width:0;padding:10px 12px;border:1px solid rgba(0,0,0,.12);border-radius:10px}" +
    ".spw-form button{padding:10px 14px;border:none;border-radius:10px;background:#111827;color:#fff;font-weight:600;cursor:pointer}";
  document.head.appendChild(style);

  function getVisitorId() {
    var storageKey = "salesperson_visitor_id";
    try {
      var existing = localStorage.getItem(storageKey);
      if (existing) {
        return existing;
      }
      var id = "visitor-" + Math.random().toString(36).slice(2, 10);
      localStorage.setItem(storageKey, id);
      return id;
    } catch (error) {
      return "visitor-anonymous";
    }
  }

  var visitorId = getVisitorId();

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
        user_id: visitorId,
      }),
    }).then(function (response) {
      if (!response.ok) {
        throw new Error("Chat request failed: " + response.status);
      }
      return response.json();
    });
  }

  var panelOpen = false;
  var messages = [
    {
      role: "assistant",
      content: "Hi! How can I help you find the right product or plan?",
    },
  ];

  var launcher = document.createElement("button");
  launcher.type = "button";
  launcher.className = "spw-launcher";
  launcher.setAttribute("aria-label", "Open sales chat");
  launcher.textContent = "Chat with sales";

  var panel = document.createElement("div");
  panel.className = "spw-panel";
  panel.hidden = true;
  panel.setAttribute("role", "dialog");
  panel.setAttribute("aria-labelledby", "spw-title");
  panel.innerHTML =
    '<div class="spw-header"><strong id="spw-title">Sales assistant</strong><span>Online</span></div>' +
    '<div class="spw-messages" role="log" aria-live="polite"></div>' +
    '<form class="spw-form"><input type="text" placeholder="Ask a question…" autocomplete="off" /><button type="submit">Send</button></form>';

  var messageList = panel.querySelector(".spw-messages");
  var form = panel.querySelector(".spw-form");
  var input = form.querySelector("input");
  var submitButton = form.querySelector("button");

  function renderMessages() {
    messageList.innerHTML = "";
    messages.forEach(function (item) {
      var bubble = document.createElement("div");
      bubble.className = "spw-bubble spw-" + item.role;
      bubble.textContent = item.content;
      messageList.appendChild(bubble);
    });
    messageList.scrollTop = messageList.scrollHeight;
  }

  function setOpen(open) {
    panelOpen = open;
    panel.hidden = !open;
    launcher.setAttribute("aria-expanded", open ? "true" : "false");
    if (open) {
      input.focus();
    }
  }

  launcher.addEventListener("click", function () {
    setOpen(!panelOpen);
  });

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    var text = input.value.trim();
    if (!text) {
      return;
    }
    messages.push({ role: "user", content: text });
    input.value = "";
    renderMessages();
    submitButton.disabled = true;
    sendMessage(text)
      .then(function (payload) {
        messages.push({ role: "assistant", content: payload.message.content });
        renderMessages();
      })
      .catch(function (error) {
        console.error("[salesperson]", error);
        messages.push({
          role: "assistant",
          content: "Sorry, the assistant is unavailable right now.",
        });
        renderMessages();
      })
      .finally(function () {
        submitButton.disabled = false;
        input.focus();
      });
  });

  renderMessages();
  document.body.appendChild(launcher);
  document.body.appendChild(panel);
})();
