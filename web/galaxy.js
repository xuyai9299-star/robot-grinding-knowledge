/**
 * galaxy.js v2 — 3D 知识星系（层级轨道版）
 * 太阳(中心) → Ring1 L1工艺领域 → Ring2 L2工艺方式 → Ring3 L3研究主题 → Ring4 论文星球
 * 配色：金色 → 橙色 → 青色 → 紫色（热→冷，近→远）
 */
(function () {
  "use strict";

  // ---- 数据 ----
  var papersById = {};
  var mindmapsFive = null;
  var allMeshes = [];  // { mesh, paperId, type, name }

  // ---- Three.js ----
  var scene = new THREE.Scene();
  scene.background = new THREE.Color(0x020617);
  scene.fog = new THREE.FogExp2(0x020617, 0.0003);

  var camera = new THREE.PerspectiveCamera(50, window.innerWidth/window.innerHeight, 0.5, 150);
  camera.position.set(0, 12, 38);
  camera.lookAt(0, 0, 0);

  var renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  document.body.appendChild(renderer.domElement);

  // ---- 灯光 ----
  scene.add(new THREE.AmbientLight(0x223344, 0.5));
  var sunLight = new THREE.PointLight(0xffd700, 2.5, 60);
  sunLight.position.set(0, 0, 0);
  scene.add(sunLight);
  var fillLight = new THREE.PointLight(0x4488ff, 0.6, 50);
  fillLight.position.set(0, 20, 0);
  scene.add(fillLight);

  // ---- 星空 ----
  (function(){
    var geo = new THREE.BufferGeometry();
    var n = 3000, arr = new Float32Array(n*3);
    for (var i=0;i<n*3;i+=3) { arr[i]=(Math.random()-0.5)*100; arr[i+1]=(Math.random()-0.5)*100; arr[i+2]=(Math.random()-0.5)*100; }
    geo.setAttribute("position", new THREE.BufferAttribute(arr,3));
    var mat = new THREE.PointsMaterial({ color:0xffffff, size:0.06, transparent:true, opacity:0.6 });
    scene.add(new THREE.Points(geo, mat));
  })();

  // ---- 中心太阳 ----
  var sunGeo = new THREE.SphereGeometry(1.4, 48, 48);
  var sunMat = new THREE.MeshPhongMaterial({ color:0xffd700, emissive:0xffb700, emissiveIntensity:1.2, shininess:120 });
  var sun = new THREE.Mesh(sunGeo, sunMat);
  scene.add(sun);
  // 光芒
  var auraGeo = new THREE.SphereGeometry(1.9, 32, 32);
  var auraMat = new THREE.ShaderMaterial({
    uniforms: { uTime: { value: 0 } },
    vertexShader: "varying vec3 vPos; void main(){ vPos=position; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0); }",
    fragmentShader: "varying vec3 vPos; uniform float uTime; void main(){ float d=length(vPos); float a=0.35*(1.0-smoothstep(0.8,2.2,d)); a+=0.08*sin(d*6.0-uTime*3.0); gl_FragColor=vec4(1.0,0.75,0.15,a); }",
    transparent: true, depthWrite: false,
  });
  var aura = new THREE.Mesh(auraGeo, auraMat);
  scene.add(aura);

  // 标签
  function spriteLabel(text, pos, color, scale) {
    var c = document.createElement("canvas");
    c.width=512; c.height=128;
    var ctx=c.getContext("2d");
    ctx.fillStyle=color||"#fbbf24";
    ctx.font="bold 36px 'PingFang SC','Microsoft YaHei',sans-serif";
    ctx.textAlign="center";
    ctx.fillText(text,256,72);
    var tex = new THREE.CanvasTexture(c);
    tex.minFilter=THREE.LinearFilter;
    var sp = new THREE.Sprite(new THREE.SpriteMaterial({ map:tex, transparent:true, depthTest:false }));
    sp.position.copy(pos);
    sp.scale.set(scale||8, (scale||8)/4, 1);
    return sp;
  }
  scene.add(spriteLabel("机器人柔性磨削知识库", new THREE.Vector3(0, 3.2, 0), "#ffd700", 9));

  // ---- 轨道环（4层） ----
  var ringConfig = [
    { radius: 5.5,  color: 0xf59e0b, opacity: 0.35, label: "L1 工艺领域",   level: "l1" },
    { radius: 9.5,  color: 0xf97316, opacity: 0.28, label: "L2 工艺方式",   level: "l2" },
    { radius: 14,   color: 0x06b6d4, opacity: 0.22, label: "L3 研究主题",   level: "l3" },
    { radius: 19.5, color: 0xa78bfa, opacity: 0.18, label: "论文",          level: "paper" },
  ];

  ringConfig.forEach(function(rc){
    var ringGeo = new THREE.TorusGeometry(rc.radius, 0.05, 16, 180);
    var ringMat = new THREE.MeshBasicMaterial({ color: rc.color, transparent: true, opacity: rc.opacity });
    var ring = new THREE.Mesh(ringGeo, ringMat);
    ring.rotation.x = Math.PI/2.2;
    scene.add(ring);
    // 第二圈（偏移一点角度，更像土星环）
    var ring2 = new THREE.Mesh(
      new THREE.TorusGeometry(rc.radius, 0.03, 16, 144),
      new THREE.MeshBasicMaterial({ color: rc.color, transparent: true, opacity: rc.opacity*0.6 })
    );
    ring2.rotation.x = Math.PI/2.0;
    scene.add(ring2);
    // 标签
    var labelAngle = -0.3;
    scene.add(spriteLabel(rc.label, new THREE.Vector3(
      Math.cos(labelAngle)*rc.radius, 1.2, Math.sin(labelAngle)*rc.radius
    ), "#ffffff", 4.5));
  });

  // ---- 放置节点 ----
  function createGlowSphere(radius, color, emissiveIntensity) {
    var geo = new THREE.SphereGeometry(radius, 24, 24);
    var mat = new THREE.MeshPhongMaterial({
      color: color, emissive: color,
      emissiveIntensity: emissiveIntensity || 0.6,
      shininess: 80,
    });
    return new THREE.Mesh(geo, mat);
  }

  function placeAllNodes() {
    var processTree = mindmapsFive.process_tree;
    if (!processTree) return;

    // 遍历 process_tree，把节点放在对应层级轨道上
    // L1 在 ring 0, L2 在 ring 1, L3 在 ring 2, papers 在 ring 3

    var l1Count = processTree.length;
    processTree.forEach(function (l1, l1Idx) {
      // L1 节点：均匀分布在 ring 0
      var l1Angle = (l1Idx / l1Count) * Math.PI * 2;
      var l1R = ringConfig[0].radius;
      var l1Pos = new THREE.Vector3(
        Math.cos(l1Angle) * l1R, (Math.random()-0.5)*1.5, Math.sin(l1Angle) * l1R
      );
      var l1Mesh = createGlowSphere(0.35, 0xf59e0b, 0.7);
      l1Mesh.position.copy(l1Pos);
      scene.add(l1Mesh);
      allMeshes.push({ mesh: l1Mesh, type: "l1", name: l1.name });

      var l2Children = l1.children || [];
      var l2Count = l2Children.length;
      l2Children.forEach(function (l2, l2Idx) {
        // L2 节点围绕父 L1 角度分布
        var l2Angle = l1Angle + (l2Idx - l2Count/2) * 0.3;
        var l2R = ringConfig[1].radius;
        var l2Pos = new THREE.Vector3(
          Math.cos(l2Angle) * l2R, (Math.random()-0.5)*2.5, Math.sin(l2Angle) * l2R
        );
        var l2Mesh = createGlowSphere(0.28, 0xf97316, 0.65);
        l2Mesh.position.copy(l2Pos);
        scene.add(l2Mesh);
        allMeshes.push({ mesh: l2Mesh, type: "l2", name: l2.name });

        // 连线 L1→L2
        var lineGeo = new THREE.BufferGeometry().setFromPoints([l1Pos, l2Pos]);
        var lineMat = new THREE.LineBasicMaterial({ color: 0x475569, transparent: true, opacity: 0.25 });
        scene.add(new THREE.Line(lineGeo, lineMat));

        var l3Children = l2.children || [];
        var l3Count = l3Children.length;
        l3Children.forEach(function (l3, l3Idx) {
          // L3 节点
          var l3Angle = l2Angle + (l3Idx - l3Count/2) * 0.2;
          var l3R = ringConfig[2].radius;
          var l3Pos = new THREE.Vector3(
            Math.cos(l3Angle) * l3R, (Math.random()-0.5)*3.5, Math.sin(l3Angle) * l3R
          );
          var l3Mesh = createGlowSphere(0.22, 0x06b6d4, 0.6);
          l3Mesh.position.copy(l3Pos);
          scene.add(l3Mesh);
          allMeshes.push({ mesh: l3Mesh, type: "l3", name: l3.name });

          // 连线 L2→L3
          var line2Geo = new THREE.BufferGeometry().setFromPoints([l2Pos, l3Pos]);
          var line2Mat = new THREE.LineBasicMaterial({ color: 0x334155, transparent: true, opacity: 0.2 });
          scene.add(new THREE.Line(line2Geo, line2Mat));

          // 论文粒子
          var paperIds = l3.paper_ids || [];
          var pCount = paperIds.length;
          paperIds.forEach(function (pid, pIdx) {
            var pAngle = l3Angle + (pIdx - pCount/2) * 0.08;
            var pR = ringConfig[3].radius + (Math.random()-0.5)*3;
            var pPos = new THREE.Vector3(
              Math.cos(pAngle) * pR, (Math.random()-0.5)*5, Math.sin(pAngle) * pR
            );
            var pMesh = createGlowSphere(0.14, 0xa78bfa, 0.5);
            pMesh.position.copy(pPos);
            pMesh.userData = { paperId: pid };
            scene.add(pMesh);
            allMeshes.push({ mesh: pMesh, type: "paper", paperId: pid, name: "#"+pid });

            // 少数论文加光晕环
            if (Math.random() < 0.12) {
              var hrGeo = new THREE.TorusGeometry(0.2, 0.015, 8, 16);
              var hrMat = new THREE.MeshBasicMaterial({ color: 0xc4b5fd, transparent: true, opacity: 0.55 });
              var hr = new THREE.Mesh(hrGeo, hrMat);
              hr.position.copy(pPos);
              hr.rotation.x = Math.random()*Math.PI;
              hr.rotation.y = Math.random()*Math.PI;
              scene.add(hr);
            }
          });
        });
      });
    });
  }

  // ---- 图例 ----
  function buildLegend() {
    var el = document.getElementById("legend");
    if (!el) return;
    var items = [
      { color: "#f59e0b", label: "L1 工艺领域" },
      { color: "#f97316", label: "L2 工艺方式" },
      { color: "#06b6d4", label: "L3 研究主题" },
      { color: "#a78bfa", label: "论文" },
    ];
    el.innerHTML = items.map(function(item){
      return "<div style='display:flex;align-items:center;gap:6px;color:#94a3b8;font-size:0.72rem'>"+
        "<span style='width:10px;height:10px;border-radius:50%;background:"+item.color+";box-shadow:0 0 8px "+item.color+"'></span>"+
        item.label+"</div>";
    }).join("");
  }

  // ---- 交互 ----
  var isDragging = false, prevMouse = {x:0,y:0};
  var rotation = { x: 0.15, y: 0 };
  var camDist = 38;
  var autoRotate = true;

  function onDown(e) { isDragging=true; autoRotate=false; prevMouse.x=e.clientX; prevMouse.y=e.clientY; }
  function onMove(e) {
    if (!isDragging) return;
    rotation.y += (e.clientX-prevMouse.x)*0.004;
    rotation.x += (e.clientY-prevMouse.y)*0.004;
    rotation.x = Math.max(-1.2, Math.min(1.2, rotation.x));
    prevMouse.x=e.clientX; prevMouse.y=e.clientY;
  }
  function onUp() { isDragging=false; setTimeout(function(){ if(!isDragging) autoRotate=true; }, 2500); }
  function onWheel(e) { e.preventDefault(); camDist+=e.deltaY*0.04; camDist=Math.max(8,Math.min(65,camDist)); }

  renderer.domElement.addEventListener("mousedown", onDown);
  window.addEventListener("mousemove", onMove);
  window.addEventListener("mouseup", onUp);
  renderer.domElement.addEventListener("wheel", onWheel, {passive:false});
  renderer.domElement.addEventListener("touchstart", function(e){ if(e.touches.length===1){ onDown({clientX:e.touches[0].clientX,clientY:e.touches[0].clientY}); } });
  renderer.domElement.addEventListener("touchmove", function(e){ if(e.touches.length===1) onMove({clientX:e.touches[0].clientX,clientY:e.touches[0].clientY}); });
  renderer.domElement.addEventListener("touchend", onUp);

  // ---- 点击检测 ----
  var raycaster = new THREE.Raycaster();
  raycaster.params.Points.threshold = 0.4;

  function getClickTarget(e) {
    var mouse = new THREE.Vector2(
      (e.clientX/window.innerWidth)*2-1,
      -(e.clientY/window.innerHeight)*2+1
    );
    raycaster.setFromCamera(mouse, camera);
    var targets = allMeshes.filter(function(m){ return m.type==="paper"; }).map(function(m){return m.mesh;});
    var hits = raycaster.intersectObjects(targets);
    return hits.length>0 ? hits[0].object : null;
  }

  // ---- 卡片 ----
  var card = document.getElementById("card");
  var cardContent = document.getElementById("cardContent");
  function esc(s) { return String(s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;"); }
  function extLink(p) {
    if (!p) return "";
    if (p.url) return p.url;
    var d = String(p.doi||"").replace(/^https?:\/\/(doi\.org\/)?/i,"");
    return d?"https://doi.org/"+d:"";
  }

  function showCard(pid) {
    var p = papersById[String(pid)]||papersById[pid];
    if (!p) return;
    var link = extLink(p);
    var doi = p.doi?String(p.doi).replace(/^https?:\/\/(doi\.org\/)?/i,""):"";
    var kwsHtml = (p.keywords_zh||p.keywords||[]).map(function(k){return"<span>"+esc(k)+"</span>";}).join("");
    cardContent.innerHTML =
      "<h3>#" + p.id + " " + esc((p.title_en||p.title||"").substring(0,45)) + "</h3>" +
      "<div class='meta'>"+esc(p.school||"")+" · "+esc(p.year||"")+"</div>"+
      "<div class='kws'>"+(kwsHtml||"<span>无关键词</span>")+"</div>"+
      "<div class='links'>"+
        (link?"<a href='"+esc(link)+"' target='_blank'>📄 原文</a>":"")+
        (doi?"<a href='https://doi.org/"+esc(doi)+"' target='_blank' style='background:#475569'>DOI</a>":"")+
      "</div>"+
      "<div class='summary'>"+esc(p.summary_zh||"（暂无中文摘要）")+"</div>";
    card.classList.add("show");
  }

  document.getElementById("closeCard").addEventListener("click", function(){ card.classList.remove("show"); });

  var highlighted = null;
  function highlight(mesh) {
    if (highlighted) { highlighted.material.emissive.set(highlighted.userData.origColor||0xa78bfa); highlighted.material.emissiveIntensity=0.5; highlighted.scale.set(1,1,1); }
    if (mesh) {
      mesh.userData.origColor = mesh.material.emissive.getHex();
      mesh.material.emissive.set(0xffffff);
      mesh.material.emissiveIntensity = 1.0;
      mesh.scale.set(2.2,2.2,2.2);
      highlighted = mesh;
    }
  }

  renderer.domElement.addEventListener("click", function(e){
    var target = getClickTarget(e);
    if (target && target.userData && target.userData.paperId) {
      highlight(target);
      showCard(target.userData.paperId);
    } else {
      highlight(null);
      card.classList.remove("show");
    }
  });

  // ---- 动画 ----
  function animate(time) {
    requestAnimationFrame(animate);
    var t = time * 0.001;

    if (autoRotate && !isDragging) rotation.y += 0.002;

    var theta = rotation.y, phi = rotation.x + 0.7;
    camera.position.x = Math.cos(theta)*Math.cos(phi)*camDist;
    camera.position.y = Math.sin(phi)*camDist;
    camera.position.z = Math.sin(theta)*Math.cos(phi)*camDist;
    camera.lookAt(0, 0, 0);

    // 太阳脉冲
    sun.scale.setScalar(1+Math.sin(t*2.5)*0.04);
    aura.material.uniforms.uTime.value = t;

    renderer.render(scene, camera);
  }

  window.addEventListener("resize", function(){
    camera.aspect = window.innerWidth/window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
  });

  // ---- 启动 ----
  function init() {
    Promise.all([
      fetch("papers_index.json",{cache:"no-store"}).then(function(r){return r.json();}),
      fetch("mindmaps_five.json",{cache:"no-store"}).then(function(r){return r.json();}),
    ]).then(function(results){
      papersById = results[0].by_id || {};
      mindmapsFive = results[1];
      placeAllNodes();
      buildLegend();
      requestAnimationFrame(animate);
    }).catch(function(e){
      document.body.innerHTML+=
        "<div style='position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);color:#ef4444;text-align:center'>"+
        "<b>数据加载失败</b><br/><small>"+esc(e.message)+"</small></div>";
    });
  }

  init();
})();
