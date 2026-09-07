/* 文物数据库 · 检索前端逻辑 v1 */
"use strict";

const PAGE_SIZE = 24;
const $ = (s, el) => (el || document).querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

const LOGO_SVG = '<svg viewBox="0 0 48 48" fill="none" stroke="currentColor" aria-hidden="true">' +
  '<circle cx="24" cy="24" r="5" stroke-width="2.4"/>' +
  '<circle cx="24" cy="24" r="12.5" stroke-width="1.4" stroke-dasharray="0.1 5.4" stroke-linecap="round"/>' +
  '<g stroke-width="1.9">' +
  '<ellipse cx="24" cy="9.5" rx="4.6" ry="7"/><ellipse cx="24" cy="38.5" rx="4.6" ry="7"/>' +
  '<ellipse cx="9.5" cy="24" rx="7" ry="4.6"/><ellipse cx="38.5" cy="24" rx="7" ry="4.6"/>' +
  '<ellipse cx="13.6" cy="13.6" rx="4.4" ry="6.6" transform="rotate(-45 13.6 13.6)"/>' +
  '<ellipse cx="34.4" cy="34.4" rx="4.4" ry="6.6" transform="rotate(-45 34.4 34.4)"/>' +
  '<ellipse cx="34.4" cy="13.6" rx="4.4" ry="6.6" transform="rotate(45 34.4 13.6)"/>' +
  '<ellipse cx="13.6" cy="34.4" rx="4.4" ry="6.6" transform="rotate(45 13.6 34.4)"/></g></svg>';

const state = { q: "", dyn: "全部", cat: "全部", sort: "default", page: 1, index: null };

/* ---------- 索引加载（gz 优先，明文兜底） ---------- */
async function loadIndex() {
  if ("DecompressionStream" in window) {
    try {
      const buf = await (await fetch("data/index.json.gz", { cache: "force-cache" })).arrayBuffer();
      const stream = new Blob([buf]).stream().pipeThrough(new DecompressionStream("gzip"));
      return JSON.parse(await new Response(stream).text());
    } catch (e) { /* fallthrough */ }
  }
  const r = await fetch("data/index.json");
  if (!r.ok) throw new Error("HTTP " + r.status);
  return r.json();
}

/* ---------- 筛选与排序 ---------- */
let _blobCache = null;
function blobs() {
  if (!_blobCache) _blobCache = state.index.items.map(x =>
    (x.name + " " + x.alias + " " + x.dyn + " " + x.cat + " " + x.mat + " " + x.inv + " " + (x.tags || []).join(" ")).toLowerCase());
  return _blobCache;
}

function filtered() {
  const q = state.q.trim().toLowerCase();
  let list = state.index.items;
  if (state.dyn !== "全部") list = list.filter(x => x.dyn === state.dyn);
  if (state.cat !== "全部") list = list.filter(x => x.cat === state.cat);
  if (q) { const bl = blobs(); list = list.filter((x, i) => bl[i].includes(q)); }
  if (state.sort === "year_asc") list = [...list].sort((a, b) => (a.y0 ?? 9e9) - (b.y0 ?? 9e9));
  if (state.sort === "year_desc") list = [...list].sort((a, b) => (b.y0 ?? -9e9) - (a.y0 ?? -9e9));
  return list;
}

/* ---------- 渲染 ---------- */
function renderChips() {
  const f = state.index.facets;
  const top = (arr, n) => arr.slice(0, n);
  $("#dynChips").innerHTML = [{ k: "全部", c: state.index.total }, ...top(f.dynasties, 10)]
    .map(o => `<button class="chip${o.k === state.dyn ? " on" : ""}" data-dyn="${esc(o.k)}">${esc(o.k)}<span class="c">${o.c}</span></button>`).join("");
  $("#catChips").innerHTML = [{ k: "全部", c: state.index.total }, ...top(f.cats, 10)]
    .map(o => `<button class="chip${o.k === state.cat ? " on" : ""}" data-cat="${esc(o.k)}">${esc(o.k)}<span class="c">${o.c}</span></button>`).join("");
}

function yearLabel(x) { return x.y0 ? `${x.y0}${x.y1 && x.y1 !== x.y0 ? "–" + x.y1 : ""} 年` : ""; }

