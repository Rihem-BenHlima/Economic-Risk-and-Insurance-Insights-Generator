/* The hero slideshow: Tunisian pictures that FADE in one over the other (not a scroll), each held for 2 seconds, with a slow zoom while visible, a caption, small dots
 * and a thin trend curve drawn over the top (solid = past, dashed = forecast, the 2027 value from the data). It pauses while the mouse is over it.
 * Pictures are the web-sized copies in img/ (make_slides.py); in the single-file build they travel inside the page as window.HERO_DATA.
 * Captions are written here: correct them if a place is named wrongly. The Roman ruins picture is AI-generated and is captioned as such. */
(function () {
  const SLIDES = [
    { file: "img/01-sousse.jpg", caption: "Sousse" },
    { file: "img/02-el-jem.jpg", caption: "El Jem amphitheatre" },
    { file: "img/03-sidi-bou-said.jpg", caption: "Sidi Bou Said" },
    { file: "img/04-ghorfas.jpg", caption: "Ghorfas, southern Tunisia" },
    { file: "img/05-tunis-rooftop.jpg", caption: "Rooftop in Tunis" },
    { file: "img/06-roman-ruins-ai.jpg", caption: "Roman temple ruins (AI-generated illustration)" },
    { file: "img/07-mountain-snow.jpg", caption: "Snow in a mountain town" },
  ];
  const HOLD_MS = 2000, FADE_MS = 900;                                             // wait time on each picture, and the length of the fade

  const overlay = () => {
    const f = window.DATA && DATA.forecast.forecasts.ensemble.premiums_total, last = f && f[f.length - 1];
    const text = last ? `${last.year}  ·  ${UI.fmt(last.value)} M.TND` : "forecast", w = 15.2 * text.length + 34;
    return `<svg class="hero-line" viewBox="0 0 1000 667" preserveAspectRatio="xMidYMin slice" aria-hidden="true">
      <defs><filter id="soft" x="-5%" y="-5%" width="110%" height="110%"><feDropShadow dx="0" dy="1.5" stdDeviation="2.2" flood-color="#06183a" flood-opacity=".55"/></filter></defs>
      <g filter="url(#soft)" fill="none" stroke="#fff" stroke-linecap="round" stroke-width="3.4">
        <path d="M60 176 C150 168 240 150 330 126" opacity=".95"/><path d="M330 126 C420 102 510 74 590 40" stroke-dasharray="3 11" stroke-width="4.2" opacity=".95"/>
      </g>
      <circle cx="330" cy="126" r="5.5" fill="#fff" filter="url(#soft)"/><circle cx="590" cy="40" r="15" fill="#fff" opacity=".28"/><circle cx="590" cy="40" r="7.5" fill="#fff" filter="url(#soft)"/>
      <rect x="64" y="62" width="${w}" height="40" rx="20" fill="rgba(8,24,56,.58)"/>
      <text x="${64 + w / 2}" y="89" text-anchor="middle" font-family="Segoe UI, system-ui, sans-serif" font-size="23" font-weight="600" fill="#fff">${text}</text>
    </svg>`;
  };

  function hero() {
    const src = (s) => (window.HERO_DATA && HERO_DATA[s.file]) || s.file;
    const imgs = SLIDES.map((s, i) => UI.h("img", { class: "slide" + (i === 0 ? " on" : ""), src: src(s), alt: s.caption, draggable: "false" }));
    const caption = UI.h("div", { class: "hero-caption" }, SLIDES[0].caption);
    const dots = SLIDES.map((s, i) => UI.h("button", { type: "button", class: "dot" + (i === 0 ? " on" : ""), "aria-label": "Show picture " + (i + 1) + ": " + s.caption, onclick: () => go(i, true) }));
    const root = UI.h("div", { class: "hero-art", role: "img", "aria-label": "Slideshow of places in Tunisia, with a rising forecast curve over it" }, imgs, UI.h("div", { html: overlay() }), caption, UI.h("div", { class: "hero-dots" }, dots));
    let cur = 0, timer = null, paused = false;

    function go(i, user) {
      imgs[cur].classList.remove("on"); dots[cur].classList.remove("on");
      cur = i;
      imgs[cur].classList.remove("on"); void imgs[cur].offsetWidth;               // restart the zoom animation of the picture that appears
      imgs[cur].classList.add("on"); dots[cur].classList.add("on");
      caption.textContent = SLIDES[cur].caption;
      if (user) schedule();
    }
    function schedule() {
      clearTimeout(timer);
      if (paused) return;
      timer = setTimeout(() => {
        if (!root.isConnected) return;                                            // the page was left: stop
        go((cur + 1) % SLIDES.length);
        schedule();
      }, FADE_MS + HOLD_MS);                                                      // the fade, then 2 seconds of waiting
    }
    root.addEventListener("mouseenter", () => { paused = true; clearTimeout(timer); });
    root.addEventListener("mouseleave", () => { paused = false; schedule(); });
    schedule();
    return root;
  }

  window.Art = { hero };
})();
