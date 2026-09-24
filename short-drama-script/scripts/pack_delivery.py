#!/usr/bin/env python3
"""把项目打成交付包，放进 交付/。

包内：正本（第N集.txt）＋ 支持文档（全局设定／整体大纲／台词对照本／分集场次表／交付说明）
      ＋ 审查记录（审查/ 下的 md 与 json，可用 --no-audit 排除）。

与其他打包方式的三点差别，都是踩过坑换来的：
  1. 文件名显式带 UTF-8 标记——macOS 的 zip 默认不打，解压常见乱码；
  2. 写完立刻逐文件回读比对字节，确认包内和项目当前文件一致；
  3. 不覆盖同名包，自动加序号；输出 SHA-256。

用法：
    python3 pack_delivery.py <项目目录>
    python3 pack_delivery.py <项目目录> --label r2 --name 狂沙-WASTELAND-第一季
    python3 pack_delivery.py <项目目录> --dry-run     # 只列清单，不写文件
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import re
import sys
import zipfile
from pathlib import Path

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


def find_episodes(project: Path):
    out = []
    for p in project.glob("第*集.txt"):
        m = re.match(r"^第([一二三四五六七八九十零\d]+)集\.txt$", p.name)
        if m:
            out.append((cn2int(m.group(1)), p))
    return sorted(out)


def detect_title(project: Path, eps):
    if eps:
        first = eps[0][1].read_text(encoding="utf-8").splitlines()[0]
        m = re.match(r"^\s*(.+?)\s*·", first)
        if m:
            return m.group(1).strip()
    for cand in project.glob("*-全局设定.txt"):
        return cand.name.split("-全局设定")[0]
    return project.name


def detect_english(project: Path, eps):
    """从正本第一行 <剧名> · <英文名> · 第 N 集 里取英文名（用于默认包名）。"""
    if eps:
        first = eps[0][1].read_text(encoding="utf-8").splitlines()[0]
        m = re.match(r"^\s*.+?\s*·\s*(.+?)\s*·\s*第", first)
        if m:
            return m.group(1).strip()
    return ""


def collect(project: Path, title: str, with_audit: bool):
    eps = find_episodes(project)
    files = [p for _, p in eps]
    for pat in (f"{title}-全局设定.txt", "*整体大纲*.txt", "*台词对照*.txt",
                f"{title}-分集场次表.txt", "*分集场次表.txt", "*分集表*.txt",
                f"{title}-交付说明.txt", "*交付说明*.txt", "*故事概要*.txt",
                "*制作形态卡*.txt", f"{title}-*.txt"):
        for p in project.glob(pat):
            if p.is_file() and p not in files and "台词中文映射" not in p.name:
                files.append(p)
    if with_audit:
        for p in sorted((project / "审查").glob("*")) if (project / "审查").is_dir() else []:
            if p.is_file() and p.suffix in (".md", ".json"):
                files.append(p)
    return eps, files


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("project", type=Path)
    ap.add_argument("--label", default="r1")
    ap.add_argument("--name", default="")
    ap.add_argument("--out", default="交付")
    ap.add_argument("--no-audit", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    project: Path = args.project
    if not project.is_dir():
        print(f"找不到项目目录：{project}", file=sys.stderr)
        return 1
    eps0 = find_episodes(project)
    if not eps0:
        print("没有找到 第N集.txt 正本", file=sys.stderr)
        return 1
    title = detect_title(project, eps0)
    eps, files = collect(project, title, not args.no_audit)

    day = dt.date.today().strftime("%Y%m%d")
    english = detect_english(project, eps0)
    head = f"{title}-{english}" if english else title
    base = args.name or f"{head}-第一季-全{len(eps)}集-{day}"
    zip_name = f"{base}-{args.label}.zip" if args.label else f"{base}.zip"
    out_dir = project / args.out
    target = out_dir / zip_name
    n = 2
    while target.exists() and not args.dry_run:
        target = out_dir / f"{base}-{args.label}-{n}.zip"
        n += 1

    # 交付前置体检：审查记录是否比正本旧
    newest = max((p.stat().st_mtime for _, p in eps), default=0)
    stale = [p.name for p in sorted((project / "审查").glob("*.json"))
             if p.stat().st_mtime < newest] if (project / "审查").is_dir() else []
    if stale:
        print("提示：这些审查记录比正本旧，交付前建议重审 —— " + "、".join(stale))

    root = f"{base}-{args.label}" if args.label else base
    print(f"项目：{project}　剧名：{title}　正本 {len(eps)} 集")
    print(f"包内 {len(files)} 个文件：")
    for p in files:
        print("   ", p.relative_to(project))
    if args.dry_run:
        print(f"[dry-run] 将要写出：{target}")
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        z.writestr(zipfile.ZipInfo(root + "/"), "")
        for p in files:
            zi = zipfile.ZipInfo(f"{root}/" + str(p.relative_to(project)))
            zi.flag_bits |= 0x800                       # 显式声明 UTF-8 文件名
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            z.writestr(zi, p.read_bytes())

    # 回读比对：包内字节必须与项目当前文件一致
    verify = zipfile.ZipFile(target)
    bad = []
    for p in files:
        name = f"{root}/" + str(p.relative_to(project))
        if verify.read(name) != p.read_bytes():
            bad.append(name)
    ok = verify.testzip() is None and not bad
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    print(f"\n已写出：{target}")
    print(f"大小：{target.stat().st_size:,} bytes")
    print(f"一致性：{'OK（逐文件与项目当前文件字节一致）' if ok else 'FAIL ' + str(bad)}")
    print(f"SHA-256：{digest}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
