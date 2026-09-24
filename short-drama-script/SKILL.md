---
name: short-drama-script
description: 写“纯剧本格式（场次本）”的短剧／漫剧剧本，并维护项目骨架与支持文档（全局设定、整体大纲、台词对照本、分集场次表、交付包）。用户要新建短剧项目、写或改某一集、把旧格式整改成场次本、补支持文档、或把剧本打进交付包时使用。只管剧本文本与项目结构，不产出分镜、图片、视频、配音。
metadata:
  short-description: 短剧场次本写作与项目标准
---

# 短剧场次本写作与项目标准

目标格式是**纯剧本格式（场次本）**：剧本只管戏，一场＝一个连续时空；
镜号、景别参数、机位、焦段、每场时长那一层全部交给分镜系统。
格式定义见 [references/format-spec.md](references/format-spec.md)——写任何一集之前先按它对齐。

写作与审查是两个工作单元：**写作轮**产出与修改正本及派生件；**审查轮**交给
`$short-drama-script-audit`。写手不给自己签字。

## 一、先把项目建对

完整目录树、七份文档的职责与命名、别名规则，见
[references/project-layout.md](references/project-layout.md)。要点：

```text
<项目目录>/
|-- 第N集.txt                      正本：一集一文件，纯剧本格式
|-- <剧名>-全局设定.txt             画风／光色／格式规范／世界观／资产命名表／人物／场景／物品／出图提示词
|-- <剧名>-第一季整体大纲.txt        故事引擎／人物弧线／分集地图／集间衔接硬规则／逐日锚点
|-- <剧名>-台词对照本.txt           逐条英文＋中文大意（对账与配音用）
|-- <剧名>-分集场次表.txt           一行一场：排期与资产分派用
|-- 交付/                          打包 zip 与 PDF 的落点
|-- 审查/                          所有审查记录（第 N 轮、机械校验 json）
`-- 备份-<节点>-<YYYYMMDD>/        改稿前快照（改稿前先拷一份）
```

## 二、工作流

1. **新建项目**

   `python3 scripts/init_project.py <项目目录> --title <剧名> --episodes <N>`

   生成目录骨架 ＋ 四份支持文档 ＋ 第一集集头模板。已存在的文件一律跳过、不覆盖。

2. **写一集**：读 [references/format-spec.md](references/format-spec.md) 与
   [references/write-checklist.md](references/write-checklist.md)，然后写 `第N集.txt`。
   写之前先把这一集的数值／道具／伤情／时间账对齐整体大纲。

3. **生成派生件**（不许手写、不许手改）

   `python3 scripts/build_derived_docs.py <项目目录>`　重建分集场次表＋对账台词对照本

   `python3 scripts/build_derived_docs.py <项目目录> --check`　只报差异，不动文件

   台词对照本的中文由已有稿保留、新句补齐；脚本会列出缺中文的条目。

4. **自查门禁**：跑 `$short-drama-script-audit` 的
   `scripts/audit_plain_script.py <项目目录>`。FAIL 不为 0 不要往下走。

5. **交审查**：审查记录落 `审查/`，按 `$short-drama-script-audit` 的
   `references/review-ledger.md` 写。

6. **交付**：`python3 scripts/pack_delivery.py <项目目录> --label r1`

   包内结构、UTF-8 文件名、逐文件字节校验、SHA-256 由脚本负责；已存在的同名包不覆盖，自动加序号。

## 三、写作硬约束

下面几条直接决定返工量，其余见 format-spec。

1. 场标题只允许 `【N-M 时间 内／外 场景】`；时间只用 `日／昏／夜／晨` 四个词；
   切空间就换场号。**一场＝一个连续时空**：时间从夜走到晨、或中途换了地点，都要拆成两场。
2. 同一母场景必须带子视图（`山谷营地·水塔下`）。只写母场景名，等于让分镜把同一套景重复生成几十次。
3. 人物行只写资产命名表里的英文人名，或已登记的群像。不写中文注释、不写分号；载具不是人，不进人物行。
4. 说明文字（概要、大场面、动作行、语气提示）不出现“他／她”，一律用人名——分镜与人物识别靠名字。
5. 场外人声（无线电／喇叭／画外／远处传来）标 `[VO]`；漏标会让配音按现场口型处理。
6. 台词是目标语言原句、人名保持英文；动作、语气提示、概要保持中文。一个项目只允许一种台词语种。
7. 画面里不出现任何可读文字（旗号只用图形，不做字幕与水印）。
8. 一集按 10–12 分钟写；场数与台词量按这一集的冲突规模定，不为凑时长写水戏。

## 四、三件事不许手改

`分集场次表`、`台词对照本`、`交付包` 一律由脚本生成。改了正本就必须重跑
`build_derived_docs.py`；派生件与正本脱钩是这套流程里最常见的翻车点，
审查脚本会按“条数＋正文”逐条对账。

## 五、与其它 skill 的关系

- 审查：`$short-drama-script-audit`——同一份格式标准的另一端。
- 本 skill 的 `references/format-spec.md`、`references/project-layout.md` 与审查 skill 里的
  同名文件是**同源副本**，文件头有「同步源」行；改一处必须同步另一处，审查脚本会做 hash 比对。
- 分镜、关键帧、图片、视频、配音、音乐不归本 skill。

## 六、维护（改完必须推仓库）

本 skill 与 `$short-drama-script-audit` 同属仓库 `beautyaiClub/short-drama-skills`（GitHub）。
**任何改动——改 SKILL.md、加 references、改脚本——都要 commit 并 push 到该仓库**，
不要只改本地安装副本。仓库根目录有 `sync.sh`，用来在「仓库」与 `~/.codex/skills` 之间对齐：

```bash
./sync.sh              # 仓库 → ~/.codex/skills（装最新版）
./sync.sh --check      # 只比对差异，不动文件
```

改完的固定顺序：改仓库里的文件 → `./sync.sh` → 跑校验（脚本自测 ＋ 真项目体检）→ commit ＋ push。
