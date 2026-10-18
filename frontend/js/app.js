/* App shell: navigation, hash routing (#/overview ...), light / dark theme, and the page title. */
(function () {
  const { h, icon, fmt, D } = UI;
  const ORDER = ["overview", "forecasts", "insurance", "economy", "labour", "agriculture", "climate"];
  const NAMES = { overview: "Overview", forecasts: "Forecasts", insurance: "Insurance", economy: "Economy", labour: "Labour", agriculture: "Agriculture", climate: "Climate and risk" };

  const store = { get: (k) => { try { return localStorage.getItem(k); } catch (e) { return null; } }, set: (k, v) => { try { localStorage.setItem(k, v); } catch (e) { /* private window */ } } };

  function setTheme(t) {
    document.documentElement.setAttribute("data-theme", t);
    store.set("theme", t);
    const b = document.getElementById("theme-btn");
    b.replaceChildren(icon(t === "dark" ? "sun" : "moon", 19));
  }

  function buildNav() {
    const nav = document.getElementById("nav");
    ORDER.forEach((id, i) => {
      if (id === "insurance") nav.append(h("div", { class: "sep" }));
      nav.append(h("a", { href: "#/" + id, "data-id": id }, icon(id, 20), NAMES[id]));
    });
    nav.append(h("div", { class: "sep" }), h("a", { href: "#", class: "ask", onclick: (e) => { e.preventDefault(); document.body.classList.remove("menu-open"); Chat.open(true, true); } }, icon("chat", 20), "Ask the assistant"));
    const ens = D.forecast.forecasts.ensemble.premiums_total, y = D.meta.last_year;
    document.getElementById("foot-forecast").innerHTML = `Premiums reach <b>${fmt(ens[2].value)}</b> M.TND in ${ens[2].year}`;
    document.getElementById("foot-meta").textContent = `Data to ${y}  ·  built ${D.meta.built}`;
    document.getElementById("chip-data").textContent = `Data up to ${y}, forecast to ${y + 3}`;
  }

  let current = null;
  function route() {
    const id = (location.hash.replace(/^#\//, "") || "overview");
    const page = Pages[id] || Pages.overview;
    current = Pages[id] ? id : "overview";
    document.querySelectorAll("#nav a").forEach((a) => a.classList.toggle("active", a.dataset.id === current));
    document.body.dataset.page = current;
    document.getElementById("page-title").textContent = page.title;
    document.getElementById("page-sub").textContent = page.subtitle;
    document.title = page.title + " · Tunisia Risk & Insurance Insights";
    const view = document.getElementById("view");
    view.replaceChildren();
    page.render(view);
    document.body.classList.remove("menu-open");
    window.scrollTo({ top: 0 });
  }

  document.getElementById("theme-btn").addEventListener("click", () => { setTheme(document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark"); route(); });
  document.getElementById("menu-btn").addEventListener("click", () => document.body.classList.toggle("menu-open"));
  document.getElementById("scrim").addEventListener("click", () => document.body.classList.remove("menu-open"));
  window.addEventListener("hashchange", route);

  const saved = new URLSearchParams(location.search).get("theme") || store.get("theme");
  setTheme(saved || (window.matchMedia && matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"));
  buildNav();
  route();
})();
