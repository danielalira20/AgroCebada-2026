/* Guía de uso (tour): difumina la pantalla y deja nítido lo que se explica en cada paso.
   Se instala una sola vez; se abre sola la primera vez que se entra a cada vista y con el botón «?» del mapa.
   Los textos están aquí; los estilos (.guia-*) en assets/css/tema.css. */
(() => {
  if (window.__guiaAgro) return;
  window.__guiaAgro = true;

  const ICONO = {
    parcela: '<path d="M12 21s-7-5.2-7-11a7 7 0 1 1 14 0c0 5.8-7 11-7 11z"/><circle cx="12" cy="10" r="2.5"/>',
    mapa: '<path d="M9 4 3 6v14l6-2 6 2 6-2V4l-6 2-6-2z"/><path d="M9 4v14M15 6v14"/>',
    capas: '<path d="m12 3 9 5-9 5-9-5 9-5z"/><path d="m3 13 9 5 9-5"/>',
    datos: '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
    ficha: '<path d="M14 3H6a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8z"/><path d="M14 3v5h5M9 13h6M9 17h6"/>',
    calculadora: '<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M8 7h8M8 12h2M12 12h2M16 12h0M8 16h2M12 16h2M16 16h0"/>',
    filtros: '<path d="M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12M20 18h0"/><circle cx="16" cy="6" r="2"/><circle cx="10" cy="12" r="2"/><circle cx="18" cy="18" r="2"/>',
    resumen: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
    vista: '<path d="M3 12h13M12 6l6 6-6 6M21 4v16"/>',
    pestanas: '<path d="M3 8a2 2 0 0 1 2-2h5l2 2h7a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
  };
  const MAPA = '[class*="st-key-hero_"] [data-testid="stDeckGlJsonChart"]';
  const COLOR = ["Mira el mapa en 3D o desde arriba y coloréalo por rendimiento o por confianza de la estimación.",
                 "Colorear por confianza muestra con color y palabra qué tanto respaldo tiene cada estimación."];

  const PASOS = {
    agricultor: [
      {sel: ".st-key-glass_panel", icono: "parcela", lado: ["right"], titulo: "Elige tu parcela",
       texto: "Escoge tu municipio y tu parcela. Aquí ves cuántas toneladas por hectárea se estiman, qué tanta confianza tiene la cifra y cómo se calculó."},
      {sel: MAPA, icono: "mapa", lado: ["center"], titulo: "Explora el mapa",
       texto: "Tu parcela aparece resaltada y las vecinas alrededor. Haz clic en otra para verla, arrastra para moverte y usa los botones + y − para acercar."},
      {sel: ".st-key-glass_leyenda", icono: "capas", lado: ["left", "top"], titulo: "Cambia cómo ver el mapa", texto: COLOR.join(" ")},
      {sel: ".st-key-glass_chips", icono: "datos", lado: ["left", "bottom"], titulo: "Datos de tu parcela",
       texto: "Área, altitud, lluvia de abril a octubre y el mes de más verdor, para darle contexto a la estimación."},
      {sel: ".st-key-ficha_agricultor", icono: "ficha", lado: ["right", "top"], titulo: "Llévate tu ficha",
       texto: "Descarga en PDF, en una página, la estimación de tu parcela con su rango, su mapa, su verdor y su clima."},
      {sel: ".st-key-glass_calculadora", icono: "calculadora", lado: ["top", "bottom"], titulo: "¿Me alcanza?",
       texto: "Escribe tu precio por tonelada y tu costo por hectárea para ver cuánto te dejaría la cosecha. Es una guía, no un dictamen de crédito."},
    ],
    analista: [
      {sel: ".st-key-glass_filtros", icono: "filtros", lado: ["left", "bottom"], titulo: "Filtra lo que ves",
       texto: "Muestra todas las parcelas, sólo las 59 por estimar o las 138 con cosecha. Limita por municipio o busca una parcela por su ID."},
      {sel: MAPA, icono: "mapa", lado: ["center"], titulo: "Explora y selecciona",
       texto: "Haz clic en una parcela para ver su estimación y elegirla. Si la buscas por ID, el mapa se acerca a ella."},
      {sel: ".st-key-glass_leyenda", icono: "capas", lado: ["left", "top"], titulo: "Cambia cómo ver el mapa", texto: COLOR.join(" ")},
      {sel: ".st-key-glass_kpis", icono: "resumen", lado: ["right", "bottom"], titulo: "Resumen del modelo",
       texto: "Parcelas estimadas, estimación promedio y el error del modelo (MAE y R²) en la validación sin respaldo. Desde aquí descargas las cifras."},
      {sel: ".st-key-glass_top", icono: "vista", lado: ["bottom"], titulo: "Vista, modelo y satélite",
       texto: "Cambia entre Agricultor y Analista, y entre la mediana (modelo oficial) y la media (referencia). Apaga el satélite si tu conexión es lenta."},
      {sel: '[data-testid="stTabs"] [role="tablist"]', icono: "pestanas", lado: ["top", "bottom"], titulo: "Siete pestañas de análisis",
       texto: "Cartera por municipio, las 59 estimaciones, ficha técnica, validación, evidencia, método y límites, y el análisis de tus propios datos."},
    ],
  };

  const vistaActual = () => document.querySelector('[class*="st-key-hero_analista"]') ? "analista"
    : document.querySelector('[class*="st-key-hero_agricultor"]') ? "agricultor" : null;
  const hayDialogo = () => !!document.querySelector('[role="dialog"]:not(.guia-tarjeta)');
  const svg = (n) => `<svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONO[n] || ""}</svg>`;
  const vistoKey = (v) => "agrocebada_guia_" + v;
  const marcarVisto = (v) => { try { localStorage.setItem(vistoKey(v), "1"); } catch (e) { /* sin almacenamiento */ } };
  const yaVisto = (v) => { try { return localStorage.getItem(vistoKey(v)) === "1"; } catch (e) { return true; } };

  let activo = null;      // {vista, pasos, i, velo, aro, tarjeta, raf}
  const HUECO = 8, RADIO = 16, MARGEN = 14;

  function crear(tag, clase, attrs = {}) {
    const e = document.createElement(tag); e.className = clase;
    Object.entries(attrs).forEach(([k, v]) => e.setAttribute(k, v));
    return e;
  }

  function mascara(r) {      // velo con un hueco redondeado: lo de fuera se difumina, lo de dentro queda nítido
    const w = innerWidth, h = innerHeight, x = r.left - HUECO, y = r.top - HUECO, a = r.width + 2 * HUECO, b = r.height + 2 * HUECO;
    const k = Math.min(RADIO, a / 2, b / 2);
    const hueco = `M${x + k} ${y}h${a - 2 * k}a${k} ${k} 0 0 1 ${k} ${k}v${b - 2 * k}a${k} ${k} 0 0 1 -${k} ${k}h-${a - 2 * k}a${k} ${k} 0 0 1 -${k} -${k}v-${b - 2 * k}a${k} ${k} 0 0 1 ${k} -${k}z`;
    const s = `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}"><path fill-rule="evenodd" d="M0 0H${w}V${h}H0z ${hueco}"/></svg>`;
    return `url("data:image/svg+xml,${encodeURIComponent(s)}")`;
  }

  function colocar() {
    if (!activo) return;
    const paso = activo.pasos[activo.i], el = document.querySelector(paso.sel);
    if (!el) return;
    const r = el.getBoundingClientRect(), t = activo.tarjeta;
    const m = mascara(r);
    activo.velo.style.webkitMaskImage = activo.velo.style.maskImage = m;
    Object.assign(activo.aro.style, {left: r.left - HUECO + "px", top: r.top - HUECO + "px",
      width: r.width + 2 * HUECO + "px", height: r.height + 2 * HUECO + "px"});
    if (innerWidth < 700) { t.style.left = t.style.top = ""; t.classList.add("guia-hoja"); return; }
    t.classList.remove("guia-hoja");
    const w = t.offsetWidth, h = t.offsetHeight, g = HUECO + MARGEN;
    const opciones = {
      right: [r.right + g, r.top], left: [r.left - g - w, r.top], bottom: [r.left, r.bottom + g], top: [r.left, r.top - g - h],
      center: [r.left + (r.width - w) / 2, r.top + (r.height - h) / 2],
    };
    const cabe = ([x, y]) => x >= MARGEN && y >= MARGEN && x + w <= innerWidth - MARGEN && y + h <= innerHeight - MARGEN;
    let pos = null;
    for (const lado of [...paso.lado, "right", "left", "bottom", "top"]) if (cabe(opciones[lado])) { pos = opciones[lado]; break; }
    if (!pos) pos = [Math.max(MARGEN, Math.min(innerWidth - w - MARGEN, r.left)), Math.max(MARGEN, innerHeight - h - MARGEN)];
    t.style.left = Math.max(MARGEN, Math.min(innerWidth - w - MARGEN, pos[0])) + "px";
    t.style.top = Math.max(MARGEN, Math.min(innerHeight - h - MARGEN, pos[1])) + "px";
  }

  function dibujarTarjeta() {
    const {pasos, i, tarjeta: t} = activo, p = pasos[i], ultimo = i === pasos.length - 1;
    t.innerHTML = `
      <div class="guia-cab"><span class="guia-etiqueta">Guía de uso</span>
        <button class="guia-x" type="button" aria-label="Cerrar guía">×</button></div>
      <div class="guia-icono">${svg(p.icono)}<span class="guia-barras"><i></i><i></i><i></i></span></div>
      <h3 id="guia-titulo">${p.titulo}</h3><p>${p.texto}</p>
      <div class="guia-pie"><span class="guia-cuenta">${i + 1} de ${pasos.length}</span>
        <span class="guia-puntos">${pasos.map((_, k) => `<i class="${k === i ? "on" : ""}"></i>`).join("")}</span></div>
      <div class="guia-botones">${i > 0 ? '<button class="guia-sec" type="button" data-guia="atras">Anterior</button>' : ""}
        <button class="guia-pri" type="button" data-guia="${ultimo ? "fin" : "sig"}">${ultimo ? "Finalizar ✓" : "Siguiente →"}</button></div>`;
    t.querySelector(".guia-pri").focus({preventScroll: true});
  }

  function mostrar(i) {
    activo.i = i;
    let paso = activo.pasos[i], el = document.querySelector(paso.sel);
    if (!el) {      // si falta lo que se explica, se salta al siguiente paso
      const sig = activo.pasos.findIndex((p, k) => k > i && document.querySelector(p.sel));
      if (sig < 0) return cerrar(); return mostrar(sig);
    }
    dibujarTarjeta();
    const r = el.getBoundingClientRect();
    if (innerWidth < 700) {      // en el celular la tarjeta es una hoja abajo: lo que se explica sube a la parte de arriba
      el.style.scrollMarginTop = "16px"; el.scrollIntoView({block: "start", behavior: "instant"});
    } else if (r.top < 0 || r.bottom > innerHeight) el.scrollIntoView({block: "center", behavior: "instant"});
    colocar();
  }

  function cerrar() {
    if (!activo) return;
    cancelAnimationFrame(activo.raf);
    [activo.velo, activo.aro, activo.tarjeta].forEach((e) => e.remove());
    document.removeEventListener("keydown", teclas, true);
    document.body.classList.remove("guia-abierta");
    if (activo.previo && document.contains(activo.previo)) activo.previo.focus({preventScroll: true});
    activo = null;
  }

  function teclas(ev) {
    if (!activo) return;
    if (ev.key === "Escape") { ev.preventDefault(); cerrar(); }
    else if (ev.key === "ArrowRight") { ev.preventDefault(); if (activo.i < activo.pasos.length - 1) mostrar(activo.i + 1); }
    else if (ev.key === "ArrowLeft") { ev.preventDefault(); if (activo.i > 0) mostrar(activo.i - 1); }
  }

  function abrir(forzada) {
    const vista = vistaActual();
    if (!vista || activo) return;
    marcarVisto(vista);
    const velo = crear("div", "guia-velo"), aro = crear("div", "guia-aro");
    const tarjeta = crear("div", "guia-tarjeta", {role: "dialog", "aria-modal": "true", "aria-labelledby": "guia-titulo"});
    document.body.append(velo, aro, tarjeta);
    document.body.classList.add("guia-abierta");
    activo = {vista, pasos: PASOS[vista], i: 0, velo, aro, tarjeta, previo: document.activeElement, raf: 0};
    velo.addEventListener("click", cerrar);
    tarjeta.addEventListener("click", (ev) => {
      const b = ev.target.closest("button"); if (!b) return;
      if (b.classList.contains("guia-x") || b.dataset.guia === "fin") cerrar();
      else if (b.dataset.guia === "sig") mostrar(activo.i + 1);
      else if (b.dataset.guia === "atras") mostrar(activo.i - 1);
    });
    document.addEventListener("keydown", teclas, true);
    const bucle = () => { if (!activo) return; colocar(); activo.raf = requestAnimationFrame(bucle); };
    mostrar(0); activo.raf = requestAnimationFrame(bucle);
  }

  // botón «?» fijo sobre el mapa, al lado de los botones de zoom
  const boton = crear("button", "guia-ayuda", {type: "button", "aria-label": "Abrir la guía de uso", title: "Guía de uso"});
  boton.textContent = "?";
  boton.addEventListener("click", () => abrir(true));
  document.body.append(boton);

  let listoDesde = 0;
  function vigilar() {
    const vista = vistaActual(), mapa = document.querySelector(MAPA);
    const r = mapa && mapa.getBoundingClientRect();
    const visible = !!vista && !!r && r.width > 100 && r.bottom > 80 && r.top < innerHeight - 60 && !hayDialogo() && !activo;
    boton.style.display = visible && innerWidth >= 901 ? "flex" : "none";
    if (visible) { boton.style.left = r.left + 16 + 40 + "px"; boton.style.top = r.top + 16 + "px"; }
    if (!vista || !r || hayDialogo()) { listoDesde = 0; return; }
    if (!activo && !yaVisto(vista)) {      // primera vez en esta vista: se abre sola cuando el mapa lleva un momento en pantalla
      listoDesde = listoDesde || Date.now();
      if (Date.now() - listoDesde > 1800) abrir(false);
    }
  }
  setInterval(vigilar, 400);
  addEventListener("scroll", vigilar, {passive: true});
  addEventListener("resize", vigilar);
})();
