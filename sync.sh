#!/usr/bin/env bash
# 在「本仓库」与「~/.codex/skills 安装副本」之间对齐两个 skill。
# 用法：
#   ./sync.sh            仓库 → 安装目录（装最新版）
#   ./sync.sh --check    只比对差异，不动文件
#   ./sync.sh --pull     安装目录 → 仓库（把在安装目录里做的改动收回仓库）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
DEST="${CODEX_SKILLS_DIR:-$HOME/.codex/skills}"
SKILLS=(short-drama-script short-drama-script-audit)
MODE="${1:-push}"

for s in "${SKILLS[@]}"; do
  if [ ! -d "$ROOT/$s" ]; then
    echo "仓库里缺少 $s" >&2
    exit 1
  fi
done
mkdir -p "$DEST"

if [ "$MODE" = "--check" ]; then
  status=0
  for s in "${SKILLS[@]}"; do
    if [ ! -d "$DEST/$s" ]; then
      echo "${s}：安装目录里没有，需要 ./sync.sh"
      status=1
      continue
    fi
    if diff -r -q "$ROOT/$s" "$DEST/$s" >/dev/null; then
      echo "${s}：一致"
    else
      echo "${s}：有差异"
      diff -r -q "$ROOT/$s" "$DEST/$s" | sed 's/^/    /'
      status=1
    fi
  done
  exit "$status"
fi

copy() {  # copy <src> <dst>
  if command -v rsync >/dev/null 2>&1; then
    rsync -a --delete --itemize-changes "$1/" "$2/" | sed 's/^/    /'
  else
    rm -rf "$2"
    mkdir -p "$2"
    cp -R "$1/." "$2/"
    echo "    （已用 cp 覆盖，未列明细）"
  fi
}

for s in "${SKILLS[@]}"; do
  echo "${s}:"
  if [ "$MODE" = "--pull" ]; then
    copy "$DEST/$s" "$ROOT/$s"
  else
    copy "$ROOT/$s" "$DEST/$s"
  fi
done

echo
echo "完成（目标：${DEST}）。提醒：改完 skill 记得 commit 并 push 到 GitHub。"
