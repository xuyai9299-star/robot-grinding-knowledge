# -*- coding: utf-8 -*-
"""v2: 分离会议/期刊，趋势语义分析，时间轴数据"""
import csv, json, re
from pathlib import Path
from collections import defaultdict, Counter

ROOT = Path(__file__).resolve().parents[1]
CSV_DIR = Path(r"d:\SRTP\代码")
OUTPUT_DIR = ROOT / "conferences"

# ============ 配置 ============

CONFERENCE_KEYWORDS = [
    "conference", "proceedings", "symposium", "congress", "workshop",
    "international conference", "ieee international", "asme", "icra", "iros",
    "icarm", "icma", "case", "aim", "icarcv", "ram", "robio",
]

JOURNAL_INDICATORS = [
    "journal", "international journal", "review", "letters", "acta",
    "transactions", "annals", "archive",
]

ABBREV_MAP = {
    "the international journal of advanced manufacturing technology": ("Int J Adv Manuf Technol", "IJAMT", "journal"),
    "robotics and computer-integrated manufacturing": ("Robot Comput Integr Manuf", "RCIM", "journal"),
    "chinese journal of aeronautics": ("Chin J Aeronaut", "CJA", "journal"),
    "journal of manufacturing processes": ("J Manuf Process", "JMP", "journal"),
    "tribology international": ("Tribol Int", "TRIBINT", "journal"),
    "ieee access": ("IEEE Access", "IEEE Access", "journal"),
    "advances in mechanical engineering": ("Adv Mech Eng", "AME", "journal"),
    "proceedings of the institution of mechanical engineers, part b: journal of engineering manufacture": ("Proc IMechE B: J Eng Manuf", "PIMechE-B", "journal"),
    "journal of mechanical science and technology": ("J Mech Sci Technol", "JMST", "journal"),
    "measurement": ("Measurement", "Measurement", "journal"),
    "crystals": ("Crystals", "Crystals", "journal"),
    "international journal of computer integrated manufacturing": ("Int J Comput Integr Manuf", "IJCIM", "journal"),
    "materials and manufacturing processes": ("Mater Manuf Process", "MMP", "journal"),
    "materials": ("Materials", "Materials", "journal"),
    "materials & design": ("Mater Des", "Mater Des", "journal"),
    "journal of materials processing technology": ("J Mater Process Technol", "JMPT", "journal"),
    "applied surface science": ("Appl Surf Sci", "ASS", "journal"),
    "surface and coatings technology": ("Surf Coat Technol", "SCT", "journal"),
    "wear": ("Wear", "Wear", "journal"),
    "precision engineering": ("Precis Eng", "Precis Eng", "journal"),
    "mechanical systems and signal processing": ("Mech Syst Signal Process", "MSSP", "journal"),
    "journal of cleaner production": ("J Clean Prod", "JCP", "journal"),
    "ceramics international": ("Ceram Int", "Ceram Int", "journal"),
    "composites part b: engineering": ("Compos Part B: Eng", "Compos B", "journal"),
    "international journal of machine tools and manufacture": ("Int J Mach Tools Manuf", "IJMTM", "journal"),
    "cirp annals": ("CIRP Annals", "CIRP", "journal"),
    "journal of intelligent manufacturing": ("J Intell Manuf", "JIM", "journal"),
    "robotics and autonomous systems": ("Robot Auton Syst", "RAS", "journal"),
    "engineering applications of artificial intelligence": ("Eng Appl Artif Intell", "EAAI", "journal"),
    "expert systems with applications": ("Expert Syst Appl", "ESA", "journal"),
    "aerospace science and technology": ("Aerosp Sci Technol", "AST", "journal"),
    "acta astronautica": ("Acta Astronaut", "Acta Astronaut", "journal"),
    "ieee/asme transactions on mechatronics": ("IEEE/ASME Trans Mechatron", "TMECH", "journal"),
    "mechanical sciences": ("Mech Sci", "MS", "journal"),
    "advanced engineering informatics": ("Adv Eng Inform", "AEI", "journal"),
}

