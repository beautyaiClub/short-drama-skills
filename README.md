# short-drama-skills

两个 Codex skill，构成短剧剧本「写 → 审 → 交」的标准闭环：

| skill | 职责 | 入口 |
|---|---|---|
| `short-drama-script` | 写纯剧本格式（场次本）剧本；维护项目骨架（全局设定／整体大纲／台词对照本／分集场次表）；生成派生件；打包交付 | `SKILL.md` |
| `short-drama-script-audit` | 审查同一格式的剧本：机械校验、连续性、接缝、台词、项目与交付层；出审查记录与结论 | `SKILL.md` |

两边的 `references/format-spec.md`、`references/project-layout.md` 是**逐字节同源副本**，
改一处必须改两处；审查脚本会做 hash 比对，漂移会在检查里报出来。

## 安装 / 同步

仓库是**源**，`~/.codex/skills/` 是安装副本。改完用仓库根目录的脚本对齐：

```bash
./sync.sh              # 仓库 → ~/.codex/skills（装最新版）
./sync.sh --check      # 只比对差异，不动文件
```

手动安装也可以（把两个目录拷进 skills 目录）：

```bash
cp -R short-drama-script short-drama-script-audit ~/.codex/skills/
```

## 标准流程

**新建项目**

```bash
python3 short-drama-script/scripts/init_project.py <项目目录> --title <剧名> --episodes <N>
```

生成目录骨架（`交付/`、`审查/`）、四份支持文档、第一集集头模板；已存在的文件跳过、不覆盖。

**写一集**

先读 `short-drama-script/references/format-spec.md`（格式标准）与
`references/write-checklist.md`（写作自检＋真实事故清单），然后写 `第N集.txt`。
集头块 → 场标题 `【N-M 时间 内／外 场景】` → 场下三件套（人物行／`△` 动作行／对白行）。

**生成派生件（不许手改）**

```bash
python3 short-drama-script/scripts/build_derived_docs.py <项目目录>            # 重建 + 对账
python3 short-drama-script/scripts/build_derived_docs.py <项目目录> --check    # 只体检
```

**审查门禁**

```bash
python3 short-drama-script-audit/scripts/audit_plain_script.py <项目目录>
```

FAIL 不为 0 就不要往下走；审查记录落 `<项目目录>/审查/`，每次审查一个新文件，不覆盖旧记录
（格式见 `short-drama-script-audit/references/review-ledger.md`）。

**交付**

```bash
python3 short-drama-script/scripts/pack_delivery.py <项目目录> --label r1
```

包内显式写 UTF-8 文件名标记（macOS 的 `zip` 默认不打，解压会乱码），写入后逐文件回读比对字节，
输出 SHA-256；同名包不覆盖，自动加序号。

## 仓库结构

```text
short-drama-skills/
|-- README.md
|-- sync.sh
|-- short-drama-script/
|   |-- SKILL.md
|   |-- agents/openai.yaml
|   |-- references/format-spec.md        格式标准（与审查 skill 同源）
|   |-- references/project-layout.md     目录结构与七份文档（同源）
|   |-- references/write-checklist.md    写作自检清单
|   |-- references/derived-docs.md       派生件结构与对账纪律
|   `-- scripts/{init_project,build_derived_docs,pack_delivery}.py
`-- short-drama-script-audit/
    |-- SKILL.md
    |-- references/format-spec.md        同源副本
    |-- references/project-layout.md     同源副本
    |-- references/audit-checklist.md    A 格式／B 连续性／C 接缝／D 台词／E 审查口径／F 项目与交付
    |-- references/review-ledger.md      审查记录规范与状态机
    `-- scripts/audit_plain_script.py    机械校验 ＋ 项目与交付检查
```

## 维护规则

1. **任何改动都要 commit 并 push 到本仓库**——改 SKILL.md、加 references、改脚本都算；
   不要只改本地安装副本。
2. 改完的顺序：改仓库文件 → `./sync.sh` → 跑校验（脚本自测 ＋ 拿一个真项目
   `audit_plain_script.py` 体检）→ commit ＋ push。
3. `format-spec.md`／`project-layout.md` 同源，必须两边一起改。
4. 校验脚本依赖 Python 3 标准库，零外部依赖；skill 结构校验可用
   skill-creator 的 `quick_validate.py`（需要 PyYAML）。

## 首次推送 / 日常推送

```bash
# 首次（已配置好 origin 时跳过前两行）
git remote add origin https://github.com/beautyaiClub/short-drama-skills.git
git branch -M main
git push -u origin main

# 日常
./sync.sh && git add -A && git commit -m "docs: 说明改了什么" && git push
```

注意：走 HTTPS 推送时，**fine-grained PAT 必须勾上 Repository permissions → Contents: Read and write**
（只有 read 权限时 `git ls-remote` 能过、`git push` 会报
`403 … denied`，API 侧报 `Resource not accessible by personal access token`）。
推完不要在 `.git/config` 里留 token：用 `credential.helper` 或 `GIT_ASKPASS` 临时提供即可。
