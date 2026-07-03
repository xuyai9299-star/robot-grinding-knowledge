# -*- coding: utf-8 -*-
"""五级分类规则（与既有 papers_classified 体系一致）。"""
from __future__ import annotations

from typing import Any

TAXONOMY: dict[str, dict[str, list[str]]] = {
    "process_domain": {
        "机器人磨削/抛光": [
            "机器人磨削", "机器人砂带磨削", "机器人带式磨削", "机器人辅助加工",
            "机器人抛光", "机器人柔性磨削", "机器人磁盘磨削", "机器人合规磨削",
            "柔顺机器人磨削", "机器人带磨削", "bone-grinding robot",
            "robotic grinding", "robot grinding", "robotic belt grinding",
            "robot belt grinding", "robotic polishing", "robot-assisted grinding",
            "robot grinding system", "robotic abrasive", "robotic machining",
            "robot-assisted", "machining robot", "grinding robot",
            "climbing machining robot", "robot-assisted bone",
            "robot-assisted surgical", "robotic bone", "surgical robot grinding",
        ],
        "非机器人专用磨削": [
            "带式磨削", "砂带磨削", "七轴联动", "CNC", "机床磨削", "数控磨削",
            "belt grinding", "abrasive belt", "conventional grinding",
            "angle grinder", "grinding wheel", "abrasive machining",
            "machining", "cutting technology", "precision grinding",
            "surface grinding", "cylindrical grinding",
        ],
    },
    "process_method": {
        "砂带/带式磨削": [
            "砂带磨削", "带式磨削", "机器人砂带磨削", "机器人带式磨削", "砂带", "带磨",
            "belt grinding", "abrasive belt", "belt grind", "sand belt",
            "belt finishing", "belt abrasive", "abrasive grain", "abrasive process",
        ],
        "抛光": ["抛光", "belt polishing", "柔性抛光", "带式抛光", "polishing",
            "finishing", "deburring", "derusting", "contouring"],
        "磁盘/其他磨削": [
            "磁盘磨削", "disk grinding", "卷积磨削", "软工具磨削",
            "abrasive wheel", "grinding wheel", "wheel grinding",
            "angle grinder", "rock grinder", "3-dof grinder",
            "diamond abrasive", "free abrasive", "abrasive grain condition",
        ],
    },
    "research_topic": {
        "表面质量与完整性": [
            "表面粗糙度", "表面完整性", "表面形貌", "表面纹理", "表面质量",
            "轮廓精度", "形面精度", "磨削痕", "表面重构", "表面预测", "亚表面",
            "surface roughness", "surface integrity", "surface quality",
            "surface topography", "surface texture", "profile accuracy",
            "surface finish", "surface morphology", "roughness analysis",
            "multiscale roughness", "burr", "deburring",
        ],
        "残余应力": ["残余应力", "residual stress"],
        "材料去除与机理": [
            "材料去除", "材料去除率", "材料去除深度", "磨削力", "切削机理",
            "比磨削能", "未变形切屑厚度", "能量效率", "耕犁", "滑擦", "磨损",
            "material removal", "material removal rate", "depth of cut",
            "grinding force", "cutting force", "grinding mechanism",
            "chip thickness", "specific energy", "cutting mechanism",
        ],
        "力/位控制": [
            "力控制", "力-位混合控制", "阻抗控制", "恒力控制", "力反馈",
            "柔顺控制", "力跟踪", "混合力控制", "主动力控", "力/位",
            "force control", "force-position", "impedance control",
            "constant force", "force feedback", "compliant control",
            "hybrid force", "active force", "force tracking",
        ],
        "轨迹与路径规划": [
            "轨迹规划", "路径规划", "刀位规划", "进给规划", "dwell time", "刀路", "驻留时间",
            "trajectory planning", "path planning", "tool path",
            "toolpath", "tool-path", "trajectory generation",
            "feed rate planning", "motion planning",
            "contour tracking", "robotic contouring", "contour following",
            "conformance grinding",
        ],
        "标定与测量": [
            "标定", "TCP标定", "系统标定", "在机测量", "点云配准",
            "三维重建", "扫描测量", "激光扫描", "视觉测量", "红宝石",
            "calibration", "tcp calibration", "laser scanner",
            "measurement", "scanning", "3d reconstruction", "point cloud",
            "registration", "visual measurement", "surface metrology",
            "on-machine", "in-process metrology", "on-machine measurement",
            "multiscale roughness analysis", "nondestructive evaluation",
        ],
        "状态监测与砂带磨损": [
            "状态监测", "条件监测", "砂带磨损", "belt wear", "声发射", "磨损监测",
            "condition monitoring", "belt wear", "tool wear",
            "acoustic emission", "wear monitoring", "belt condition",
            "fault diagnosis", "angle grinder", "electric impact drill",
            "advanced monitoring", "machining operations monitoring",
        ],
        "工艺优化与智能方法": [
            "工艺优化", "参数优化", "机器学习", "深度学习", "迁移学习",
            "知识嵌入", "智能算法", "智能磨削", "粒子群", "神经网络",
            "optimization", "machine learning", "deep learning",
            "neural network", "intelligent", "smart",
            "genetic algorithm", "particle swarm", "reinforcement learning",
            "adaptive control", "adaptive sliding",
        ],
        "建模与仿真": [
            "有限元", "数值模拟", "神经网络", "预测模型", "仿真", "Hertz", "有限元仿真",
            "simulation", "finite element", "numerical", "predict",
            "model", "modeling", "fem", "analytical model",
            "digital twin", "digital",
        ],
    },
    "application": {
        "航空航天": [
            "航空", "发动机", "叶片", "涡轮", "压气机", "整体叶盘", "叶盘", "叶根", "航天", "aero", "blisk",
            "aero-engine", "turbine blade", "blade", "turbine",
            "aerospace", "aircraft", "aeroengine",
        ],
        "船舶/能源": ["船", "螺旋桨", "propeller", "能源", "marine", "ship",
            "pipeline", "pipeline grinding", "spherical tank", "pressure vessel",
            "inner wall", "pipe grinding", "derusting"],
        "汽车/通用机械": [
            "汽车", "齿轮", "泵", "20CrMnTi", "压缩机",
            "automotive", "gear", "pump", "bearing",
        ],
        "通用小零件/试件": [
            "试件", "test workpiece", "功能件", "薄壁", "环形件", "样件",
            "thin-walled", "workpiece", "test piece", "free-form surface",
            "complex surface", "complex geometry",
        ],
        "增材/修复再制造": [
            "增材", "修复", "激光熔覆", "remanufacturing", "再制造", "焊接",
            "additive manufacturing", "laser cladding", "repair",
            "remanufacturing", "welding", "hybrid additive",
        ],
        "医学/手术": [
            "surgery", "surgical", "bone", "cervical", "laminectomy",
            "skull", "medical", "dental", "implant", "prosthesis",
            "orthopedic", "orthopaedic", "cranial", "mandible",
            "maxillofacial", "tissue engineering", "scaffold",
            "surgical robot", "bone-grinding", "bone grinding",
            "decompressive", "spinal", "vertebra", "disc replacement",
        ],
    },
    "material": {
        "钛合金": [
            "钛合金", "TC4", "TC17", "Ti-6Al-4V", "TC4钛合金",
            "titanium alloy", "titanium", "ti-6al-4v", "tc4", "tc17",
        ],
        "高温合金": [
            "高温合金", "GH4169", "superalloy", "镍基", "Inconel", "单晶高温合金",
            "nickel", "inconel", "nickel-based", "superalloy",
            "gh4169", "ni-based",
        ],
        "陶瓷/复合材料": [
            "陶瓷", "氧化锆", "Cf/SiC", "复合材料", "zirconia", "SiC", "陶瓷基",
            "ceramic", "composite", "zirconia", "sic", "cf/sic",
        ],
        "钢/铁": [
            "钢", "铁", "20CrMnTi", "纯铁",
            "steel", "iron", "stainless steel",
        ],
    },
}