function renderGrid() {
  const list = filtered();
  const pages = Math.max(1, Math.ceil(list.length / PAGE_SIZE));
  if (state.page > pages) state.page = 1;
  const slice = list.slice((state.page - 1) * PAGE_SIZE, state.page * PAGE_SIZE);
  $("#cnt").textContent = `共 ${list.length.toLocaleString()} 件`;
  const grid = $("#grid");
  if (!slice.length) {
    grid.innerHTML = `<div class="status">${LOGO_SVG.replace("<svg", '<svg class="flower"')}<p>未检索到相关文物</p><p style="font-size:12.5px;margin-top:6px">换个关键词试试，或清除筛选条件</p></div>`;
    $("#pager").innerHTML = ""; return;
  }
  grid.innerHTML = slice.map(x => `
    <article class="card" data-id="${esc(x.id)}" tabindex="0" role="button" aria-label="${esc(x.name)}">
      <div class="ph">${x.img
        ? `<img loading="lazy" src="${esc(x.img)}" alt="${esc(x.name)}" onerror="this.parentElement.innerHTML='<span class=\\'nopic\\'>${LOGO_SVG.replace(/"/g, "&quot;")}</span>'">`
        : `<span class="nopic">${LOGO_SVG.replace(/"/g, "&quot;")}</span>`}
        <span class="badge">${esc(x.dyn)}</span></div>
      <div class="bd"><h3>${esc(x.name)}</h3>
        <div class="mu">${esc(x.mu)}${yearLabel(x) ? " · " + yearLabel(x) : ""}</div>
        <div class="tg">${(x.tags || []).slice(0, 3).map(t => `<i>${esc(t)}</i>`).join("")}</div></div>
    </article>`).join("");
  const cards = grid.querySelectorAll(".card");
  cards.forEach((el, i) => {
    el.style.transitionDelay = Math.min(i * 30, 300) + "ms";
    requestAnimationFrame(() => requestAnimationFrame(() => { el.classList.add("in"); el.style.transitionDelay = ""; }));
  });
  renderPager(pages);
}

function renderPager(pages) {
  const p = state.page, el = $("#pager");
  const nums = new Set([1, 2, p - 1, p, p + 1, pages]);
  let html = `<button data-pg="${p - 1}" ${p <= 1 ? "disabled" : ""}>‹</button>`;
  let prev = 0;
  for (const n of [...nums].filter(n => n >= 1 && n <= pages).sort((a, b) => a - b)) {
    if (n - prev > 1) html += `<span class="dots">…</span>`;
    html += `<button data-pg="${n}" class="${n === p ? "cur" : ""}">${n}</button>`;
    prev = n;
  }
  html += `<button data-pg="${p + 1}" ${p >= pages ? "disabled" : ""}>›</button>`;
  el.innerHTML = pages > 1 ? html : "";
}

/* ---------- 详情弹层 ---------- */
function openDetail(id) {
  const x = state.index.items.find(i => i.id === id);
  if (!x) return;
  const fig = $("#mFig");
  fig.innerHTML = (x.img ? `<img src="${esc(x.img)}" alt="${esc(x.name)}" loading="lazy">`
    : `<span class="nopic">${LOGO_SVG.replace(/"/g, "&quot;")}</span>`)
    + `<button class="close" aria-label="关闭" onclick="closeDetail()">✕</button><span class="badge">${esc(x.dyn)}</span>`;
  $("#mName").textContent = x.name;
  $("#mAlias").textContent = x.alias ? "又名：" + x.alias : "";
  $("#mDyn").innerHTML = `<a href="#" onclick="filterDyn('${esc(x.dyn).replace(/'/g, "")}');return false">${esc(x.dyn)}</a>`;
  $("#mYear").textContent = yearLabel(x) || "—";
  $("#mCat").textContent = x.cat || "—";
  $("#mMat").textContent = x.mat || "—";
  $("#mDim").textContent = x.dim || "—";
  $("#mMu").textContent = x.mu || "—";
  $("#mInv").textContent = x.inv || "—";
  $("#mDesc").textContent = x.desc || "";
  $("#mTags").innerHTML = (x.tags || []).map(t => `<i>${esc(t)}</i>`).join("");
  $("#mSrc").onclick = () => x.url && window.open(x.url, "_blank", "noopener");
  $("#mCopy").onclick = () => copyCitation(x);
  $("#mLic").textContent = x.lic;
  $("#detail").classList.add("open");
  document.body.style.overflow = "hidden";
  history.replaceState(null, "", "#r=" + encodeURIComponent(x.id));
}
function closeDetail() {
  $("#detail").classList.remove("open");
  document.body.style.overflow = "";
  history.replaceState(null, "", location.pathname + location.search);
}
function filterDyn(d) { closeDetail(); setDyn(d); window.scrollTo({ top: 0, behavior: "smooth" }); }

function copyCitation(x) {
  const yr = yearLabel(x);
  const text = `《${x.name}》，${x.dyn}${yr ? "（" + yr + "）" : ""}，${x.mu}藏，馆藏号 ${x.inv}。${x.url}（${x.lic}）`;
  const done = () => toast("引用已复制到剪贴板");
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(done, () => fallbackCopy(text, done));
  } else fallbackCopy(text, done);
}
function fallbackCopy(text, done) {
  const ta = document.createElement("textarea");
  ta.value = text; ta.style.position = "fixed"; ta.style.opacity = "0";
  document.body.appendChild(ta); ta.select();
  try { document.execCommand("copy"); done(); } catch (e) { toast("复制失败，请手动复制"); }
  ta.remove();
}
let toastTimer;
function toast(msg) {
  const t = $("#toast"); t.textContent = msg; t.classList.add("show");
  clearTimeout(toastTimer); toastTimer = setTimeout(() => t.classList.remove("show"), 2200);
}

