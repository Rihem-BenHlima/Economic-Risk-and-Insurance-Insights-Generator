/* Chat settings.
 *
 * backends: addresses the page tries, in order, when it opens. "" means the same address that served the page (when you start backend/server.py and open
 * http://127.0.0.1:8000). If none answers, the chat runs "page only": it answers from the numbers inside this page (chat_local.js) and says so.
 * Contract with the backend:  GET /health -> {mode, ...}   POST /chat {message, history:[{role, content}]} -> {reply, sources, mode}
 *
 * Never put an API key in this file or anywhere in the frontend: anything in the page can be read by whoever opens it.
 * The Gemini key belongs in the root .env; the page only talks to the backend.
 */
window.CHAT_CONFIG = {
  name: "Insights assistant",
  backends: ["", "http://127.0.0.1:8000"],
};
