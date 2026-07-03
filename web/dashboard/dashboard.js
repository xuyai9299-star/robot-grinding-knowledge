// ===== Navigation =====
function navigateTo(url) { window.location.href = url; }

// ===== CENTER: RAG Pipeline Flowchart =====
(function initPipeline() {
  var w = document.getElementById("pipelineFlow").offsetWidth || 800;
  var h = document.getElementById("pipelineFlow").offsetHeight || 450;
  var svg = d3.select("#pipelineFlow").append("svg").attr("width", "100%").attr("height", "100%").attr("viewBox", "0 0 " + w + " " + h).attr("preserveAspectRatio", "xMidYMid meet");

  // Arrow marker
  svg.append("defs").append("marker")
    .attr("id", "arrowhead").attr("viewBox", "0 0 10 7").attr("refX", 10).attr("refY", 3.5)
    .attr("markerWidth", 8).attr("markerHeight", 6).attr("orient", "auto")
    .append("polygon").attr("points", "0 0,10 3.5,0 7").attr("fill", "#5aa9c8");

  // Define pipeline stages
  var stages = [
    {label: "数据源", sub: "Zotero + OpenAlex", x: 40, y: 60, w: 100, h: 48, color: "#2dd4a8"},
    {label: "LLM处理", sub: "摘要+关键词生成", x: 170, y: 60, w: 100, h: 48, color: "#5aa9c8"},
    {label: "五维分类", sub: "L1→L2→L3→L4→L5", x: 300, y: 60, w: 110, h: 48, color: "#9888c8"},
    {label: "向量化", sub: "text-embedding-v3", x: 440, y: 60, w: 110, h: 48, color: "#f0c060"},
    {label: "ChromaDB", sub: "向量数据库存储", x: 140, y: 160, w: 110, h: 48, color: "#e05570"},
    {label: "混合检索", sub: "BM25 + Vector + 分类", x: 300, y: 160, w: 120, h: 48, color: "#2dd4a8"},
    {label: "千问生成", sub: "qwen-plus 回答", x: 470, y: 160, w: 110, h: 48, color: "#5aa9c8"},
    {label: "Web展示", sub: "交互式知识系统", x: 350, y: 260, w: 120, h: 48, color: "#9888c8"},
  ];

  // Draw nodes
  stages.forEach(function(s) {
    var g = svg.append("g").attr("class", "pf-node");
    g.append("rect").attr("x", s.x).attr("y", s.y).attr("width", s.w).attr("height", s.h)
      .attr("stroke", s.color).attr("fill", "rgba(11,19,32,0.92)").attr("rx", 8);
    g.append("text").attr("x", s.x + s.w/2).attr("y", s.y + 20).text(s.label)
      .attr("fill", "#fff").attr("font-size", "11px").attr("font-weight", "600").attr("text-anchor", "middle");
    g.append("text").attr("x", s.x + s.w/2).attr("y", s.y + 36).text(s.sub)
      .attr("fill", "#6b7d95").attr("font-size", "8px").attr("text-anchor", "middle");
  });

  // Draw connecting arrows
  var arrows = [
    [140,84, 170,84], [270,84, 300,84], [410,84, 440,84],
    [550,84, 195,160], [250,184, 300,184], [420,184, 470,184],
    [495,160, 250,184], [195,208, 410,260], [580,184, 410,260],
  ];
  arrows.forEach(function(a) {
    svg.append("line").attr("x1", a[0]).attr("y1", a[1]).attr("x2", a[2]).attr("y2", a[3])
      .attr("class", "pf-arrow flow").attr("marker-end", "url(#arrowhead)");
  });

  // Connect lines
  var lines = [
    [440+55, 60+48, 140+55, 160],  // 向量化 → ChromaDB
    [110+55, 60+48, 470+55, 160],  // 五维 → 千问 (indirect)
  ];
  lines.forEach(function(l) {
    svg.append("path").attr("d", "M"+l[0]+","+l[1]+" Q"+l[0]+",110 "+l[2]+","+l[3])
      .attr("class", "pf-arrow").attr("marker-end", "url(#arrowhead)");
  });
})();

// ===== RIGHT: Mini 3D Globe =====
(function initMiniGlobe() {
  var container = document.getElementById("miniGlobe");
  if (!window.THREE || !container) return;
  var w = container.offsetWidth, h = container.offsetHeight;
  var scene = new THREE.Scene(); scene.background = new THREE.Color(0x0b1320);
  var cam = new THREE.PerspectiveCamera(50, w/h, 0.5, 50); cam.position.set(0, 0, 6);
  var renderer = new THREE.WebGLRenderer({canvas: document.getElementById("miniGlobeCanvas"), antialias: true});
  renderer.setSize(w, h);
  scene.add(new THREE.AmbientLight(0x446688, 0.6));
  var earth = new THREE.Mesh(new THREE.SphereGeometry(2.5, 36, 30), new THREE.MeshPhongMaterial({color: 0x1e3a5f, emissive: 0x0a1628}));
  scene.add(earth);
  // Markers
  var markers = [
    {lat:42.33, lng:-83.05, c:0x44ff88},  // ICRA (Detroit)
    {lat:35.69, lng:139.69, c:0x44ff88}, // IROS (Tokyo)
    {lat:48.86, lng:2.35, c:0x4488ff},   // CIRP (Paris)
    {lat:37.77, lng:-122.42, c:0xbb88ff},// T-RO (San Fran)
    {lat:31.23, lng:121.47, c:0x44ff88}, // ICARM (Shanghai)
    {lat:1.35, lng:103.82, c:0x4488ff},  // ROBIO (Singapore)
  ];
  markers.forEach(function(m) {
    var lat = m.lat * Math.PI/180, lng = m.lng * Math.PI/180, r = 2.6;
    var dot = new THREE.Mesh(new THREE.SphereGeometry(0.06, 6, 6), new THREE.MeshBasicMaterial({color: m.c}));
    dot.position.set(r*Math.cos(lat)*Math.cos(lng), r*Math.sin(lat), r*Math.cos(lat)*Math.sin(lng));
    earth.add(dot);
  });
  var ry = 0;
  function anim() { requestAnimationFrame(anim); ry += 0.004; earth.rotation.y = ry; renderer.render(scene, cam); }
  anim();
})();

// ===== RIGHT: Venue List =====
fetch("../conferences/conferences.json", {cache: "no-store"})
  .then(function(r) { return r.json(); })
  .then(function(d) {
    var items = (d.conferences || []).concat(d.journals || []).slice(0, 8);
    var html = "";
    items.forEach(function(v) {
      html += '<div class="vl-item">' + (v.abbrev || v.name) + ' · ' + (v.paper_count || '?') + '篇</div>';
    });
    document.getElementById("dbVenueList").innerHTML = html;
  }).catch(function(){});

// ===== RIGHT: Timeline Mini =====
fetch("../conferences/timeline.json", {cache: "no-store"})
  .then(function(r) { return r.json(); })
  .then(function(td) {
    var tl = (td.timeline || []).filter(function(y) { return y.year && y.year >= 2010; });
    var html = "";
    tl.forEach(function(y) {
      html += '<div><span class="tl-dot"></span>' + y.year + ' &nbsp;' + (y.paper_count||0) + '篇 &nbsp;' + ((y.top_directions||[]).slice(0,2).map(function(d){return d.name;}).join(', ')) + '</div>';
    });
    document.getElementById("dbTimelineMini").innerHTML = html;
  }).catch(function(){});