# 研究方向细分（更精细的分类）
DIRECTION_MAP = {
    # 传统工艺
    "surface roughness": ("表面质量", "传统工艺"),
    "surface integrity": ("表面完整性", "传统工艺"),
    "surface quality": ("表面质量", "传统工艺"),
    "material removal": ("材料去除机理", "传统工艺"),
    "cutting force": ("切削力", "传统工艺"),
    "force control": ("力控制", "传统工艺"),
    "force model": ("力建模", "传统工艺"),
    "chip thickness": ("切屑形成", "传统工艺"),
    "tool path": ("轨迹规划", "传统工艺"),
    "trajectory planning": ("轨迹规划", "传统工艺"),
    "path planning": ("路径规划", "传统工艺"),
    "calibration": ("标定与测量", "传统工艺"),
    # 材料
    "titanium alloy": ("钛合金加工", "材料"),
    "titanium": ("钛合金加工", "材料"),
    "nickel": ("高温合金", "材料"),
    "superalloy": ("高温合金", "材料"),
    "ceramic": ("陶瓷加工", "材料"),
    "composite": ("复合材料", "材料"),
    # 应用
    "aero-engine": ("航空发动机", "应用"),
    "blade": ("叶片加工", "应用"),
    "blisk": ("整体叶盘", "应用"),
    "turbine": ("涡轮部件", "应用"),
    "thin-walled": ("薄壁件", "应用"),
    # 智能方法
    "neural network": ("神经网络", "AI/智能方法"),
    "deep learning": ("深度学习", "AI/智能方法"),
    "machine learning": ("机器学习", "AI/智能方法"),
    "artificial intelligence": ("人工智能", "AI/智能方法"),
    "optimization": ("工艺优化", "AI/智能方法"),
    "genetic algorithm": ("遗传算法", "AI/智能方法"),
    "reinforcement learning": ("强化学习", "AI/智能方法"),
    # 仿真建模
    "finite element": ("有限元仿真", "仿真建模"),
    "simulation": ("仿真", "仿真建模"),
    "prediction": ("预测建模", "仿真建模"),
    "model": ("理论建模", "仿真建模"),
    "digital twin": ("数字孪生", "仿真建模"),
    # 监测
    "condition monitoring": ("状态监测", "智能监测"),
    "wear": ("磨损监测", "智能监测"),
    "sensor": ("传感器", "智能监测"),
    "acoustic emission": ("声发射监测", "智能监测"),
    # 新兴方向
    "additive manufacturing": ("增材制造", "新兴方向"),
    "laser": ("激光加工", "新兴方向"),
    "ultrasonic": ("超声辅助", "新兴方向"),
    "robot": ("机器人加工", "机器人"),
    "robotic": ("机器人加工", "机器人"),
    "digital": ("数字化", "新兴方向"),
    "data-driven": ("数据驱动", "AI/智能方法"),
    "adaptive": ("自适应控制", "AI/智能方法"),
    "intelligent": ("智能制造", "AI/智能方法"),
}

def classify_venue(name):
    """判断是会议还是期刊"""
    name_lower = name.lower().strip()
    # 先检查已知映射
    for key, val in ABBREV_MAP.items():
        if key in name_lower or name_lower in key:
            return val[2]  # "journal" or "conference"
    # 关键词判断
    for kw in CONFERENCE_KEYWORDS:
        if kw in name_lower:
            return "conference"
    for kw in JOURNAL_INDICATORS:
        if kw in name_lower:
            return "journal"
    return "journal"  # 默认期刊


def get_abbrev(name):
    name_lower = name.strip().lower()
    for key, val in ABBREV_MAP.items():
        if key in name_lower or name_lower in key:
            return val[0], val[1]
    # 自动生成
    words = name.split()
    stop = {"the","of","and","in","for","on","a","an","international","journal"}
    content_words = [w for w in words if w.lower() not in stop]
    short = " ".join(content_words[:4]) if content_words else name
    abbrev = "".join(w[0].upper() for w in content_words[:5] if w)
    return short, abbrev


def extract_directions(abstract):
    """从摘要提取研究方向（返回带分类的列表）"""
    found = []
    abstract_lower = (abstract or "").lower()
    for eng_key, (cn_label, category) in DIRECTION_MAP.items():
        if eng_key in abstract_lower:
            found.append({"label": cn_label, "category": category})
    # 去重
    seen = set()
    unique = []
    for d in found:
        if d["label"] not in seen:
            seen.add(d["label"])
            unique.append(d)
    return unique