/* ---------- 事件绑定 ---------- */
function setDyn(d) { state.dyn = d; state.page = 1; renderChips(); renderGrid(); }
function setCat(c) { state.cat = c; state.page = 1; renderChips(); renderGrid(); }

function bind() {
  let deb;
  $("#q").addEventListener("input", e => {
    clearTimeout(deb);
    deb = setTimeout(() => { state.q = e.target.value; state.page = 1; renderGrid(); }, 160);
  });
  document.body.addEventListener("click", e => {
    const dyn = e.target.closest("[data-dyn]");
    if (dyn) return setDyn(dyn.dataset.dyn);
    const cat = e.target.closest("[data-cat]");
    if (cat) return setCat(cat.dataset.cat);
    const pg = e.target.closest("[data-pg]");
    if (pg && !pg.disabled) { state.page = +pg.dataset.pg; renderGrid(); $("#listTop").scrollIntoView({ behavior: "smooth" }); return; }
    const card = e.target.closest(".card[data-id]");
    if (card) return openDetail(card.dataset.id);
  });
  document.body.addEventListener("keydown", e => {
    if (e.key === "Enter" && e.target.classList?.contains("card")) openDetail(e.target.dataset.id);
    if (e.key === "Escape") closeDetail();
  });
  $("#detail").addEventListener("click", e => { if (e.target.id === "detail") closeDetail(); });
  $("#sort").addEventListener("change", e => { state.sort = e.target.value; state.page = 1; renderGrid(); });
  window.addEventListener("hashchange", () => {
    const m = location.hash.match(/^#r=(.+)$/);
    if (m) openDetail(decodeURIComponent(m[1]));
  });
}

/* ---------- 启动 ---------- */
(async function init() {
  bind();
  try {
    state.index = await loadIndex();
    const f = state.index.facets;
    $("#totalN").textContent = state.index.total.toLocaleString();
    $("#muN").textContent = Object.keys(state.index.museums).length.toLocaleString();
    $("#genDate").textContent = state.index.generated;
    renderChips(); renderGrid();
    const m = location.hash.match(/^#r=(.+)$/);
    if (m) openDetail(decodeURIComponent(m[1]));
  } catch (e) {
    $("#grid").innerHTML = `<div class="status"><p>索引加载失败（${esc(e.message)}）</p><p style="font-size:12.5px;margin-top:6px">请刷新重试；若持续失败请到 GitHub 提交 issue</p></div>`;
  }
})();