LEVEL_KEYS = list(TAXONOMY.keys())


def _match_category(keywords: list[str], terms: list[str]) -> bool:
    kw_str = " ".join(keywords).lower()
    for t in terms:
        t_low = t.lower()
        if any(t_low in k.lower() for k in keywords) or t_low in kw_str:
            return True
    return False


def classify_keywords(keywords: list[str]) -> dict[str, list[str]]:
    """根据关键词列表得到 hierarchy 五层标签。"""
    hierarchy: dict[str, list[str]] = {k: [] for k in LEVEL_KEYS}
    for level, cats in TAXONOMY.items():
        for cat, terms in cats.items():
            if _match_category(keywords, terms):
                hierarchy[level].append(cat)
    return hierarchy


def classify_from_text(paper: dict[str, Any]) -> dict[str, list[str]]:
    """当没有关键词时，从标题+摘要+venue 文本匹配分类（与 mindmaps_five 的 fallback 一致）。"""
    text = " ".join([
        paper.get("title_en", ""), paper.get("title", ""),
        paper.get("abstract", ""), paper.get("summary_zh", ""),
        paper.get("venue", ""),
    ]).lower()
    hierarchy: dict[str, list[str]] = {k: [] for k in LEVEL_KEYS}
    for level, cats in TAXONOMY.items():
        for cat, terms in cats.items():
            for term in terms:
                if term.lower() in text:
                    hierarchy[level].append(cat)
                    break
    return hierarchy


