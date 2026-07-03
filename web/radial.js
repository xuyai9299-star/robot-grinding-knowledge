/**
 * radial.js v2 — ECharts 径向思维导图
 * 修复：空标签、数据校验、搜索高亮
 */
(function () {
  "use strict";

  var papersById = {};
  var mindmapsFive = null;
  var chart = null;
  var currentKey = "process_tree";
  var allTreeData = {};

  // DOM
  var chartDom = document.getElementById("chart");
  var detailPanel = document.getElementById("detailPanel");
  var detailContent = document.getElementById("detailContent");
  var searchInput = document.getElementById("searchInput");
  var searchResults = document.getElementById("searchResults");

  // ECharts 初始化
  chart = echarts.init(chartDom);
  window.addEventListener("resize", function () { chart.resize(); });

  // ---- 辅助 ----
  function extLink(p) {
    if (!p) return "";
    if (p.url) return p.url;
    var d = String(p.doi || "").replace(/^https?:\/\/(doi\.org\/)?/i, "");
    return d ? "https://doi.org/" + d : "";
  }
  function esc(s) { return String(s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;"); }

  // 论文标签（确保永不返回空字符串）
  function paperLabel(pid) {
    var p = papersById[String(pid)] || papersById[pid];
    if (!p) return "#" + pid;
    var kws = p.keywords || p.keywords_zh || [];
    if (kws.length > 0) {
      var kw = kws[0];
      if (kw.length > 6) kw = kw.substring(0, 5) + "…";
      return kw || "#" + pid;
    }
    var t = p.title_en || p.title || "";
    if (t.length > 12) t = t.substring(0, 10) + "…";
    return t || "#" + pid;
  }

  function paperTooltip(pid) {
    var p = papersById[String(pid)] || papersById[pid];
    if (!p) return "#" + pid;
    var cn = (p.keywords_zh || p.keywords || []).join(" · ");
    var en = (p.title_en || p.title || "").substring(0, 80);
    return "<b>#" + p.id + "</b> " + esc(en) +
      "<br/><span style='color:#f59e0b'>" + esc(cn||"无关键词") + "</span>" +
      "<br/><span style='color:#94a3b8;font-size:11px'>" + esc(p.school||"") + " · " + esc(p.year||"") + "</span>";
  }

  // ---- 构建树数据（加防护） ----

  function safeName(s) { return String(s || "(未命名)").trim() || "(未命名)"; }

  function buildProcessTreeData() {
    var tree = mindmapsFive && mindmapsFive.process_tree;
    if (!tree || !tree.length) return null;
    return {
      name: "机器人柔性磨削",
      itemStyle: { color: "#f59e0b" },
      children: tree.map(function (l1) {
        return {
          name: safeName(l1.name),
          itemStyle: { color: "#f97316" },
          collapsed: true,
          children: (l1.children || []).map(function (l2) {
            return {
              name: safeName(l2.name),
              itemStyle: { color: "#06b6d4" },
              collapsed: true,
              children: (l2.children || []).map(function (l3) {
                var paperChildren = (l3.paper_ids || []).map(function (pid) {
                  return {
                    name: paperLabel(pid),
                    value: pid,
                    paperId: pid,
                    symbol: "circle",
                    symbolSize: 6,
                    itemStyle: { color: "#818cf8" },
                    label: { fontSize: 9, color:"#a5b4fc" },
                  };
                });
                return {
                  name: safeName(l3.name),
                  itemStyle: { color: "#a78bfa" },
                  collapsed: true,
                  children: paperChildren.length > 0 ? paperChildren : [{ name: "(无)", symbolSize: 3, itemStyle: { color: "#475569" } }],
                };
              }),
            };
          }),
        };
      }),
    };
  }

  function buildDimensionData(dimKey) {
    if (!mindmapsFive || !mindmapsFive.dimensions) return null;
    var dim = mindmapsFive.dimensions.find(function (d) { return d.id === dimKey; });
    if (!dim) return null;
    return {
      name: safeName(dim.label),
      itemStyle: { color: "#f59e0b" },
      children: (dim.categories || []).map(function (cat) {
        var paperChildren = (cat.paper_ids || []).map(function (pid) {
          return {
            name: paperLabel(pid),
            value: pid,
            paperId: pid,
            symbol: "circle",
            symbolSize: 6,
            itemStyle: { color: "#818cf8" },
            label: { fontSize: 9, color:"#a5b4fc" },
          };
        });
        return {
          name: safeName(cat.name + " (" + cat.count + ")"),
          itemStyle: { color: "#06b6d4" },
          collapsed: true,
          children: paperChildren.length > 0 ? paperChildren : [{ name: "(无)", symbolSize: 3, itemStyle: { color: "#475569" } }],
        };
      }),
    };
  }

  function buildTreeData(key) {
    if (allTreeData[key]) return allTreeData[key];
    var data = key === "process_tree" ? buildProcessTreeData() : buildDimensionData(key);
    if (data) allTreeData[key] = data;
    return data;
  }

  // ---- 详情 ----
  function showDetail(pid) {
    var p = papersById[String(pid)] || papersById[pid];
    if (!p) return;
    var kwsHtml = (p.keywords_zh || p.keywords || []).map(function(k){return "<span>"+esc(k)+"</span>";}).join("");
    var link = extLink(p);
    var doi = p.doi ? String(p.doi).replace(/^https?:\/\/(doi\.org\/)?/i,"") : "";
    detailContent.innerHTML =
      "<h3>#" + p.id + " " + esc((p.title_en||p.title||"").substring(0,50)) + "</h3>" +
      "<div class='meta'>" + esc(p.school||"") + " · " + esc(p.year||"") + " · " + esc(p.authors||"") + "</div>" +
      "<div class='kws'>" + (kwsHtml||"<span style='color:#94a3b8'>无关键词</span>") + "</div>" +
      "<div class='links'>" +
        (link?"<a href='"+esc(link)+"' target='_blank'>📄 原文 ↗</a>":"") +
        (doi?"<a href='https://doi.org/"+esc(doi)+"' target='_blank' style='background:#475569'>DOI ↗</a>":"") +
      "</div>" +
      "<h4 style='color:#f59e0b;font-size:0.8rem;margin:8px 0 4px'>中文摘要</h4>" +
      "<div class='summary'>"+esc(p.summary_zh||"（暂无）")+"</div>";
    detailPanel.classList.add("show");
  }

  function hideDetail() { detailPanel.classList.remove("show"); }
  document.getElementById("closeDetail").addEventListener("click", hideDetail);

  // ---- 渲染 ----
  function getOption(treeData) {
    return {
      tooltip: {
        trigger: "item", triggerOn: "mousemove", enterable: true,
        backgroundColor: "rgba(30,41,59,0.95)", borderColor: "#475569",
        textStyle: { color: "#e2e8f0", fontSize: 12 },
        formatter: function(p) {
          if (p.data && p.data.paperId) return paperTooltip(p.data.paperId);
          return "<b>" + esc(p.name||"") + "</b>";
        },
      },
      series: [{
        type: "tree", data: [treeData], layout: "radial",
        symbol: "circle",
        symbolSize: 8,
        label: {
          show: true, position: "right",
          fontSize: function(value, params) {
            var d = (params.data && params.data.depth) || (params.treePathInfo ? params.treePathInfo.length : 99);
            if (d <= 0) return 18;
            if (d <= 1) return 15;
            if (d <= 2) return 13;
            if (d <= 3) return 11;
            return 9;
          },
          fontWeight: function(value, params) {
            var d = (params.data && params.data.depth) || 99;
            return d <= 1 ? "bold" : "normal";
          },
          color: function(params) {
            var d = (params.data && params.data.depth) || 99;
            if (d <= 0) return "#fbbf24";
            if (d <= 1) return "#f97316";
            if (d <= 2) return "#38bdf8";
            if (d <= 3) return "#a78bfa";
            return "#94a3b8";
          },
          formatter: function(p) { return p.name || ""; },
        },
        itemStyle: { borderWidth: 1, borderColor: "#1e293b" },
        lineStyle: { color: "#334155", width: 0.8, curveness: 0.3 },
        roam: true,
        expandAndCollapse: true,
        animationDuration: 400,
        animationDurationUpdate: 600,
        initialTreeDepth: 3,
        leaves: {
          label: { fontSize: 9, color:"#94a3b8" },
        },
      }],
    };
  }

  function render(key) {
    currentKey = key;
    var treeData = buildTreeData(key);
    if (!treeData) {
      chart.clear();
      chartDom.innerHTML = "<div style='color:#94a3b8;text-align:center;padding-top:40vh'>数据加载中…</div>";
      return;
    }
    var opt = getOption(treeData);
    chart.setOption(opt, true);
    searchInput.value = "";
    searchResults.classList.remove("show");
  }

  // ---- Tab ----
  document.getElementById("tabCol").addEventListener("click", function (e) {
    var btn = e.target.closest("button[data-key]");
    if (!btn) return;
    document.querySelectorAll("#tabCol button").forEach(function(b){b.classList.remove("active");});
    btn.classList.add("active");
    render(btn.dataset.key);
  });

  // ---- 图表点击 ----
  chart.on("click", function (params) {
    if (params.data && params.data.paperId) showDetail(params.data.paperId);
  });

  // ---- 搜索 ----
  function flatten(node, path, out) {
    if (!node) return;
    var cp = path ? path + " > " + node.name : node.name;
    if (node.paperId) out.push({ id: node.paperId, label: node.name, path: cp });
    if (node.children) node.children.forEach(function(c){ flatten(c, cp, out); });
  }

  function doSearch(q) {
    if (!q || q.length < 1) { searchResults.classList.remove("show"); return; }
    q = q.toLowerCase();
    var tree = allTreeData[currentKey];
    if (!tree) return;
    var all = [];
    flatten(tree, "", all);
    var matches = all.filter(function(n) {
      if (String(n.id)===q) return true;
      if (n.label.toLowerCase().indexOf(q)>=0) return true;
      if (n.path.toLowerCase().indexOf(q)>=0) return true;
      var p = papersById[String(n.id)] || papersById[n.id];
      if (p) {
        var blob = [p.title_en,p.title,(p.keywords_zh||p.keywords||[]).join(" "),p.school,p.summary_zh].join(" ").toLowerCase();
        if (blob.indexOf(q)>=0) return true;
      }
      return false;
    });
    if (!matches.length) {
      searchResults.innerHTML = "<div style='padding:8px;color:#94a3b8;font-size:0.75rem'>无匹配</div>";
    } else {
      searchResults.innerHTML = matches.slice(0,20).map(function(m,i){
        return "<div class='sr-item' data-pid='"+m.id+"'>"+
          "<span style='color:#f59e0b'>#"+m.id+"</span> "+esc(m.label)+
          "<div class='sr-kw'>"+esc(m.path)+"</div></div>";
      }).join("");
      if (matches.length>20) searchResults.innerHTML+="<div style='padding:6px;color:#94a3b8;font-size:0.72rem'>…还有"+(matches.length-20)+"条</div>";
    }
    searchResults.classList.add("show");
  }

  searchResults.addEventListener("click", function(e){
    var el = e.target.closest(".sr-item");
    if (!el) return;
    var pid = parseInt(el.dataset.pid);
    if (pid) showDetail(pid);
    searchResults.classList.remove("show");
  });

  document.addEventListener("click", function(e){
    if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) searchResults.classList.remove("show");
  });

  searchInput.addEventListener("input", function(){ doSearch(this.value.trim()); });

  // ---- 加载 ----
  function init() {
    Promise.all([
      fetch("papers_index.json",{cache:"no-store"}).then(function(r){return r.json();}),
      fetch("mindmaps_five.json",{cache:"no-store"}).then(function(r){return r.json();}),
    ]).then(function(results){
      papersById = results[0].by_id || {};
      mindmapsFive = results[1];
      render("process_tree");
    }).catch(function(e){
      chart.clear();
      chartDom.innerHTML =
        "<div style='color:#ef4444;text-align:center;padding-top:40vh'>"+
        "<b>数据加载失败</b><br/><small>"+esc(e.message)+"</small><br/>"+
        "<small>请确认已运行 ingest.py —rebuild-only</small></div>";
      console.error(e);
    });
  }

  init();
})();