def parse_csv(filepath):
    papers = []
    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pub_title = (row.get("Publication Title") or "").strip()
            conf_name = (row.get("Conference Name") or "").strip()
            venue = conf_name if conf_name else pub_title
            if not venue:
                continue
            papers.append({
                "key": row.get("Key", ""),
                "title": (row.get("Title") or "").strip(),
                "year": int(row["Publication Year"]) if (row.get("Publication Year") or "").isdigit() else 0,
                "authors": (row.get("Author") or "").strip(),
                "venue": venue,
                "doi": (row.get("DOI") or "").strip(),
                "url": (row.get("Url") or "").strip(),
                "abstract": (row.get("Abstract Note") or "").strip()[:500],
                "type": (row.get("Item Type") or "journalArticle").strip(),
                "directions": extract_directions((row.get("Abstract Note") or "").strip()[:500]),
            })
    return papers


def analyze_trend(papers):
    """分析趋势：不仅统计数量，还分析研究方向变化"""
    if not papers:
        return [], ""

    year_papers = defaultdict(list)
    for p in papers:
        if p["year"]:
            year_papers[p["year"]].append(p)

    years = sorted(year_papers.keys())
    if not years:
        return [], ""

    trend_data = []
    for y in years:
        yp = year_papers[y]
        all_dirs = []
        for p in yp:
            all_dirs.extend(d["label"] for d in p["directions"])
        dir_counts = Counter(all_dirs).most_common(5)
        trend_data.append({
            "year": y,
            "count": len(yp),
            "top_directions": [{"name": d, "count": c} for d, c in dir_counts],
        })

    # 生成趋势描述
    descriptions = []
    for i in range(1, len(trend_data)):
        prev_dirs = set(d["name"] for d in trend_data[i-1]["top_directions"])
        curr_dirs = set(d["name"] for d in trend_data[i]["top_directions"])
        new_dirs = curr_dirs - prev_dirs
        lost_dirs = prev_dirs - curr_dirs
        if new_dirs:
            descriptions.append(f"{trend_data[i]['year']}年新增: {', '.join(list(new_dirs)[:3])}")
        if lost_dirs and i == len(trend_data)-1:
            descriptions.append(f"早期方向: {', '.join(list(lost_dirs)[:3])} 近年减少")

    # 整体趋势总结
    all_years_dirs = defaultdict(list)
    for td in trend_data:
        for d in td["top_directions"]:
            all_years_dirs[d["name"]].append(td["year"])

    rising = []
    declining = []
    for dir_name, ys in all_years_dirs.items():
        if len(ys) >= 2 and max(ys) >= max(years) - 1:
            rising.append(dir_name)
        elif len(ys) <= 1 and max(ys) <= min(years) + 2:
            declining.append(dir_name)

    summary_parts = []
    if rising:
        summary_parts.append(f"近期热门: {', '.join(rising[:4])}")
    if declining:
        summary_parts.append(f"早期关注: {', '.join(declining[:3])}")

    return trend_data, "；".join(summary_parts + descriptions[-3:])


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    all_papers = []
    csv_files = list(CSV_DIR.glob("*.csv"))
    print(f"找到 {len(csv_files)} 个 CSV 文件:")
    for f in csv_files:
        papers = parse_csv(f)
        if papers:
            print(f"  {f.name}: {len(papers)} 篇论文")
            all_papers.extend(papers)

    # 也从 papers_enriched_updated.json 加载爬取的论文
    enriched_path = ROOT / "papers_enriched_updated.json"
    if enriched_path.exists():
        with open(enriched_path, "r", encoding="utf-8") as f:
            enriched = json.load(f)
        enriched_count = 0
        for p in enriched:
            venue = (p.get("venue") or "").strip()
            if not venue:
                continue
            # 跳过已经在 CSV 里的
            all_papers.append({
                "key": f"crawled_{p['id']}",
                "title": p.get("title_en") or p.get("title", ""),
                "year": int(p["year"]) if p.get("year") and str(p["year"]).isdigit() else 0,
                "authors": p.get("authors", ""),
                "venue": venue,
                "doi": p.get("doi", ""),
                "url": p.get("url", ""),
                "abstract": p.get("abstract", "")[:500],
                "type": "journalArticle",
                "directions": extract_directions((p.get("abstract") or "")[:500]),
            })
            enriched_count += 1
        print(f"  papers_enriched_updated.json: {enriched_count} 篇有venue的论文")

    # 按 venue 分组
    venue_papers = defaultdict(list)
    for p in all_papers:
        venue_papers[p["venue"]].append(p)

    # 分离会议/期刊
    conferences = []
    journals = []

    for venue, papers in sorted(venue_papers.items(), key=lambda x: -len(x[1])):
        venue_type = classify_venue(venue)
        full_name, abbrev = get_abbrev(venue)
        years = sorted(set(p["year"] for p in papers if p["year"]))
        trend_data, trend_summary = analyze_trend(papers)

        # 汇总研究方向
        all_dirs = []
        for p in papers:
            all_dirs.extend(d["label"] for d in p["directions"])
        top_dirs = [{"name": d, "count": c} for d, c in Counter(all_dirs).most_common(8)]
        dir_categories = Counter()
        for p in papers:
            for d in p["directions"]:
                dir_categories[d["category"]] += 1
        category_summary = [{"category": c, "count": n} for c, n in dir_categories.most_common()]

        related_papers = []
        for p in sorted(papers, key=lambda x: -(x["year"] or 0)):
            related_papers.append({
                "key": p["key"],
                "title": p["title"],
                "year": str(p["year"]),
                "authors": p["authors"][:120] if p["authors"] else "",
                "doi": p["doi"],
                "url": p["url"],
                "abstract": p["abstract"][:300],
                "directions": [d["label"] for d in p["directions"]],
            })

        # 加载元数据
        metadata = {}
        meta_path = OUTPUT_DIR / "venue_metadata.json"
        if meta_path.exists():
            with open(meta_path, "r", encoding="utf-8") as f:
                meta_all = json.load(f)
            metadata = meta_all.get(abbrev, {}) or meta_all.get(full_name, {}) or {}

        entry = {
            "id": abbrev.replace(" ", "_").replace("/", "_").lower(),
            "full_name": full_name,
            "abbrev": abbrev,
            "paper_count": len(papers),
            "years": years,
            "year_range": f"{min(years)}-{max(years)}" if years else "",
            "trend_data": trend_data,
            "trend_summary": trend_summary,
            "top_directions": top_dirs,
            "category_summary": category_summary,
            "papers": related_papers,
            "website": metadata.get("website", ""),
            "publisher": metadata.get("publisher", ""),
            "scope": metadata.get("scope", ""),
            "impact_factor": metadata.get("impact_factor", ""),
            "frequency": metadata.get("frequency", ""),
            "notes": metadata.get("notes", ""),
        }

        if venue_type == "conference":
            conferences.append(entry)
        else:
            journals.append(entry)

    # 时间轴数据：每年 + 热门方向
    year_directions = defaultdict(lambda: defaultdict(int))
    year_papers_count = defaultdict(int)
    for p in all_papers:
        y = p["year"]
        if not y:
            continue
        year_papers_count[y] += 1
        for d in p["directions"]:
            year_directions[y][d["label"]] += 1

    timeline = []
    for y in sorted(year_papers_count.keys()):
        top = [{"name": d, "count": c} for d, c in Counter(year_directions[y]).most_common(8)]
        timeline.append({
            "year": y,
            "paper_count": year_papers_count[y],
            "top_directions": top,
        })

    # 识别研究方向演变里程碑
    all_labels = set()
    for td in timeline:
        for d in td["top_directions"]:
            all_labels.add(d["name"])

    # 输出
    output = {
        "total_venues": len(conferences) + len(journals),
        "total_conferences": len(conferences),
        "total_journals": len(journals),
        "total_papers": len(all_papers),
        "conferences": conferences,
        "journals": journals,
        "timeline": timeline,
    }

    # 写 conferences.json
    with open(OUTPUT_DIR / "conferences.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # 写 timeline 专用 JSON
    with open(OUTPUT_DIR / "timeline.json", "w", encoding="utf-8") as f:
        json.dump({"timeline": timeline}, f, ensure_ascii=False, indent=2)

    print(f"\n输出: {OUTPUT_DIR}/conferences.json + timeline.json")
    print(f"会议: {len(conferences)}  期刊: {len(journals)}  总计: {len(all_papers)} 篇")
    print(f"时间轴: {len(timeline)} 年 ({min(year_papers_count.keys())}-{max(year_papers_count.keys())})")
    print("\n=== 会议 ===")
    for c in conferences[:10]:
        print(f"  [{c['abbrev']}] {c['full_name'][:45]} — {c['paper_count']}篇 | {c['trend_summary'][:60]}")
    print("\n=== 期刊 TOP 10 ===")
    for j in journals[:10]:
        print(f"  [{j['abbrev']}] {j['full_name'][:45]} — {j['paper_count']}篇")


if __name__ == "__main__":
    main()
