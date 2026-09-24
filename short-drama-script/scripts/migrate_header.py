#!/usr/bin/env python3
"""把老排法的集头区迁移成现行标准。

老排法：第一行 `<剧名> · <英文名> · 第 N 集：<集名>`（或 `<剧名> · 第 N 集：<集名>`），
        概要块（本集概要／大场面／人物／场景）排在集头块下面。
现行标准：第一行只写 `<剧名> · <英文名>`；概要块整块提到集头块**上面**；
        集头块 = `第 N 集：<集名>` ＋ 语言声明行。

只动集头区的顺序与拆行，正文（场标题／人物行／动作行／对白行）逐字保留；
写盘前会先备份，写盘后会复验（剧名／集名／场数／台词数必须一致，否则回滚不写）。

用法：
    python3 migrate_header.py <项目目录> --dry-run     # 只报要改哪些集
    python3 migrate_header.py <项目目录>               # 真改（先备份到 备份-集头整改-<YYYYMMDD>/）
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import shutil
import sys
from pathlib import Path

CN_NUM = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6,
          "七": 7, "八": 8, "九": 9, "十": 10}
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


def dissect(lines):
    """拆出 (文档头行, 标题, 英文名, 集标签, 集名, 概要块行, 语言声明行, 正文起始行号)。"""
    first = lines[0].strip() if lines else ""
    label, ep_name, decl = "", "", ""
    head, body_at = [], len(lines)
    for i, raw in enumerate(lines):
        s = raw.strip()
        if SCENE_RE.match(s):
            body_at = i
            break
        m = EP_LABEL_RE.match(s)
        if m and not label:
            label, ep_name = f"第 {m.group(1)} 集", m.group(2).strip()
            continue
        if i == 0 or not s:
            continue
        if s.startswith(("(", "（")):
            decl = decl or raw
            continue
        head.append(raw)
    stripped = EP_LABEL_RE.sub("", first).strip(" 　·")
    parts = [p.strip() for p in stripped.split("·") if p.strip()]
    title = parts[0] if parts else ""
    english = parts[1] if len(parts) > 1 else ""
    if not label:
        m = EP_LABEL_RE.search(first)
        if m:
            label, ep_name = f"第 {m.group(1)} 集", m.group(2).strip()
    return first, title, english, label, ep_name, head, decl, body_at


def counts(lines):
    scenes = sum(1 for s in lines if SCENE_RE.match(s.strip()))
    dlg = sum(1 for s in lines if DLG_RE.match(s.strip()))
    return scenes, dlg


def rebuild(lines):
    _, title, english, label, ep_name, head, decl, body_at = dissect(lines)
    new_title = f"{title} · {english}" if english else title
    while head and not head[0].strip():
        head.pop(0)
    while head and not head[-1].strip():
        head.pop()
    out = [new_title, ""]
    out += head
    out += ["", f"{label}：{ep_name}"]
    if decl:
        out.append(decl)
    out += ["", ""]
    out += lines[body_at:]
    return out, (title, english, label, ep_name)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("project", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    project: Path = args.project
    if not project.is_dir():
        print(f"找不到项目目录：{project}", file=sys.stderr)
        return 1
    eps = find_episodes(project)
    if not eps:
        print("没有找到 第N集.txt 正本", file=sys.stderr)
        return 1

    targets = []
    for n, path in eps:
        lines = path.read_text(encoding="utf-8").split("\n")
        first = lines[0].strip() if lines else ""
        if EP_LABEL_RE.search(first):          # 集号写进第一行 = 老排法
            targets.append((n, path, lines))
    if not targets:
        print("集头区已经是现行排法，无需迁移。")
        return 0

    print(f"待迁移：{len(targets)} 集 —— " + "、".join(p.name for _, p, _ in targets))
    if args.dry_run:
        n, path, lines = targets[0]
        print("\n示例（改后前 12 行）：")
        for l in rebuild(lines)[0][:12]:
            print("   ", l)
        return 0

    backup = project / f"备份-集头整改-{dt.date.today().strftime('%Y%m%d')}"
    backup.mkdir(exist_ok=True)
    for n, path, lines in targets:
        new_lines, meta = rebuild(lines)
        before, after = counts(lines), counts(new_lines)
        _, t2, e2, l2, n2, _, _, _ = dissect(new_lines)
        if (t2, e2, l2, n2) != meta or before != after:
            print(f"跳过 {path.name}：复验不一致（{before} → {after}）", file=sys.stderr)
            return 1
        shutil.copy2(path, backup / path.name)
        path.write_text("\n".join(new_lines), encoding="utf-8")
        print(f"已改：{path.name}（场 {after[0]} · 台词 {after[1]}，备份在 {backup.name}/）")
    print("\n完成。建议接着跑：")
    print(f"  python3 ../short-drama-script/scripts/build_derived_docs.py {project}")
    print(f"  python3 ../short-drama-script-audit/scripts/audit_plain_script.py {project}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
