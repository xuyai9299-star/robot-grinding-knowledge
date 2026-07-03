/**
 * 三层浏览：分类树 → 论文列表 → 详情（含 URL/DOI/关键词）
 * 依赖：papers_index.json, mindmap_stats.json, category_index.json（可选）
 */
const state = {
  papersById: {},
  stats: null,
  categoryIndex: null,
  currentIds: [],
  selectedId: null,
  searchQuery: "",
};

async function loadJson(url) {
  const r = await fetch(url, { cache: "no-store" });
  if (!r.ok) throw new Error(`${url} → ${r.status}`);
  return r.json();
}

function paper(id) {
  return state.papersById[String(id)];
}

function doiLink(doi) {
  if (!doi) return "";
  const d = doi.replace(/^https?:\/\/(doi\.org\/)?/i, "");
  return `https://doi.org/${d}`;
}

function extLink(p) {
  if (p.url) return p.url;
  if (p.doi) return doiLink(p.doi);
  return "";
}

function renderDetail(id) {
  const p = paper(id);
  const el = document.getElementById("detailPanel");
  if (!p) {
    el.innerHTML = "<p class='text-danger'>未找到论文数据</p>";
    return;
  }
  state.selectedId = id;
  document.querySelectorAll(".paper-item").forEach((n) => {
    n.classList.toggle("active", Number(n.dataset.id) === id);
  });

  const link = extLink(p);
  const kws = (p.keywords || [])
    .map((k) => `<span class="kw-tag">${escapeHtml(k)}</span>`)
    .join("");
  const tags = (p.hierarchy_tags || [])
    .map((t) => `<span class="badge text-bg-secondary me-1">${escapeHtml(t)}</span>`)
    .join("");

  el.innerHTML = `
    <div class="mb-2 text-muted small">#${p.id} · ${escapeHtml(p.school || "")} · ${escapeHtml(p.year || "")}</div>
    <h3>${escapeHtml(p.title)}</h3>
    <p class="small text-muted mb-2">${escapeHtml(p.authors || "")}</p>
    <p class="small mb-2"><em>${escapeHtml(p.venue || "")}</em></p>
    <div class="path-line mb-2">📂 ${escapeHtml(p.mindmap_path || "")}</div>
    <div class="mb-2">${tags}</div>
    <div class="mb-3">
      ${link ? `<a class="btn btn-primary btn-sm me-2" href="${escapeAttr(link)}" target="_blank" rel="noopener">打开论文原文链接</a>` : ""}
      ${p.doi ? `<a class="btn btn-outline-secondary btn-sm" href="${escapeAttr(doiLink(p.doi))}" target="_blank" rel="noopener">DOI</a>` : ""}
    </div>
    <h4 class="h6">中文摘要</h4>
    <p class="small">${escapeHtml(p.summary_zh || "（暂无中文摘要）")}</p>
    <h4 class="h6 mt-3">关键词</h4>
    <div>${kws || "<span class='text-muted'>无</span>"}</div>
  `;
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function escapeAttr(s) {
  return escapeHtml(s).replace(/'/g, "&#39;");
}

function renderPaperList(ids, title) {
  state.currentIds = ids;
  document.getElementById("listTitle").textContent = title;
  document.getElementById("listCount").textContent = String(ids.length);

  const q = state.searchQuery.toLowerCase();
  let filtered = ids;
  if (q) {
    filtered = ids.filter((id) => {
      const p = paper(id);
      if (!p) return false;
      const blob = [p.title, p.summary_zh, (p.keywords || []).join(" "), p.school, p.mindmap_path]
        .join(" ")
        .toLowerCase();
      return blob.includes(q);
    });
  }

  const box = document.getElementById("paperList");
  if (!filtered.length) {
    box.innerHTML = "<p class='text-muted small'>该分类下暂无论文，或搜索无匹配。</p>";
    return;
  }

  box.innerHTML = filtered
    .map((id) => {
      const p = paper(id);
      if (!p) return "";
      const link = extLink(p);
      return `
        <div class="paper-item ${state.selectedId === id ? "active" : ""}" data-id="${id}">
          <div class="pid">#${id} ${escapeHtml(p.school || "")} · ${escapeHtml(p.year || "")}</div>
          <div class="ptitle">${escapeHtml(p.title)}</div>
          <div class="pmeta">${escapeHtml((p.keywords || []).slice(0, 4).join(" · "))}</div>
          ${link ? `<div class="pmeta"><a href="${escapeAttr(link)}" target="_blank" rel="noopener" onclick="event.stopPropagation()">原文 ↗</a></div>` : ""}
        </div>
      `;
    })
    .join("");

  box.querySelectorAll(".paper-item").forEach((node) => {
    node.addEventListener("click", () => renderDetail(Number(node.dataset.id)));
  });

  if (filtered.length && !filtered.includes(state.selectedId)) {
    renderDetail(filtered[0]);
  }
}

function setActiveTree(el) {
  document.querySelectorAll(".tree-item.active, .cat-btn.active").forEach((n) => n.classList.remove("active"));
  if (el) el.classList.add("active");
}

function renderProcessTree(nodes, level = 0) {
  let html = "";
  for (const node of nodes) {
    const ids = node.paper_ids || [];
    const hasChildren = node.children && node.children.length;
    const pathLabel = node.path || node.name;
    html += `<div class="tree-node">`;
    html += `<div class="tree-item" data-ids='${JSON.stringify(ids)}' data-title="${escapeAttr(pathLabel)}">
      <span>📌 ${escapeHtml(node.name)}</span>
      <span class="badge text-bg-light text-dark">${node.count}</span>
    </div>`;
    if (hasChildren) html += renderProcessTree(node.children, level + 1);
    html += `</div>`;
  }
  return html;
}

function bindTreeClicks(root) {
  root.querySelectorAll(".tree-item").forEach((el) => {
    el.addEventListener("click", (e) => {
      e.stopPropagation();
      const ids = JSON.parse(el.dataset.ids || "[]");
      const title = el.dataset.title || "论文列表";
      setActiveTree(el);
      renderPaperList(ids, title);
    });
  });
}

function renderAppMatHtml() {
  return (state.stats.application || []).map(function(app){
    return '<button class="cat-btn tree-item" data-ids=\''+JSON.stringify(app.paper_ids||[])+'\' data-title="应用场景 · '+escapeAttr(app.name)+'"><span>'+escapeHtml(app.name)+'</span><span class="badge">'+app.count+'</span></button>';
  }).join("");
}
function renderMatHtml() {
  return (state.stats.material || []).map(function(mat){
    return '<button class="cat-btn tree-item" data-ids=\''+JSON.stringify(mat.paper_ids||[])+'\' data-title="加工材料 · '+escapeAttr(mat.name)+'"><span>'+escapeHtml(mat.name)+'</span><span class="badge">'+mat.count+'</span></button>';
  }).join("");
}

function bindCatBtns() {
  document.querySelectorAll(".cat-btn").forEach(function(btn){
    btn.addEventListener("click",function(){
      setActiveTree(btn);
      renderPaperList(JSON.parse(btn.dataset.ids||"[]"),btn.dataset.title);
    });
  });
}

// Tab 切换
document.getElementById("treeTabs").addEventListener("click",function(e){
  var btn=e.target.closest("button[data-tab]");
  if(!btn) return;
  document.querySelectorAll("#treeTabs button").forEach(function(b){b.classList.remove("on")});
  btn.classList.add("on");
  var tc=document.getElementById("treeContent");
  if(btn.dataset.tab==="process"){tc.innerHTML=renderProcessTree(state.stats.process_tree||[]);bindTreeClicks(tc)}
  else if(btn.dataset.tab==="app"){tc.innerHTML=state._appHtml;bindCatBtns()}
  else{tc.innerHTML=state._matHtml;bindCatBtns()}
});

async function init() {
  try {
    const [index, stats] = await Promise.all([
      loadJson("papers_index.json"),
      loadJson("mindmap_stats.json"),
    ]);
    state.papersById = index.by_id || {};
    state.stats = stats;

    try {
      state.categoryIndex = await loadJson("category_index.json");
    } catch {
      state.categoryIndex = null;
    }

    // 更新 hero 统计
    var hpc=document.getElementById("statPapers");if(hpc) hpc.textContent=stats.total_papers;
    var cnt=0,yrMin=9999,yrMax=0;
    Object.values(state.papersById).forEach(function(p){cnt++;var y=parseInt(p.year);if(y){if(y<yrMin)yrMin=y;if(y>yrMax)yrMax=y}});
    var sy=document.getElementById("statYears");if(sy&&yrMin<9999) sy.textContent=yrMin+"-"+yrMax;
    fetch("conferences/conferences.json",{cache:"no-store"}).then(function(r){return r.json()}).then(function(d){
      var jc=document.getElementById("statVenues");if(jc) jc.textContent=(d.total_journals||0)+(d.total_conferences||0);
    }).catch(function(){});

    // 渲染分类树
    var treeContent=document.getElementById("treeContent");
    treeContent.innerHTML = renderProcessTree(stats.process_tree || []);
    bindTreeClicks(treeContent);
    // 缓存 app/mat 数据以便 tab 切换
    state._appHtml = renderAppMatHtml();
    state._matHtml = renderMatHtml();

    document.getElementById("paperSearch").addEventListener("input", (e) => {
      state.searchQuery = e.target.value.trim();
      if (state.currentIds.length) {
        const title = document.getElementById("listTitle").textContent;
        renderPaperList(state.currentIds, title);
      } else {
        const allIds = Object.keys(state.papersById).map(Number).sort((a, b) => a - b);
        renderPaperList(allIds, "全部论文（搜索）");
      }
    });

    const allIds = Object.keys(state.papersById).map(Number).sort((a, b) => a - b);
    renderPaperList(allIds, "全部论文");
  } catch (err) {
    document.getElementById("subtitle").textContent =
      "加载失败，请确认已运行 ingest.py 并部署 papers_index.json / mindmap_stats.json";
    console.error(err);
  }
}

init();
