(function () {
  "use strict";

  var replies = [
    {
      match: /price|plan|cost/i,
      text: "We have four plans — Free, Basic API, Custom, and Advanced. I can help you pick one based on your traffic and integration needs.",
    },
    {
      match: /api|integrat/i,
      text: "Paste one script tag for the widget, or call our /v1/chat/completions API directly. Higher plans add customization and integration support.",
    },
    {
      match: /free|start/i,
      text: "The Free plan includes the embed widget and a site API key so you can try it on your website right away.",
    },
    {
      match: /.*/,
      text: "Thanks for asking! I can explain our plans, the embed widget, or how the API gateway works. What would you like to know?",
    },
  ];

  function pickReply(input) {
    for (var i = 0; i < replies.length - 1; i += 1) {
      if (replies[i].match.test(input)) {
        return replies[i].text;
      }
    }
    return replies[replies.length - 1].text;
  }

  function mount(root) {
    var panelOpen = false;
    var messages = [
      {
        role: "assistant",
        content: "Hi! I'm the Salesperson demo assistant. Ask about plans, the widget, or our API.",
      },
    ];

    var launcher = document.createElement("button");
    launcher.type = "button";
    launcher.className = "demo-chat-launcher";
    launcher.setAttribute("aria-label", "Open sales chat demo");
    launcher.textContent = "Chat with sales";

    var panel = document.createElement("div");
    panel.className = "demo-chat-panel";
    panel.hidden = true;
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-labelledby", "demo-chat-title");
    panel.innerHTML =
      '<div class="demo-chat-header">' +
      '<strong id="demo-chat-title">Sales assistant</strong>' +
      '<span>Demo</span>' +
      "</div>" +
      '<div class="demo-chat-messages" role="log" aria-live="polite"></div>' +
      '<form class="demo-chat-form">' +
      '<input type="text" placeholder="Ask about plans or integration…" autocomplete="off" />' +
      '<button type="submit">Send</button>' +
      "</form>";

    var messageList = panel.querySelector(".demo-chat-messages");
    var form = panel.querySelector(".demo-chat-form");
    var input = form.querySelector("input");

    function renderMessages() {
      messageList.innerHTML = "";
      messages.forEach(function (item) {
        var bubble = document.createElement("div");
        bubble.className = "demo-chat-bubble demo-chat-" + item.role;
        bubble.textContent = item.content;
        messageList.appendChild(bubble);
      });
      messageList.scrollTop = messageList.scrollHeight;
    }

    function togglePanel(open) {
      panelOpen = open;
      panel.hidden = !open;
      launcher.setAttribute("aria-expanded", open ? "true" : "false");
      if (open) {
        input.focus();
      }
    }

    launcher.addEventListener("click", function () {
      togglePanel(!panelOpen);
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
      window.setTimeout(function () {
        messages.push({ role: "assistant", content: pickReply(text) });
        renderMessages();
      }, 450);
    });

    renderMessages();
    root.appendChild(launcher);
    root.appendChild(panel);
  }

  document.addEventListener("DOMContentLoaded", function () {
    var root = document.getElementById("salesperson-demo");
    if (root) {
      mount(root);
    }
  });
})();
