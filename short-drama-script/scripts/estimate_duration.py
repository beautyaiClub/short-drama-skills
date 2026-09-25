#!/usr/bin/env python3
"""按分析系统的时长口径，估算一集（或一场）的成片秒数。

算法与校准依据见 references/timing-model.md。摘要：
    台词秒 = Σ(对白正文字数 ÷ 语速 ÷ 语言系数) + 0.4×句数      （只数冒号后面的字）
    动作秒 = max(含动作句数, 可演动作个数) × 2.5               （可演动作 = ▲ 行）
    场需求 ≈ max(台词秒, 动作秒) + 0.5×min(…)                  （逐场算再相加）
    实测拟合：秒 ≈ 15 + 0.077 × 正文字数

用法：
    python3 estimate_duration.py <剧本文件> [--rate 4.5] [--lang 1.0] [--spec 90]
    python3 estimate_duration.py 第一集.txt --spec 90      # 按 90 秒规格自查

有《*全局设定*.txt》且里面写了「成片规格：单集 90 秒」时，--spec 可省。
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SCENE = re.compile(r"^【(\d+-\d+)\s+(\S+)\s+(\S+)\s+(.+)】$")
DLG = re.compile(r"^([^（：]{1,14})(（[^）]*）)?(\[VO\]|\[OS\])?：(.+)$")
UNIT = 2.5                 # 一个可演动作折算秒数
FIT = (15.0, 0.077)        # 秒 ≈ a + b×正文字数
SPEC_RE = re.compile(r"成片规格[：:]\s*[^\n]*?(\d+)\s*秒")


def parse_scenes(path: Path):
    scenes, cur = [], None
    for raw in path.read_text(encoding="utf-8").split("\n"):
        s = raw.strip()
        m = SCENE.match(s)
        if m:
            cur = {"id": m.group(1), "dlg": [], "act": 0, "env": 0, "chars": 0}
            scenes.append(cur)
            continue
        if s.startswith("【") and not m:
            cur = None                       # 场外的说明块不算
            continue
        if cur is None or not s or s.startswith("人物："):
            continue
        cur["chars"] += len(re.sub(r"\s", "", s))
        if s.startswith("▲"):
            cur["act"] += 1
            continue
        if s.startswith("△"):
            cur["env"] += 1
            continue
        d = DLG.match(s)
        if d and not s.startswith(("本集", "第")):
            cur["dlg"].append(d.group(4).strip())
    return scenes


def read_spec(path: Path):
    for f in path.parent.glob("*全局设定*.txt"):
        m = SPEC_RE.search(f.read_text(encoding="utf-8"))
        if m:
            return int(m.group(1))
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("script", type=Path)
    ap.add_argument("--rate", type=float, default=4.5, help="语速（字/秒）")
    ap.add_argument("--lang", type=float, default=1.0, help="语言系数")
    ap.add_argument("--spec", type=int, default=None, help="目标单集秒数")
    args = ap.parse_args()

    scenes = parse_scenes(args.script)
    if not scenes:
        print("没解析到场标题【N-M 时间 内／外 场景】", file=sys.stderr)
        return 1

    print(f"{args.script.name}　语速 {args.rate} 字/秒　语言系数 {args.lang}")
    print()
    print(f"{'小场':<8}{'对白':<5}{'对白字':<7}{'可演动作':<9}{'环境':<5}"
          f"{'台词秒':<8}{'动作秒':<8}{'并行':<7}")
    print("-" * 62)
    parallel = 0.0
    for sc in scenes:
        nc = sum(len(t) for t in sc["dlg"])
        say = nc / args.rate / args.lang + 0.4 * len(sc["dlg"])
        act = sc["act"] * UNIT
        both = max(say, act) + 0.5 * min(say, act)
        parallel += both
        print(f"{sc['id']:<8}{len(sc['dlg']):<5}{nc:<7}{sc['act']:<9}{sc['env']:<5}"
              f"{say:<8.1f}{act:<8.1f}{both:<7.1f}")

    chars = sum(sc["chars"] for sc in scenes)
    dlg_n = sum(len(sc["dlg"]) for sc in scenes)
    dlg_c = sum(sum(len(t) for t in sc["dlg"]) for sc in scenes)
    act_n = sum(sc["act"] for sc in scenes)
    est = FIT[0] + FIT[1] * chars

    print("-" * 62)
    print(f"正文字数 {chars}　对白 {dlg_n} 句／{dlg_c} 字　可演动作 {act_n} 条"
          f"　分镜 {len(scenes)} 个")
    print(f"逐场并行折算 {parallel:.1f} 秒")
    print(f"按实测拟合（15 + 0.077×字数）预计成片 **{est:.0f} 秒**")

    spec = args.spec or read_spec(args.script)
    if spec:
        lo, hi = int(spec * 0.95), int(spec * 1.05)
        lo_c, hi_c = int((lo - FIT[0]) / FIT[1]), int((hi - FIT[0]) / FIT[1])
        print(f"目标 {lo}–{hi} 秒 ⇒ 正文 {lo_c}–{hi_c} 字", end="")
        if chars < lo_c:
            print(f"　⚠ 偏短，还差约 {lo_c - chars} 字（或补 2–4 个可演动作）")
        elif chars > hi_c:
            print(f"　⚠ 偏长，超出约 {chars - hi_c} 字（先砍动作，别砍台词）")
        else:
            print("　✓ 在区间内")
    else:
        print("提示：没声明成片规格（《全局设定》里写「成片规格：单集 90 秒」），"
              "本次不判达标")
    return 0


if __name__ == "__main__":
    sys.exit(main())
