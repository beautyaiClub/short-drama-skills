#!/usr/bin/env python3
"""Generate a clean complete-season TXT from canonical per-episode scripts.

Front matter is an authored synopsis and character guide. Episode preambles are
omitted; episode titles and scene bodies are preserved. This is a reading export,
not a replacement for the canonical scripts or their production metadata.
"""
from __future__ import annotations
import argparse
import os
from pathlib import Path
import re
import tempfile

NUM = r"[0-9零〇一二三四五六七八九十百千两]+"
FILE_RE = re.compile(rf"第({NUM})集\.txt")
HEADER_RE = re.compile(rf"^第\s*({NUM})\s*集\s*[：:]\s*\S.*$", re.M)
SCENE_RE = re.compile(r"^【(\d+)-(\d+)\s+[^\n]+】\s*$", re.M)


def number(value: str) -> int:
    if value.isascii() and value.isdigit():
        return int(value)
    digits = dict(zip("零〇一二三四五六七八九两", [0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 2]))
    units = {"十": 10, "百": 100, "千": 1000}
    total = pending = 0
    for char in value:
        if char in digits:
            pending = digits[char]
        elif char in units:
            total += (pending or 1) * units[char]
            pending = 0
        else:
            raise ValueError(f"无法识别集号：{value}")
    return total + pending


def render(project: Path, front_matter: Path, expected: int | None = None) -> tuple[str, list[Path]]:
    front = front_matter.read_text(encoding="utf-8-sig").strip()
    if not front or HEADER_RE.search(front) or SCENE_RE.search(front):
        raise ValueError("前言须为非空的全剧概要与人物一览，不得包含分集头或场正文")
    episodes: dict[int, Path] = {}
    for file in project.glob("第*集.txt"):
        match = FILE_RE.fullmatch(file.name)
        if match:
            ep = number(match[1])
            if ep < 1 or ep in episodes:
                raise ValueError(f"集号非法或重复：{file.name}")
            episodes[ep] = file
    if not episodes:
        raise ValueError("项目根目录没有单集正本")
    count = expected if expected is not None else max(episodes)
    if count < 1 or set(episodes) != set(range(1, count + 1)):
        raise ValueError(f"正本须从第1集连续至第{count}集；实有 {sorted(episodes)}")
    parts = [front]
    sources = [episodes[n] for n in sorted(episodes)]
    for ep, file in sorted(episodes.items()):
        source = file.read_text(encoding="utf-8-sig")
        headers = list(HEADER_RE.finditer(source))
        if len(headers) != 1 or number(headers[0][1]) != ep:
            raise ValueError(f"{file.name} 的唯一集头与文件集号不符")
        header = headers[0]
        scenes = list(SCENE_RE.finditer(source, header.end()))
        if not scenes or [(int(m[1]), int(m[2])) for m in scenes] != [(ep, n) for n in range(1, len(scenes) + 1)]:
            raise ValueError(f"{file.name} 场号缺漏、错序或没有场正文")
        # Strip only preamble / repeated language declarations. Do not summarize,
        # translate, normalize or filter anything in the actual scene body.
        body = source[scenes[0].start():].strip()
        parts.append(header[0].strip() + "\n\n" + body)
    return "\n\n\n".join(parts) + "\n", sources


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("--front-matter", required=True, type=Path, help="已写好的概要与人物一览 TXT")
    parser.add_argument("--output", required=True, type=Path, help="派生的全集 TXT")
    parser.add_argument("--expected-episodes", type=int, help="已知季集数；检查缺集及多集")
    parser.add_argument("--check", action="store_true", help="比对现有全集，不写文件")
    args = parser.parse_args()
    try:
        content, sources = render(args.project, args.front_matter, args.expected_episodes)
        if args.output.resolve() in {f.resolve() for f in [args.front_matter, *sources]}:
            raise ValueError("输出不得覆盖前言源或单集正本")
        if args.check:
            if not args.output.exists() or args.output.read_bytes() != content.encode("utf-8"):
                raise ValueError("全集缺失或已落后于当前正本／前言；请重新生成")
            print(f"全集一致：{len(sources)}集，前言与各场正文逐字一致")
        else:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=args.output.parent, delete=False) as out:
                temp = Path(out.name)
                out.write(content)
            try:
                os.replace(temp, args.output)
            finally:
                temp.unlink(missing_ok=True)
            print(f"已生成：{args.output}（{len(sources)}集，UTF-8，无BOM）")
    except (OSError, UnicodeError, ValueError) as error:
        parser.exit(1, f"错误：{error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
