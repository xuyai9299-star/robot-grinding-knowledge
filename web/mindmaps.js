/**
 * mindmaps.js v5 — 完整交互版
 * - 单击分类节点 → 展开/折叠子节点
 * - 单击论文节点 → 聚焦 + 右侧详情面板
 * - 双击论文 → 打开原文链接
 * - 6 个维度 Tab 切换
 */
(function () {
  "use strict";

  var ASPECTS = [
    { key:"process_tree",     title:"工艺三级树", type:"tree" },
    { key:"process_domain",   title:"L1 工艺领域", type:"flat" },
    { key:"process_method",   title:"L2 工艺方式", type:"flat" },
    { key:"research_topic",   title:"L3 研究主题", type:"flat" },
    { key:"application",      title:"L4 应用场景", type:"flat" },
    { key:"material",         title:"L5 加工材料", type:"flat" },
  ];

  var mindmapsFive = null;
  var papersById = {};
  var network = null;
  var currentAspect = "process_tree";
  var expandedNodes = {};   // 记录哪些分类节点被展开了
  var allNodes = null, allEdges = null;  // 当前完整数据

  // DOM
  var container = document.getElementById("network");
  var detailEl = document.getElementById("detail");
  var detailContent = document.getElementById("detailContent");
  var infoBar = document.getElementById("infoBar");
  var tabsEl = document.getElementById("tabs");

  // ---- 辅助 ----
  function esc(s) { return String(s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;"); }
  function extLink(p) {
    if (!p) return "";
    if (p.url) return p.url;
    var d = String(p.doi||"").replace(/^https?:\/\/(doi\.org\/)?/i,"");
    return d ? "https://doi.org/"+d : "";
  }
  function paperFromId(pid) {
    var p = papersById[String(pid)] || papersById[pid];
    if (!p) return { id:pid, title_en:"", keywords_zh:[], url:"" };
    return {
      id:p.id, title_en:p.title||p.title_en||"",
      keywords_zh:p.keywords||p.keywords_zh||[],
      url:extLink(p), doi:p.doi, school:p.school, year:p.year,
      summary_zh:p.summary_zh, authors:p.authors,
    };
  }

  // ---- 详情面板 ----
  function showDetail(pid) {
    var p = paperFromId(pid);
    var link = extLink(p);
    var doi = p.doi ? String(p.doi).replace(/^https?:\/\/(doi\.org\/)?/i,"") : "";
    var kwsHtml = (p.keywords_zh||[]).map(function(k){return"<span>"+esc(k)+"</span>";}).join("");
    detailContent.innerHTML =
      "<h3>#" + p.id + " " + esc((p.title_en||"").substring(0,55)) + "</h3>" +
      "<div class='meta'>" + esc(p.school||"") + " · " + esc(p.year||"") + " · " + esc(p.authors||"") + "</div>" +
      "<div class='tags'>" + (kwsHtml||"<span>无关键词</span>") + "</div>" +
      "<div class='btns'>" +
        (link?"<a href='"+esc(link)+"' target='_blank'>📄 原文 ↗</a>":"") +
        (doi?"<a href='https://doi.org/"+esc(doi)+"' target='_blank' style='background:#64748b'>DOI ↗</a>":"") +
      "</div>" +
      "<div class='summary'><div class='en'>" + esc((p.title_en||"").substring(0,120)) + "</div>" +
      esc(p.summary_zh||"（暂无中文摘要）") + "</div>";
    detailEl.classList.add("on");
  }

  function hideDetail() { detailEl.classList.remove("on"); }
  document.getElementById("closeDetail").addEventListener("click", hideDetail);

  // ---- 构建完整图谱 ----
  function makeNode(id, label, level, shape, color, bg, extra) {
    var n = {
      id:id, label:label, level:level, shape:shape||"box",
      color:{ background:bg||"#fef3c7", border:color||"#e2e8f0" },
      font:{ size:Math.max(9, 15-level*2), color:"#1e293b" },
    };
    if (extra) Object.keys(extra).forEach(function(k){ n[k]=extra[k]; });
    return n;
  }

  function buildFullGraph(key) {
    var nodes = [], edges = [], seenPapers = {};
    var rootId = "ROOT";

    if (key === "process_tree") {
      // 工艺三级树
      nodes.push(makeNode(rootId, "机器人柔性磨削\n知识库", 0, "box", "#f59e0b", "#fef3c7", { font:{size:15,color:"#1e293b",bold:true} }));
      (mindmapsFive.process_tree||[]).forEach(function(l1){
        var l1id = "l1_"+l1.name;
        nodes.push(makeNode(l1id, l1.name+" ("+l1.count+")", 1, "box", "#f97316", "#fff7ed"));
        edges.push({ from:rootId, to:l1id, color:{color:"#f97316"}, width:2 });

        (l1.children||[]).forEach(function(l2){
          var l2id = "l2_"+l1.name+"_"+l2.name;
          nodes.push(makeNode(l2id, l2.name+" ("+l2.count+")", 2, "box", "#06b6d4", "#ecfeff"));
          edges.push({ from:l1id, to:l2id, color:{color:"#06b6d4"}, width:1.5 });

          (l2.children||[]).forEach(function(l3){
            var l3id = "l3_"+l1.name+"_"+l2.name+"_"+l3.name;
            nodes.push(makeNode(l3id, l3.name+" ("+l3.count+")", 3, "box", "#8b5cf6", "#f5f3ff"));
            edges.push({ from:l2id, to:l3id, color:{color:"#8b5cf6"}, width:1 });

            (l3.paper_ids||[]).forEach(function(pid){
              var nid = "p"+pid;
              if (!seenPapers[nid]) {
                seenPapers[nid] = true;
                var p = paperFromId(pid);
                var kw = (p.keywords_zh||[]).slice(0,1).join("") || ("#"+pid);
                if (kw.length>6) kw=kw.substring(0,5)+"…";
                nodes.push(makeNode(nid, kw, 4, "dot", "#2563eb", "#dbeafe", {
                  size:10, paperId:pid,
                  title: "<b>#"+pid+"</b>\n"+esc((p.title_en||"").substring(0,60))+"\n<i>"+esc((p.keywords_zh||[]).join("、"))+"</i>",
                }));
              }
              edges.push({ from:l3id, to:"p"+pid, color:{color:"#93c5fd"}, width:0.5 });
            });
          });
        });
      });
    } else {
      // 平面维度
      var dim = (mindmapsFive.dimensions||[]).find(function(d){return d.id===key;});
      if (!dim) return { nodes:nodes, edges:edges };
      nodes.push(makeNode(rootId, dim.label, 0, "box", "#f59e0b", "#fef3c7", { font:{size:15,bold:true} }));

      (dim.categories||[]).forEach(function(cat){
        var cid = "c_"+key+"_"+cat.name;
        nodes.push(makeNode(cid, cat.name+" ("+cat.count+")", 1, "box", "#06b6d4", "#ecfeff"));
        edges.push({ from:rootId, to:cid, color:{color:"#06b6d4"}, width:1.5 });

        (cat.paper_ids||[]).forEach(function(pid){
          var nid = "p"+pid;
          if (!seenPapers[nid]) {
            seenPapers[nid] = true;
            var p = paperFromId(pid);
            var kw = (p.keywords_zh||[]).slice(0,1).join("") || ("#"+pid);
            if (kw.length>6) kw=kw.substring(0,5)+"…";
            nodes.push(makeNode(nid, kw, 2, "dot", "#2563eb", "#dbeafe", {
              size:10, paperId:pid,
              title: "<b>#"+pid+"</b>\n"+esc((p.title_en||"").substring(0,60))+"\n<i>"+esc((p.keywords_zh||[]).join("、"))+"</i>",
            }));
          }
          edges.push({ from:cid, to:"p"+pid, color:{color:"#93c5fd"}, width:0.5 });
        });
      });
    }
    return { nodes:nodes, edges:edges };
  }

  // ---- 按展开状态过滤可见节点 ----
  function getVisibleGraph(fullNodes, fullEdges) {
    // 收集所有展开的子树
    var visibleIds = {};
    var nodeMap = {};
    fullNodes.forEach(function(n){ nodeMap[n.id] = n; });

    // BFS，从 root 开始，只遍历展开的节点
    var queue = ["ROOT"];
    visibleIds["ROOT"] = true;

    while (queue.length > 0) {
      var parentId = queue.shift();
      fullEdges.forEach(function(e){
        if (e.from === parentId) {
          var childId = e.to;
          if (!visibleIds[childId]) {
            visibleIds[childId] = true;
            // 分类节点：检查是否展开了
            var childNode = nodeMap[childId];
            var isCategory = childNode && childNode.shape === "box";
            // 默认第1层(L1/分类)展开，更深层的按 expandedNodes 状态
            var level = childNode ? childNode.level : 99;
            if (isCategory && level >= 2) {
              // L2+ 默认折叠，除非在 expandedNodes 中
              if (expandedNodes[currentAspect] && expandedNodes[currentAspect][childId]) {
                queue.push(childId);
              }
            } else if (isCategory && level < 2) {
              // L1 和根默认展开
              queue.push(childId);
            } else if (!isCategory) {
              // 论文节点：如果父节点展开了就显示
              // (论文在加入 visibleIds 时已经通过父节点传播)
            }
          }
        }
      });
    }

    // 第二遍：确保论文节点的父节点展开了才显示
    var resultNodes = [];
    var resultEdges = [];
    fullEdges.forEach(function(e){
      var childNode = nodeMap[e.to];
      var isPaper = childNode && childNode.shape === "dot";
      if (isPaper) {
        // 论文：只有当父节点在可见集合中时才显示
        if (visibleIds[e.from]) {
          if (!visibleIds[e.to]) visibleIds[e.to] = true;
          resultEdges.push(e);
        }
      } else {
        // 分类间连线
        if (visibleIds[e.from] && visibleIds[e.to]) {
          resultEdges.push(e);
        }
      }
    });
    fullNodes.forEach(function(n){
      if (visibleIds[n.id]) resultNodes.push(n);
    });

    return { nodes:resultNodes, edges:resultEdges };
  }

  // ---- 渲染 ----
  function render(key) {
    currentAspect = key;
    var full = buildFullGraph(key);
    allNodes = full.nodes;
    allEdges = full.edges;

    // 初始化展开状态：只展开第一层
    if (!expandedNodes[key]) expandedNodes[key] = {};

    var visible = getVisibleGraph(allNodes, allEdges);

    var options = {
      layout:{ hierarchical:{ enabled:true, direction:"LR", sortMethod:"directed", levelSeparation:200, nodeSpacing:60 } },
      physics:{ enabled:true, solver:"barnesHut", barnesHut:{ gravitationalConstant:-8000, centralGravity:0.3, springLength:100, springConstant:0.04 } },
      interaction:{ hover:true, navigationButtons:true, tooltipDelay:100 },
      edges:{ smooth:{ type:"cubicBezier", forceDirection:"horizontal" }, color:{ color:"#cbd5e1" } },
    };

    if (network) { network.off("click"); network.off("doubleClick"); network.destroy(); }

    network = new vis.Network(container, {
      nodes: new vis.DataSet(visible.nodes),
      edges: new vis.DataSet(visible.edges),
    }, options);

    // 单击事件
    network.on("click", function(params){
      if (!params.nodes.length) { hideDetail(); return; }
      var nid = String(params.nodes[0]);

      // 论文节点 → 聚焦 + 显示详情
      if (nid.indexOf("p") === 0) {
        var pid = Number(nid.slice(1));
        network.focus(nid, { scale:1.8, animation:{ duration:400, easingFunction:"easeInOutQuad" } });
        network.selectNodes([nid]);
        showDetail(pid);
        return;
      }

      // 分类节点 → 切换展开/折叠
      var isExpanded = expandedNodes[currentAspect] && expandedNodes[currentAspect][nid];
      if (isExpanded) {
        // 折叠
        expandedNodes[currentAspect][nid] = false;
      } else {
        // 展开
        if (!expandedNodes[currentAspect]) expandedNodes[currentAspect] = {};
        expandedNodes[currentAspect][nid] = true;
      }
      // 重新渲染
      render(currentAspect);
      // 聚焦到这个节点
      setTimeout(function(){
        network.focus(nid, { scale:1.3, animation:{ duration:350, easingFunction:"easeInOutQuad" } });
      }, 100);
    });

    // 双击 → 打开原文
    network.on("doubleClick", function(params){
      if (!params.nodes.length) return;
      var nid = String(params.nodes[0]);
      if (nid.indexOf("p") !== 0) return;
      var pid = Number(nid.slice(1));
      var link = extLink(paperFromId(pid));
      if (link) window.open(link, "_blank", "noopener");
    });

    infoBar.textContent = visible.nodes.length + " 节点 · " + visible.edges.length + " 连线 · 单击分类展开/折叠";
  }

  // ---- Tab ----
  tabsEl.addEventListener("click", function(e){
    var btn = e.target.closest("button[data-key]");
    if (!btn) return;
    tabsEl.querySelectorAll("button").forEach(function(b){b.classList.remove("on");});
    btn.classList.add("on");
    render(btn.dataset.key);
  });

  // ---- 加载 ----
  function init() {
    Promise.all([
      fetch("papers_index.json",{cache:"no-store"}).then(function(r){return r.json();}),
      fetch("mindmaps_five.json",{cache:"no-store"}).then(function(r){return r.json();}),
    ]).then(function(results){
      papersById = results[0].by_id || {};
      mindmapsFive = results[1];
      // 更新 Tab 标题
      ASPECTS.forEach(function(a){
        var btn = tabsEl.querySelector("button[data-key='"+a.key+"']");
        if (btn) btn.textContent = a.title;
      });
      render("process_tree");
    }).catch(function(e){
      infoBar.textContent = "加载失败: " + e.message;
      console.error(e);
    });
  }

  init();
})();