def build_hierarchy_tags(hierarchy: dict[str, list[str]]) -> list[str]:
    """网页筛选用：取 L1 → L2 → L3 各第一个主标签。"""
    tags: list[str] = []
    for key in ("process_domain", "process_method", "research_topic"):
        vals = hierarchy.get(key) or []
        if vals and vals[0] not in tags:
            tags.append(vals[0])
    return tags


def build_mindmap_path(hierarchy: dict[str, list[str]]) -> str:
    parts = []
    for key in ("process_domain", "process_method", "research_topic"):
        vals = hierarchy.get(key) or []
        if vals:
            parts.append(vals[0])
    return " > ".join(parts) if parts else ""


def _hierarchy_nonempty(hierarchy: dict[str, list[str]] | None) -> bool:
    if not hierarchy:
        return False
    return any(hierarchy.get(k) for k in LEVEL_KEYS)


def sync_tags_from_hierarchy(paper: dict[str, Any]) -> dict[str, Any]:
    """保留已有 hierarchy，仅同步 tags / path / keywords_flat。"""
    h = paper.get("hierarchy") or {}
    paper["hierarchy_tags"] = build_hierarchy_tags(h)
    if not paper.get("mindmap_path"):
        paper["mindmap_path"] = build_mindmap_path(h)
    kws = paper.get("keywords") or []
    if isinstance(kws, str):
        kws = [k.strip() for k in k.split("、") if k.strip()]
    paper["keywords_flat"] = list(kws)
    return paper


def enrich_paper_record(
    paper: dict[str, Any],
    *,
    classification_source: str = "auto",
    force_reclassify: bool = False,
) -> dict[str, Any]:
    """为单篇论文补全 hierarchy / tags / mindmap_path / keywords_flat。"""
    keywords = paper.get("keywords") or []
    if isinstance(keywords, str):
        keywords = [k.strip() for k in keywords.split("、") if k.strip()]

    if (
        not force_reclassify
        and _hierarchy_nonempty(paper.get("hierarchy"))
        and paper.get("classification_source") in ("manual_override", "manual")
    ):
        return sync_tags_from_hierarchy(paper)

    if not force_reclassify and _hierarchy_nonempty(paper.get("hierarchy")):
        return sync_tags_from_hierarchy(paper)

    hierarchy = classify_keywords(keywords)
    # 当关键词分类为空时，使用文本匹配 fallback
    if not _hierarchy_nonempty(hierarchy):
        hierarchy = classify_from_text(paper)
    paper["hierarchy"] = hierarchy
    paper["hierarchy_tags"] = build_hierarchy_tags(hierarchy)
    paper["mindmap_path"] = build_mindmap_path(hierarchy)
    paper["keywords_flat"] = list(keywords)
    paper["classification_source"] = classification_source
    return paper
