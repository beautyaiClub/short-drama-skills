#!/usr/bin/env python3
"""纯剧本格式机械校验（场标题＋人物行＋△动作行＋对白行）。

检查项见 references/audit-checklist.md 里标 [机] 的那些。三条设计约束：
  1. 对账要比**台词正文**，不是只比说话人；
  2. 扫描正文要**含换行后的续行**，不能只看 △ 开头的行；
  3. 一切按**集内定位**，避免跨集重复句改错行。

项目里若有《*全局设定*.txt》，脚本会读它的资产命名表（S／CH／PR）当白名单；
若有《*台词对照本*.txt》，会与正本逐条对账。没有也能跑，白名单类检查自动降级。

用法：
    python3 audit_plain_script.py <项目目录>
    python3 audit_plain_script.py <项目目录> --json report.json
    python3 audit_plain_script.py <项目目录> --strict      # WARN 也算失败

退出码：0 = 无 FAIL；1 = 有 FAIL（或 --strict 下有 WARN）。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

TIMES = ("日", "昏", "夜", "晨")
IOS = ("内", "外")
GROUP_SUFFIX = "群像"
ANON_SPEAKERS = {
    "掠夺者", "掠夺者甲", "掠夺者乙", "掠夺者丙", "掠夺者守卫", "掠夺者随从",
    "掠夺者杀手", "掠夺者搜索队", "护卫", "杀手", "守卫", "女战士", "营地女战士",
    "那个女战士", "首领", "军官", "领头的", "军官甲", "人群", "孩子", "孩子们",
    "获救的人", "被掳的人", "未知",
}
VEHICLE_SUFFIX = ("车", "之王", "闸门", "吊闸", "水塔", "装置", "电台")
OLD_FIELDS = ("镜号", "景别：", "景别:", "机位", "焦段", "时长：", "时长:",
              "画面：", "声音：", "衔接：", "运镜：", "镜头")
LIGHT_HINT = ("火", "灯", "月", "炉", "盆", "炭", "焰", "焊枪", "光")
TIME_CARRIER = ("天刚亮", "天快亮", "天将亮", "天亮了", "天亮", "天黑", "天已黑",
                "天已经黑", "天完全黑", "入夜", "夜里", "夜，", "黄昏", "日落",
                "日头", "正午", "中午", "下午", "早上", "早晨", "白天", "斜光",
                "月光", "后半夜", "整夜", "两天之后", "半天过去", "太阳", "次日",
                "天刚黑", "黑透", "天黑之后")
# 只认"声源不在画面里"的词：设备名（无线电／电台／电话）不算——
# 角色当场对着无线电说话时人是看得见的，标了 [VO] 反而错。
VO_HINT = ("喇叭", "画外", "传来", "传过来", "从谷外", "从远处", "从射程外",
           "从车窗", "录音", "广播")
VO_NEG = ("没有回", "没回", "不回", "没有回答")   # "Lena（没有回喇叭）" 这类是现场反应，不算场外声
MIN_DIALOGUE = 50
DUP_MIN_CHARS = 12

SCENE_RE = re.compile(r"^【(\d+)-(\d+)\s+(\S+)\s+(\S+)\s+(.+)】$")
DLG_RE = re.compile(r"^(.+?)（(.+?)）(\[VO\])?：(.+)$")
# 集标题行（`<剧名> · <英文名> · 第 N 集：<集名>`）；不同项目的剧名不同，按形状认，不写死剧名。
TITLE_RE = re.compile(r"^.+ · .+ · 第 ?[0-9一二三四五六七八九十]+ ?集")
# 集头块行（现行标准：`第 N 集：<集名>`，单独一行）
EP_LABEL_RE = re.compile(r"^第\s*[0-9一二三四五六七八九十]+\s*集\s*[：:]\s*.+")
# 集号写在第一行里的老排法（不锚定，用于识别 `剧名 · 英文名 · 第 N 集：<集名>`）
EP_INLINE_RE = re.compile(r"第\s*[0-9一二三四五六七八九十]+\s*集\s*[：:]\s*.+")
LOOSE_DLG_RE = re.compile(r"^(.+?)(?:（(.*?)）)?(\[VO\])?：(.+)$")
CN_NUM = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6,
          "七": 7, "八": 8, "九": 9, "十": 10}


def cn2int(t: str) -> int:
    t = t.strip()
    if t.isdigit():
        return int(t)
    if t.startswith("十"):
        return 10 + CN_NUM.get(t[1:], 0)
    if "十" in t:
        a, _, b = t.partition("十")
        return CN_NUM.get(a, 0) * 10 + (CN_NUM.get(b, 0) if b else 0)
    return CN_NUM.get(t, 0)


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def find_episodes(project: Path):
    out = []
    for p in sorted(project.glob("第*集.txt")):
        m = re.match(r"^第([一二三四五六七八九十零\d]+)集\.txt$", p.name)
        if m:
            out.append((cn2int(m.group(1)), p))
    return sorted(out)


def parse_settings(project: Path):
    """返回 (场景母名→子视图集合, 人物集合, 物品集合, 是否有资产表)。"""
    cands = list(project.glob("*全局设定*.txt"))
    if not cands:
        return {}, set(), set(), False
    text = read(cands[0])
    scenes = {}
    for m in re.finditer(r"^(S\d+)\s+(\S+?)｜子视图：(.+)$", text, re.M):
        subs = m.group(3).split("——")[0]
        scenes[m.group(2)] = {x.strip() for x in re.split(r"\s*/\s*", subs) if x.strip()}
    people = {m.group(1).strip() for m in re.finditer(r"^CH-\d+\s+([^｜（\n]+)", text, re.M)}
    props = {m.group(1).strip() for m in re.finditer(r"^PR-\d+\s+([^｜（\n]+)", text, re.M)}
    return scenes, people, props, True


def split_scenes(text: str, ep_no: int):
    """切场。body 收**全部非对白行**（含续行），对白单独存。"""
    scenes, cur = [], None
    for raw in text.split("\n"):
        s = raw.strip()
        m = SCENE_RE.match(s)
        if m:
            cur = {"head": s, "num": int(m.group(2)), "id": f"{m.group(1)}-{m.group(2)}",
                   "ep": int(m.group(1)), "time": m.group(3), "io": m.group(4),
                   "loc": m.group(5), "people": [], "body": [], "dlg": [], "line": 0}
            scenes.append(cur)
            continue
        if cur is None:
            continue
        if s.startswith("人物："):
            cur["people"] = [x.strip() for x in s[3:].split("、") if x.strip()]
            continue
        d = DLG_RE.match(s)
        if d:
            cur["dlg"].append({"sp": d.group(1).strip(), "cue": d.group(2).strip(),
                               "vo": bool(d.group(3)), "text": d.group(4).strip(),
                               "line": cur["line"]})
            continue
        if not s or TITLE_RE.match(s) or EP_LABEL_RE.match(s) or \
                s.startswith(("【", "(", "（", "本集", "━", "┈", "=", "—")):
            continue
        cur["body"].append(s)
    return scenes


def check_episode(ep_no: int, path: Path, wl, people, props, has_assets, out: list, flags=None):
    text = read(path)
    lines = [l.strip() for l in text.split("\n")]
    name = path.name

    def add(level, scene, kind, msg):
        out.append({"level": level, "file": name, "scene": scene, "kind": kind, "msg": msg})

    # M1 集头区（范围＝文件开头到第一场；现行排法里概要块在集头块上面，比 12 行更长）
    head_end = next((i for i, s in enumerate(lines) if SCENE_RE.match(s.strip())), len(lines))
    head_area = lines[:head_end]
    head = "\n".join(head_area)
    for key in ("本集概要", "【本集大场面】", "本集人物：", "本集场景："):
        if key not in head:
            add("FAIL", "-", "集头缺块", f"缺「{key}」")
    decl = next((s for s in head_area
                 if s.startswith(("(", "（")) and ("台词" in s or "对白" in s)), "")
    if not decl:
        add("WARN", "-", "语言声明", "集头区没找到语言声明行（括号开头、说明台词语言的那一行）")

    # M1b 集头区顺序：文档头（剧名 · 英文名）→ 概要块 → 集头块（`第 N 集：<集名>` ＋ 语言声明）
    first = lines[0].strip() if lines else ""
    ep_idx = next((i for i, s in enumerate(head_area) if EP_LABEL_RE.match(s.strip())), None)
    sum_idx = next((i for i, s in enumerate(head_area) if s.strip().startswith("本集概要")), None)
    if EP_INLINE_RE.search(first):
        if flags is not None:
            flags.setdefault("old_header", []).append(name)
    elif ep_idx is not None and sum_idx is not None and ep_idx < sum_idx:
        add("WARN", "-", "集头顺序", "「第 N 集：<集名>」排在概要块前面；现行标准是先概要块、后集头块")

    # M2 旧格式字段
    for i, s in enumerate(lines, 1):
        if s.startswith("人物：") or DLG_RE.match(s):
            continue
        for w in OLD_FIELDS:
            if w in s:
                add("FAIL", "-", "旧格式字段", f"L{i} 出现「{w}」：{s[:46]}")
                break

    # M3 说明文字里的他/她
    for i, s in enumerate(lines, 1):
        if s.startswith("人物：") or DLG_RE.match(s):
            continue
        if "他" in s or "她" in s:
            add("FAIL", "-", "他她代词", f"L{i}：{s[:56]}")

    scenes = split_scenes(text, ep_no)
    if not scenes:
        add("FAIL", "-", "场标题", "没有解析到任何场标题")
        return scenes

    # M4–M7 场标题
    for idx, sc in enumerate(scenes, 1):
        if sc["ep"] != ep_no:
            add("FAIL", sc["id"], "场号集号不符", f"与文件名第 {ep_no} 集不一致")
        if sc["num"] != idx:
            add("FAIL", sc["id"], "场号不连续", f"本集第 {idx} 场写成了 {sc['id']}")
        if sc["time"] not in TIMES:
            add("FAIL", sc["id"], "场头时间", f"「{sc['time']}」不属于 {'／'.join(TIMES)}")
        if sc["io"] not in IOS:
            add("FAIL", sc["id"], "场头内外", f"「{sc['io']}」不是 内／外")
        base, _, sub = sc["loc"].partition("·")
        if base.startswith("PR-"):
            if not sub:
                add("WARN", sc["id"], "载具取景缺子视图", f"「{sc['loc']}」建议写成 PR-01 拖船·驾驶舱 这类")
        elif has_assets:
            if base not in wl:
                add("WARN", sc["id"], "场景不在资产表", f"「{base}」")
            elif not sub:
                add("WARN", sc["id"], "场景缺子视图",
                    f"「{sc['loc']}」只有母场景名；同母名多场会让分镜重复同一套景")
            elif sub not in wl[base]:
                add("WARN", sc["id"], "子视图未声明", f"「{sub}」不在 {base} 的子视图清单里")

    # M8–M10 人物行
    for sc in scenes:
        if not sc["people"]:
            add("FAIL", sc["id"], "缺人物行", "场标题下没有「人物：」行")
            continue
        base_names = [p.replace(" [VO]", "").strip() for p in sc["people"]]
        for p in sc["people"]:
            raw = p.replace(" [VO]", "").strip()
            if any(c in p for c in "（）") or "；" in p:
                add("FAIL", sc["id"], "人物行写法", f"「{p}」带中文注释或分号")
            if raw.endswith(VEHICLE_SUFFIX) or raw in props:
                add("FAIL", sc["id"], "载具进人物行", f"「{raw}」是资产不是人物")
            elif has_assets and raw not in people and GROUP_SUFFIX not in raw and raw not in ANON_SPEAKERS:
                add("WARN", sc["id"], "人物不在人物表", f"「{raw}」")
        for d in sc["dlg"]:
            if d["sp"] in ANON_SPEAKERS or GROUP_SUFFIX in d["sp"]:
                continue
            if has_assets and d["sp"] not in base_names:
                add("FAIL", sc["id"], "说话人不在人物行", f"「{d['sp']}」未写进本场人物行")
        if has_assets:
            body = " ".join(sc["body"])
            for nm in people:
                if nm in body and nm not in base_names:
                    add("WARN", sc["id"], "正文有人未列（需人工确认）",
                        f"正文出现「{nm}」，本场人物行没有；若是物主（X 的车）或不在此处（某人不在这里）请忽略")

    # M11 场外声缺 [VO]
    for sc in scenes:
        for d in sc["dlg"]:
            if d["vo"]:
                continue
            if any(n in d["cue"] for n in VO_NEG):
                continue
            if any(h in d["cue"] for h in VO_HINT):
                add("WARN", sc["id"], "疑似缺 [VO]",
                    f"「{d['sp']}（{d['cue']}）」像场外声，配音需要 [VO] 区分")

    # M12 夜戏光源
    for sc in scenes:
        if sc["time"] != "夜":
            continue
        alltext = " ".join(sc["body"]) + " " + " ".join(d["text"] for d in sc["dlg"])
        if not any(h in alltext for h in LIGHT_HINT):
            add("WARN", sc["id"], "夜戏缺光源", "整场没写主光来自火／灯／月／炉／焊枪")

    # M13 时间变化接缝的时间承载
    for a, b in zip(scenes, scenes[1:]):
        if a["time"] == b["time"]:
            continue
        head_text = " ".join(b["body"][:3]) + " " + (b["dlg"][0]["text"] if b["dlg"] else "")
        if not any(c in head_text for c in TIME_CARRIER):
            add("WARN", b["id"], "接缝缺时间承载",
                f"{a['id']}({a['time']})→{b['id']}({b['time']})：开场没交代过了多久")

    # M14 同集重复台词（含近似）
    seen = {}
    for sc in scenes:
        for d in sc["dlg"]:
            t = d["text"]
            if len(t) < DUP_MIN_CHARS:
                continue
            if t in seen and seen[t] != d["sp"]:
                add("WARN", sc["id"], "同集台词复用",
                    f"「{t[:34]}」与 {seen[t]} 说的完全一样")
            seen.setdefault(t, d["sp"])

    # M15 台词量
    total = sum(len(sc["dlg"]) for sc in scenes)
    if total < MIN_DIALOGUE:
        add("WARN", "-", "台词量不足", f"本集 {total} 句（口径 ≥{MIN_DIALOGUE}）")
    return scenes


def project_check(project: Path, eps, has_assets: bool, sheet_rows, out):
    """P 类：项目与交付层——支持文档、派生件同步、审查与交付目录、两份标准是否同源。"""
    def add(level, kind, msg):
        out.append({"level": level, "file": "-", "scene": "-", "kind": kind, "msg": msg})

    docs = {
        "全局设定（资产命名表）": list(project.glob("*全局设定*.txt")),
        "整体大纲": list(project.glob("*整体大纲*.txt")) or list(project.glob("*大纲*.txt")),
        "台词对照本": list(project.glob("*台词对照*.txt")),
        "分集场次表": (list(project.glob("*分集场次表*.txt")) or list(project.glob("*分集表*.txt"))),
    }
    for name, cands in docs.items():
        if not cands:
            add("WARN", "支持文档缺失", f"没有找到《{name}》")
    if not has_assets:
        add("WARN", "缺资产命名表",
            "没有《*全局设定*.txt》：场景／人物／道具校验已降级，结论最高只能写 PROVISIONAL")

    sheets = docs["分集场次表"]
    if sheets:
        rows = []
        for line in read(sheets[0]).split("\n"):
            m = re.match(r"^(\d+-\d+)\s*｜\s*(\S+)\s+(\S+)\s*｜\s*(.+?)\s*$", line.strip())
            if m:
                rows.append((m.group(1), m.group(2), m.group(3), m.group(4)))
        if not rows:
            add("WARN", "场次表不可对账", f"《{sheets[0].name}》里没有解析到逐场行")
        elif rows != [tuple(r) for r in sheet_rows]:
            add("FAIL", "场次表与正本脱钩",
                f"《{sheets[0].name}》{len(rows)} 场 / 正本 {len(sheet_rows)} 场：场号·时间·场景有出入，需重建")

    refs = docs["台词对照本"]
    if refs:
        gaps = sum(1 for l in read(refs[0]).split("\n")
                   if l.strip().startswith("CN｜") and "（待补）" in l)
        if gaps:
            add("WARN", "对照本缺中文", f"《{refs[0].name}》有 {gaps} 条写成（待补）")

    deliv = project / "交付"
    zips = sorted(deliv.glob("*.zip")) if deliv.is_dir() else []
    if not zips:
        add("WARN", "没有交付物", "交付/ 里没有 zip（导出的 PDF 不参与本项）")
    else:
        newest_zip = max(zips, key=lambda p: p.stat().st_mtime)
        srcs = [p for _, p in eps] + [c for cands in docs.values() for c in cands]
        newest_src = max((p.stat().st_mtime for p in srcs), default=0)
        if newest_zip.stat().st_mtime < newest_src:
            add("WARN", "交付包比项目旧", f"《{newest_zip.name}》早于项目最新改动（正本或支持文档），交付前重打")

    audit_dir = project / "审查"
    records = [p for p in audit_dir.glob("*.md")] if audit_dir.is_dir() else []
    if not records:
        add("WARN", "没有审查记录", "审查/ 为空：确认是首审，还是漏了留档")
    elif not any("轮" in p.name for p in records):
        add("WARN", "审查记录命名", "建议按 全季-审查-第N轮.md / EPnn-审查-第N轮.md 命名，便于复审定位")

    peer = Path(__file__).resolve().parents[1].parent / "short-drama-script" / "references"
    if peer.is_dir():
        for f in ("format-spec.md", "project-layout.md"):
            a = Path(__file__).resolve().parents[1] / "references" / f
            b = peer / f
            if a.exists() and b.exists() and hashlib.sha256(a.read_bytes()).hexdigest() != \
                    hashlib.sha256(b.read_bytes()).hexdigest():
                add("WARN", "标准副本漂移", f"{f} 与 $short-drama-script 的副本不一致，请同步两份")


def rebuild_check(project: Path, script_lines, out):
    """M16 台词对照本：与正本逐条对账（比正文）。"""
    cands = list(project.glob("*台词对照*.txt"))
    if not cands:
        return
    text = read(cands[0])
    sheet = [l.strip()[3:].strip() for l in text.split("\n") if l.strip().startswith("EN｜")]
    if not sheet:
        out.append({"level": "WARN", "file": cands[0].name, "scene": "-",
                    "kind": "对照本不可解析", "msg": "没有找到 EN｜ 行"})
        return
    if len(sheet) != len(script_lines):
        out.append({"level": "FAIL", "file": cands[0].name, "scene": "-",
                    "kind": "对照本条数不符",
                    "msg": f"对照本 {len(sheet)} 条 / 正本 {len(script_lines)} 条"})
        return
    for i, (a, b) in enumerate(zip(script_lines, sheet), 1):
        if a != b:
            out.append({"level": "FAIL", "file": cands[0].name, "scene": f"第 {i} 条",
                        "kind": "对照本与正本不一致",
                        "msg": f"正本「{a[:40]}」↔ 对照本「{b[:40]}」"})
            return


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("project", type=Path)
    ap.add_argument("--json", type=Path)
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()
    project = args.project
    if not project.is_dir():
        print(f"找不到项目目录：{project}", file=sys.stderr)
        return 1
    eps = find_episodes(project)
    if not eps:
        print("没有找到 第N集.txt 正本", file=sys.stderr)
        return 1

    wl, people, props, has_assets = parse_settings(project)
    out = []
    script_lines = []
    sheet_rows = []
    flags = {}
    total_scenes = 0
    for ep_no, path in eps:
        scs = check_episode(ep_no, path, wl, people, props, has_assets, out, flags)
        total_scenes += len(scs)
        for sc in scs:
            script_lines += [d["text"] for d in sc["dlg"]]
            sheet_rows.append((sc["id"], sc["time"], sc["io"], sc["loc"]))
    if flags.get("old_header"):
        fs = flags["old_header"]
        out.append({"level": "WARN", "file": "-", "scene": "-",
                    "kind": "集头顺序（老排法）",
                    "msg": f"{len(fs)} 集仍把集号写在第一行（{fs[0]} 等）；现行标准："
                           f"第一行只留「<剧名> · <英文名>」，概要块提到集头块上面，"
                           f"集头块单独写「第 N 集：<集名>」＋语言声明"})
    rebuild_check(project, script_lines, out)
    project_check(project, eps, has_assets, sheet_rows, out)

    fails = [f for f in out if f["level"] == "FAIL"]
    warns = [f for f in out if f["level"] == "WARN"]
    print(f"正本 {len(eps)} 集 ｜ 场 {total_scenes} ｜ 台词 {len(script_lines)} 句")
    print(f"FAIL {len(fails)} ｜ WARN {len(warns)}")
    for f in fails + warns:
        print(f"  [{f['level']}] {f['file']} {f['scene']} · {f['kind']}：{f['msg']}")
    if args.json:
        args.json.write_text(json.dumps(
            {"episodes": [p.name for _, p in eps], "fail": len(fails),
             "warn": len(warns), "findings": out}, ensure_ascii=False, indent=2),
            encoding="utf-8")
    return 1 if (fails or (args.strict and warns)) else 0


if __name__ == "__main__":
    sys.exit(main())
