const box = document.getElementById("chat-box");
const form = document.getElementById("chat-form");
const input = document.getElementById("message");
const sendBtn = document.getElementById("send-btn");
const quick = document.getElementById("quick-options");
const cfg = window.CHAT_CONFIG;

let history = [];   // the conversation the AI remembers
let busy = false;

/* ---- keep the conversation while the visitor moves between website pages ---- */
function save() { try { sessionStorage.setItem("ei-chat", JSON.stringify(history)); } catch (e) {} }
function load() { try { return JSON.parse(sessionStorage.getItem("ei-chat")) || []; } catch (e) { return []; } }

/* ---- safe text -> HTML (escapes everything first, then adds bold/links/line breaks) ---- */
function format(text) {
  return text
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/(https?:\/\/[^\s<)]+)/g, '<a href="$1" target="_blank" rel="noopener">$1</a>')
    .replace(/(^|[\s(])([\w.+-]+@[\w-]+\.[\w.-]*\w)/g, '$1<a href="mailto:$2">$2</a>')
    .replace(/\n/g, "<br>");
}

function addMessage(role, text) {
  const el = document.createElement("div");
  el.className = "msg " + role;
  if (role === "user") el.textContent = text; else el.innerHTML = format(text);
  box.appendChild(el);
  box.scrollTop = box.scrollHeight;
  return el;
}

function setBusy(state) {
  busy = state;
  sendBtn.disabled = state;
  input.disabled = state;
}

async function send(text) {
  text = text.trim();
  if (!text || busy) return;
  setBusy(true);
  quick.innerHTML = "";
  addMessage("user", text);

  const botEl = addMessage("bot", "");
  botEl.innerHTML = '<span class="dots"><i></i><i></i><i></i></span>';

  let reply = "";
  let ok = false;
  try {
    const res = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, history: history.slice(-12) })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || "Something went wrong. Please try again.");
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      reply += decoder.decode(value, { stream: true });
      botEl.innerHTML = format(reply);
      box.scrollTop = box.scrollHeight;
    }
    ok = reply.trim().length > 0;
  } catch (e) {
    reply = e.message === "Failed to fetch"
      ? "Sorry, I couldn't connect. Please check your internet and try again."
      : e.message;
    botEl.innerHTML = format(reply);
  }

  if (ok) { history.push({ role: "user", content: text }, { role: "assistant", content: reply }); save(); }
  setBusy(false);
  input.value = "";
  input.focus();
}

form.addEventListener("submit", (e) => { e.preventDefault(); const t = input.value; input.value = ""; send(t); });

/* ---- start-up ---- */
history = load();
if (history.length) {
  history.forEach((m) => addMessage(m.role === "user" ? "user" : "bot", m.content));
} else {
  addMessage("bot", cfg.welcome);
  cfg.quickReplies.forEach((q) => {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = q;
    b.addEventListener("click", () => send(q));
    quick.appendChild(b);
  });
}

/* ---- close button tells the website to hide the floating window ---- */
document.getElementById("close-btn").addEventListener("click", () => {
  if (window.parent !== window) window.parent.postMessage("eic-close", "*");
});
