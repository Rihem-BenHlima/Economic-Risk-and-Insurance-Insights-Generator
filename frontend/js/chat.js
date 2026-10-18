/* Chat widget: a button and a panel on every page. Each time the panel is opened a new conversation starts; past ones are kept in this browser (localStorage)
 * under the History button, and the expand button shows the chat full page. On opening, the page looks for the backend (GET /health). If it answers, questions go to it and the answer
 * comes back with its sources; if not, the chat runs "page only" and answers from the numbers inside the page (chat_local.js). */
(function () {
  const { h, icon } = UI;
  const cfg = window.CHAT_CONFIG || {};
  const bases = (location.protocol.startsWith("http") ? [""] : []).concat((cfg.backends || []).filter((b) => b !== ""));
  const SUGGESTIONS = ["What will premiums be in 2027?", "Which model is most accurate?", "How big is the motor branch?", "What is the unemployment rate?", "How reliable are the forecasts?"];
  const KEY = "tunisia_chat_history_v1", MAX_CONVS = 40;
  let convs = [], cur = null, full = false;                                          // saved conversations, the one on screen, full-page mode
  let base = null, info = null, panel, list, input, chips, statusEl, bannerEl, launcher, histEl, histList, fullBtn, busy = false;

  const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const rich = (s) => esc(s).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/\n/g, "<br>");
  const shortSource = (s) => s.split("/").pop();
  const WELCOME = "Hi! I can answer questions about the **forecasts**, how accurate they are, and the latest figures for insurance, the economy, jobs, agriculture and climate.";

  const store = {
    load() { try { const v = JSON.parse(localStorage.getItem(KEY) || "[]"); return Array.isArray(v) ? v : []; } catch (e) { return []; } },
    save() { try { localStorage.setItem(KEY, JSON.stringify(convs.slice(0, MAX_CONVS))); } catch (e) { /* storage full or blocked: history just will not persist */ } },
  };

  function bubble(role, html, note, sources) {
    const b = h("div", { class: "msg " + role }, role === "bot" ? h("span", { class: "avatar", "aria-hidden": "true" }, icon("chat", 14)) : null,
      h("div", { class: "msg-body" }, h("div", { class: "bubble", html }),
        note ? h("div", { class: "msg-note" }, note) : null));
    list.append(b);
    list.scrollTop = list.scrollHeight;
    return b;
  }

  function typing() {
    const t = h("div", { class: "msg bot" }, h("span", { class: "avatar", "aria-hidden": "true" }, icon("chat", 14)), h("div", { class: "msg-body" }, h("div", { class: "bubble typing", html: "<i></i><i></i><i></i>" })));
    list.append(t); list.scrollTop = list.scrollHeight;
    return t;
  }

  /* ---- conversations ---- */
  function show(conv) {                                                               // draws a conversation in the message list
    cur = conv;
    list.textContent = "";
    bubble("bot", rich(WELCOME));
    conv.msgs.forEach((m) => (m.role === "user" ? bubble("me", esc(m.content)) : bubble("bot", rich(m.content), m.note, m.sources)));
    chips.style.display = conv.msgs.length ? "none" : "";
    renderHistory();
  }
  function fresh() { show({ id: Date.now().toString(36), title: "", ts: Date.now(), msgs: [] }); closeHistory(); }
  function persist() {
    if (!cur.msgs.length) return;
    if (!convs.includes(cur)) convs.unshift(cur);
    cur.ts = Date.now();
    store.save();
    renderHistory();
  }
  function ago(ts) {
    const m = Math.round((Date.now() - ts) / 60000);
    if (m < 1) return "just now";
    if (m < 60) return m + " min ago";
    if (m < 1440) return Math.round(m / 60) + " h ago";
    return new Date(ts).toLocaleDateString(undefined, { day: "numeric", month: "short" });
  }
  function renderHistory() {
    histList.textContent = "";
    if (!convs.length) { histList.append(h("p", { class: "hist-empty" }, "No past conversations yet. Your questions are saved here, in this browser only.")); return; }
    convs.slice().sort((a, b) => b.ts - a.ts).forEach((c) => histList.append(h("div", { class: "hist-item" + (c === cur ? " on" : "") },
      h("button", { type: "button", class: "hist-open", onclick: () => { if (!busy) { show(c); closeHistory(); } } }, h("b", {}, c.title || "Conversation"), h("span", {}, ago(c.ts) + " · " + Math.ceil(c.msgs.length / 2) + " Q")),
      h("button", { type: "button", class: "hist-del", "aria-label": "Delete this conversation", onclick: () => remove(c) }, icon("trash", 15)))));
  }
  function remove(c) {
    if (busy) return;
    convs = convs.filter((x) => x !== c);
    store.save();
    if (c === cur) fresh(); else renderHistory();
  }
  function clearAll() { if (busy || !convs.length || !confirm("Delete all saved conversations?")) return; convs = []; store.save(); fresh(); }
  function toggleHistory() { panel.classList.toggle("hist-open"); }
  function closeHistory() { panel.classList.remove("hist-open"); }
  function setFull(on) {
    full = on;
    panel.classList.toggle("full", on);
    document.body.classList.toggle("chat-full", on);
    fullBtn.replaceChildren(icon(on ? "shrink" : "expand", 17));
    fullBtn.setAttribute("aria-label", on ? "Back to small window" : "Open in full page");
    fullBtn.title = on ? "Back to small window" : "Open in full page";
    if (!on) closeHistory();
  }

  async function detect() {
    base = null; info = null;
    for (const b of bases) {
      const ctl = new AbortController(), timer = setTimeout(() => ctl.abort(), 1500);
      try {
        const r = await fetch(b + "/health", { signal: ctl.signal });
        if (r.ok) { info = await r.json(); base = b; clearTimeout(timer); break; }
      } catch (e) { /* not there */ }
      clearTimeout(timer);
    }
    statusEl.textContent = base === null ? "Page only" : "";
    statusEl.className = "chat-status" + (base !== null ? " live" : "");
    statusEl.style.display = statusEl.textContent ? "" : "none";
    bannerEl.textContent = base === null ? "Page only: answers come from the numbers on this page. Start backend/server.py and open http://127.0.0.1:8000 for the full assistant."
      : "";
    bannerEl.style.display = bannerEl.textContent ? "" : "none";
  }

  async function reply(text, prior) {
    if (base !== null) {
      try {
        const r = await fetch(base + "/chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message: text, history: prior }) });
        if (!r.ok) throw new Error("HTTP " + r.status);
        const j = await r.json();
        return { text: j.reply, sources: j.sources || [], note: j.error ? "The language model could not be reached." : null };
      } catch (e) {
        return { text: ChatLocal.answer(text), sources: [], note: "The backend could not be reached, so this answer comes from the data on this page." };
      }
    }
    return { text: ChatLocal.answer(text), sources: [], note: null };
  }

  async function send(text) {
    text = (text || "").trim();
    if (!text || busy) return;
    busy = true;
    chips.style.display = "none";
    const conv = cur, prior = conv.msgs.map((m) => ({ role: m.role, content: m.content }));
    bubble("me", esc(text));
    conv.msgs.push({ role: "user", content: text });
    if (!conv.title) conv.title = text.length > 48 ? text.slice(0, 46) + "…" : text;
    persist();
    const t = typing();
    const r = await reply(text, prior);
    t.remove();
    bubble("bot", rich(r.text), r.note, r.sources);
    conv.msgs.push({ role: "assistant", content: r.text, sources: r.sources, note: r.note });
    persist();
    busy = false;
  }

  function open(on = true, fullPage = false) {
    const was = panel.classList.contains("open");
    panel.classList.toggle("open", on);
    launcher.classList.toggle("hidden", on);
    if (on && !was && !busy) fresh();                                                 // every time the panel is opened a new conversation starts
    if (!on) { closeHistory(); if (full) setFull(false); }
    if (on && fullPage) setFull(true);                                                // the sidebar link opens it full page; the round button keeps it small
    if (on) setTimeout(() => input.focus(), 120);
  }

  function build() {
    convs = store.load();
    list = h("div", { class: "chat-list", "aria-live": "polite" });
    input = h("input", { type: "text", placeholder: "Ask about forecasts or figures…", "aria-label": "Your question", autocomplete: "off", maxlength: "1000" });
    chips = h("div", { class: "chat-chips" }, SUGGESTIONS.map((s) => h("button", { type: "button", onclick: () => send(s) }, s)));
    statusEl = h("span", { class: "chat-status" }, "Checking…");
    bannerEl = h("div", { class: "chat-banner" }, "");
    histList = h("div", { class: "hist-list" });
    fullBtn = h("button", { class: "chat-ico", type: "button", "aria-label": "Open in full page", title: "Open in full page", onclick: () => setFull(!full) }, icon("expand", 17));
    histEl = h("aside", { class: "chat-hist", "aria-label": "Past conversations" },
      h("div", { class: "hist-head" }, h("b", {}, "History"), h("button", { type: "button", class: "hist-clear", onclick: clearAll }, "Clear all")),
      h("button", { type: "button", class: "hist-new", onclick: () => { if (!busy) fresh(); } }, icon("plus", 16), "New conversation"), histList);
    panel = h("section", { class: "chat", role: "dialog", "aria-label": cfg.name || "Assistant" },
      h("header", { class: "chat-head" },
        h("span", { class: "avatar big", "aria-hidden": "true" }, icon("chat", 18)),
        h("div", { class: "chat-title" }, h("b", {}, cfg.name || "Assistant")),
        statusEl,
        h("button", { class: "chat-ico", type: "button", "aria-label": "New conversation", title: "New conversation", onclick: () => { if (!busy) fresh(); } }, icon("plus", 17)),
        h("button", { class: "chat-ico", type: "button", "aria-label": "History", title: "History", onclick: toggleHistory }, icon("history", 17)),
        fullBtn,
        h("button", { class: "chat-x", type: "button", "aria-label": "Close", onclick: () => open(false), html: "&times;" })),
      h("div", { class: "chat-body" }, histEl,
        h("div", { class: "chat-col" }, list, bannerEl, chips,
          h("form", { class: "chat-form", onsubmit: (e) => { e.preventDefault(); const v = input.value; input.value = ""; send(v); } }, input,
            h("button", { class: "chat-send", type: "submit", "aria-label": "Send" }, icon("send", 18))))));
    launcher = h("button", { class: "chat-launch", type: "button", "aria-label": "Open the assistant", onclick: () => open(true) }, icon("chat", 22), h("span", {}, "Ask"));
    document.body.append(panel, launcher);
    document.addEventListener("keydown", (e) => {
      if (e.key !== "Escape" || !panel.classList.contains("open")) return;
      if (panel.classList.contains("hist-open")) closeHistory(); else if (full) setFull(false);
    });
    fresh();
  }

  async function init() {
    build();
    await detect();
    const q = new URLSearchParams(location.search).get("ask");        // deep link: ?ask=your question opens the chat and asks it
    if (q) { open(true); send(q); }
  }

  window.Chat = { open, send };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();
})();
