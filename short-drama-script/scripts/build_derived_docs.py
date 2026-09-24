#!/usr/bin/env python3
"""从正本生成派生件：分集场次表 ＋ 台词对照本。

- 分集场次表：整体重建（总览 / 场景使用统计 / 逐集一行一场）。
- 台词对照本：按「(集号, 英文原句)」保留已有中文，新句从项目里的补充映射取，
  都没有就写 `（待补）` 并在结尾列出。
- `--check`：只体检，不写任何文件。

用法：
    python3 build_derived_docs.py <项目目录>
    python3 build_derived_docs.py <项目目录> --check
    python3 build_derived_docs.py <项目目录> --props 兽骨爪,水账板

补充中文映射文件（可选）：<项目目录>/<剧名>-台词中文映射.txt，每行一条：
    集号｜英文原句｜中文大意
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

CN_NUM = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6,
          "七": 7, "八": 8, "九": 9, "十": 10}
DEFAULT_PROPS = ["弓", "箭", "刀", "斧", "撬棍", "工具袋", "水囊", "水桶", "碗", "望远镜",
                 "哨子", "短刃", "钢索", "钢缆", "铁爪", "钢板", "账板", "鞋", "话筒",
                 "电台", "步枪", "子弹", "燃料", "布条", "铁牌", "护齿", "折叠椅",
                 "绞盘", "水泵", "吊闸", "闸门", "水塔"]

SCENE_RE = re.compile(r"^【(\d+)-(\d+)\s+(\S+)\s+(\S+)\s+(.+)】$")
DLG_RE = re.compile(r"^(.+?)（(.+?)）(\[VO\])?：(.+)$")
EP_LABEL_RE = re.compile(r"第\s*([0-9一二三四五六七八九十]+)\s*集\s*[：:]\s*(.+)")


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


def find_episodes(project: Path):
    out = []
    for p in project.glob("第*集.txt"):
        m = re.match(r"^第([一二三四五六七八九十零\d]+)集\.txt$", p.name)
        if m:
            out.append((cn2int(m.group(1)), p))
    return sorted(out)


def parse_header(lines):
    """解析集头区：返回 (剧名, 英文名, 集标签, 集名, 概要块行)。

    三种排法都认：
      C（现行）第一行 `<剧名> · <英文名>`；中间概要块；之后 `第 N 集：<集名>` ＋ 语言声明
      A（旧）  第一行 `<剧名> · <英文名> · 第 N 集：<集名>`；概要块在集头块下面
      B（无英文名）第一行 `<剧名> · 第 N 集：<集名>`
    """
    first = lines[0].strip() if lines else ""
    head, label, ep_name = [], "", ""
    for i, raw in enumerate(lines):
        s = raw.strip()
        if SCENE_RE.match(s):
            break
        m = EP_LABEL_RE.match(s)
        if m and not label:
            label, ep_name = f"第 {m.group(1)} 集", m.group(2).strip()
            continue
        if not s or i == 0 or s.startswith(("(", "（")):
            continue
        head.append(raw)
    stripped = EP_LABEL_RE.sub("", first).strip(" 　·")
    parts = [p.strip() for p in stripped.split("·") if p.strip()]
    title = parts[0] if parts else ""
    english = parts[1] if len(parts) > 1 else ""
    if not label:                      # 集号写在第一行里的老排法
        m = EP_LABEL_RE.search(first)
        if m:
            label, ep_name = f"第 {m.group(1)} 集", m.group(2).strip()
    return title, english, label, ep_name, head


def detect_names(project: Path, eps):
    """返回 (剧名, 英文名)：优先读正本集头区，其次看全局设定文件名。"""
    if eps:
        title, english, _, _, _ = parse_header(
            eps[0][1].read_text(encoding="utf-8").split("\n"))
        if title:
            return title, english
    for cand in project.glob("*-全局设定.txt"):
        return cand.name.split("-全局设定")[0], ""
    return project.name, ""


def parse_episode(path: Path):
    """返回 (head_lines, scenes, meta)。scenes 里 body 收全部非对白行（含续行）。"""
    lines = path.read_text(encoding="utf-8").split("\n")
    title, english, label, ep_name, head = parse_header(lines)
    meta = {"title": title, "english": english, "label": label, "ep_name": ep_name}
    scenes, cur = [], None
    for raw in lines:
        s = raw.strip()
        m = SCENE_RE.match(s)
        if m:
            cur = {"id": f"{m.group(1)}-{m.group(2)}", "time": m.group(3),
                   "io": m.group(4), "loc": m.group(5), "ppl": [], "props": [],
                   "dlg": 0, "body": []}
            scenes.append(cur)
            continue
        if cur is None:
            continue
        if s.startswith("人物："):
            cur["ppl"] = [x.strip() for x in s[3:].split("、") if x.strip()]
            continue
        d = DLG_RE.match(s)
        if d:
            cur["dlg"] += 1
            cur["body"].append(d.group(4))
            continue
        if s:
            cur["body"].append(s)
    return head, scenes, meta


def scene_props(sc: dict, props: list):
    text = " ".join(sc["body"])
    return [p for p in props if p in text]


def build_sheet(title: str, english: str, eps, props: list) -> str:
    parsed = [(n, p, parse_episode(p)) for n, p in eps]
    epnames = {}
    for n, _, (_, _, meta) in parsed:
        epnames[n] = meta["ep_name"] or meta["label"]
    total_scenes = sum(len(s) for _, _, (_, s, _) in parsed)
    total_dlg = sum(sc["dlg"] for _, _, (_, s, _) in parsed for sc in s)
    tm, loc = Counter(), Counter()
    for _, _, (_, scenes, _) in parsed:
        tm.update(sc["time"] for sc in scenes)
        loc.update(sc["loc"] for sc in scenes)

    L = [f"{title}" + (f" · {english}" if english else "") + f" · 分集场次表（全 {len(eps)} 集 · {total_scenes} 场）",
         "用途：排期、资产分派、分镜对账。一行一场，列的含义——",
         "　场号 ｜ 时间/内外 ｜ 场景（资产规范名）｜ 在场人物 ｜ 本场涉及的物件 ｜ 台词数",
         "　“在场人物”就是这一场必须出现在画面里的名单；群像代表未命名的同类角色。",
         "", "━" * 46, "【一】总览", "━" * 46]
    for n, _, (_, scenes, _) in parsed:
        tc = Counter(sc["time"] for sc in scenes)
        ids = Counter(sc["loc"] for sc in scenes)
        dlg = sum(sc["dlg"] for sc in scenes)
        L.append(f"第 {n} 集 · {epnames[n]}")
        L.append(f"　　场 {len(scenes)} ｜ 台词 {dlg} 句 ｜ 时间分布：日 {tc['日']} · 昏 {tc['昏']} · 夜 {tc['夜']} · 晨 {tc['晨']}")
        L.append("　　场景：" + "、".join(f"{k}×{v}" for k, v in ids.most_common()))
    season_night = tm["夜"] / total_scenes * 100 if total_scenes else 0
    L += ["",
          f"全季合计：{total_scenes} 场 ｜ 台词 {total_dlg} 句 ｜ 时间分布 日{tm['日']} 昏{tm['昏']} 夜{tm['夜']} 晨{tm['晨']}"
          f"（夜戏 {season_night:.1f}%，规则 ≤30%）",
          "", "━" * 46, "【二】场景使用统计（做场景资产和布景排期的依据）", "━" * 46]
    for k, v in loc.most_common():
        L.append(f"　{v:>3} 场　{k}")
    L += ["", "━" * 46, "【三】逐集场次表", "━" * 46]
    for n, _, (head, scenes, meta) in parsed:
        L += ["", "┈" * 46]
        L += head
        L += ["┈" * 46, f"◆◆◆ 第 {n} 集：{epnames[n]}", ""]
        for sc in scenes:
            pr = "、".join(scene_props(sc, props)) or "—"
            L.append(f"{sc['id']} ｜ {sc['time']} {sc['io']} ｜ {sc['loc']}")
            L.append(f"　　人物：{'、'.join(sc['ppl'])}")
            L.append(f"　　物件：{pr}　｜　台词 {sc['dlg']} 句")
    return "\n".join(L) + "\n"


def parse_sheet(path: Path):
    """从已有场次表里取出逐场三元组，用于比对。"""
    rows = []
    for line in path.read_text(encoding="utf-8").split("\n"):
        m = re.match(r"^(\d+-\d+)\s*｜\s*(\S+)\s+(\S+)\s*｜\s*(.+?)\s*$", line.strip())
        if m:
            rows.append((m.group(1), m.group(2), m.group(3), m.group(4)))
    return rows


def load_cn_map(project: Path, title: str):
    """补充中文映射：剧名-台词中文映射.txt，每行 集号｜EN｜CN。"""
    out = {}
    for cand in [project / f"{title}-台词中文映射.txt"] + list(project.glob("*台词中文映射*.txt")):
        if not cand.exists():
            continue
        for line in cand.read_text(encoding="utf-8").split("\n"):
            parts = [x.strip() for x in line.split("｜")]
            if len(parts) >= 3 and parts[0].isdigit():
                out[(int(parts[0]), parts[1])] = parts[2]
    return out


def load_cn_from_sheet(path: Path):
    m, ep, i = {}, None, 0
    lines = path.read_text(encoding="utf-8").split("\n")
    while i < len(lines):
        s = lines[i].strip()
        mm = re.match(r"^第 (\d+) 集", s)
        if mm:
            ep = int(mm.group(1))
        if i + 2 < len(lines) and lines[i + 1].strip().startswith("EN｜") and lines[i + 2].strip().startswith("CN｜"):
            m[(ep, lines[i + 1].strip()[3:].strip())] = lines[i + 2].strip()[3:].strip()
            i += 3
            continue
        i += 1
    return m


def rebuild_reference(title: str, english: str, eps, project: Path, cn_map: dict, check: bool):
    """按正本顺序重建对照本；check 模式只返回 (台词条数, 缺中文清单)。"""
    items = []          # ("S", 集, 场号, 时间, 内外, 场景) | ("D", 集, 说话人, 英文)
    for n, p in eps:
        for raw in p.read_text(encoding="utf-8").split("\n"):
            s = raw.strip()
            m = SCENE_RE.match(s)
            if m:
                items.append(("S", n, f"{m.group(1)}-{m.group(2)}", m.group(3), m.group(4), m.group(5)))
                continue
            d = DLG_RE.match(s)
            if d:
                sp = f"{d.group(1)}（{d.group(2)}）" + ("[VO]" if d.group(3) else "")
                items.append(("D", n, sp.strip(), d.group(4).strip()))

    cands = list(project.glob("*台词对照*.txt"))
    have = load_cn_from_sheet(cands[0]) if cands else {}
    def cn_of(n, en):
        cn = cn_map.get((n, en)) or have.get((n, en)) or ""
        return "" if cn.strip() in ("", "（待补）") else cn

    missing = [(x[1], x[3]) for x in items if x[0] == "D" and not cn_of(x[1], x[3])]
    if check:
        return len([x for x in items if x[0] == "D"]), missing

    epnames = {}
    for n, p in eps:
        _, _, _, ep_name, _ = parse_header(p.read_text(encoding="utf-8").split("\n"))
        epnames[n] = ep_name

    out = [f"{title}" + (f" · {english}" if english else "") + f" · 台词对照本（全 {len(eps)} 集）",
           "第一列为正文原句（目标语言；列名沿用 EN｜），第二列为中文大意，仅用于审稿与配音。",
           "场标与集内编号与《第 N 集.txt》一致。", ""]
    last = None
    for x in items:
        if x[1] != last:
            out += ["", "=" * 40, f"第 {x[1]} 集：{epnames.get(x[1], '')}", "=" * 40, ""]
            last = x[1]
        if x[0] == "S":
            out.append(f"【{x[2]} {x[3]} {x[4]} {x[5]}】")
        else:
            en = x[3]
            cn = cn_of(x[1], en) or "（待补）"
            out += [x[2], "　EN｜" + en, "　CN｜" + cn]
    return out, missing


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("project", type=Path)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--only", choices=("all", "sheet", "reference"), default="all",
                    help="只重建其中一份（sheet＝分集场次表，reference＝台词对照本）")
    ap.add_argument("--props", default="")
    args = ap.parse_args()

    project: Path = args.project
    if not project.is_dir():
        print(f"找不到项目目录：{project}", file=sys.stderr)
        return 1
    eps = find_episodes(project)
    if not eps:
        print("没有找到 第N集.txt 正本", file=sys.stderr)
        return 1
    title, english = detect_names(project, eps)
    props = DEFAULT_PROPS + [x.strip() for x in args.props.split(",") if x.strip()]

    sheet_text = build_sheet(title, english, eps, props)
    sheet_path = project / f"{title}-分集场次表.txt"
    legacy = [p for p in project.glob("*分集*.txt") if p.name != sheet_path.name]
    if not sheet_path.exists() and any("分集场次表" in p.name for p in legacy):
        sheet_path = next(p for p in legacy if "分集场次表" in p.name)

    cn_map = load_cn_map(project, title)
    ref, missing = rebuild_reference(title, english, eps, project, cn_map, args.check)

    if args.check:
        print(f"项目：{project}　剧名：{title}")
        new_rows = re.findall(r"^(\d+-\d+)\s*｜\s*(\S+)\s+(\S+)\s*｜\s*(.+?)\s*$", sheet_text, re.M)
        old_rows = [tuple(r) for r in parse_sheet(sheet_path)] if sheet_path.exists() else []
        print(f"分集场次表：正本 {len(new_rows)} 场 ｜ 现有 {len(old_rows)} 场 ｜ "
              f"{'一致' if [tuple(r) for r in new_rows] == old_rows else '不一致（需要重建）'}")
        cands = list(project.glob("*台词对照*.txt"))
        if not cands:
            print("台词对照本：缺（需要生成）")
        else:
            have_en = [l.strip()[3:].strip() for l in cands[0].read_text(encoding="utf-8").split("\n")
                       if l.strip().startswith("EN｜")]
            live = [d.group(4).strip() for _, p in eps
                    for d in (DLG_RE.match(x.strip()) for x in p.read_text(encoding="utf-8").split("\n")) if d]
            same = have_en == live
            print(f"台词对照本：正本 {len(live)} 条 ｜ 对照本 {len(have_en)} 条 ｜ {'逐条一致' if same else '不一致（需要重建）'}"
                  + f" ｜ 缺中文 {len(missing)} 条")
        return 0

    if args.only in ("all", "sheet"):
        sheet_path.write_text(sheet_text, encoding="utf-8")
        print(f"已重建：{sheet_path.name}")
        for p in legacy:
            if p.name != sheet_path.name:
                print(f"注意：项目里还有旧格式的《{p.name}》，本脚本未改动它；确认后请自行留档或删除。")
    if args.only in ("all", "reference"):
        ref_path = project / f"{title}-台词对照本.txt"
        ref_path.write_text("\n".join(ref) + "\n", encoding="utf-8")
        print(f"已重建：{ref_path.name}　缺中文 {len(missing)} 条")
    for n, en in missing[:20]:
        print(f"    第 {n} 集缺中文：{en[:60]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
