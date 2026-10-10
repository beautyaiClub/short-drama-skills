# 安装与上手指南

这套 skill 用来写**短剧／漫剧剧本**，从立项一路做到可交付的剧本包。
仓库里是**源**，`~/.codex/skills/` 是 Codex 实际读取的安装副本。

---

## 一、装什么

| skill | 作用 | 命令入口（在项目目录里跑） |
|---|---|---|
| `short-drama` | 创建台：初始化项目、项目配置、本地 Dashboard；**制作形态与 Look Development 决策** | `python3 <skill>/scripts/project_tool.py` |
| `short-drama-develop` | 开发层：创作简报、故事引擎、分集地图、题材卡 | `python3 <skill>/scripts/episode_intake.py` |
| `short-drama-script` | **写剧本**：正本、全局设定、大纲、台词对照本、分集场次表、派生件、交付包 | `build_derived_docs.py` / `estimate_duration.py` / `pack_delivery.py` / `init_project.py` |
| `short-drama-script-audit` | **审剧本**：机械校验、连续性、接缝、台词、项目与交付层 | `python3 <skill>/scripts/audit_plain_script.py <项目目录>` |
| `short-drama-review` | 内容层复核：故事剧本 rubric、证据化 finding、结论分级 | `python3 <skill>/scripts/review_check.py` |

**最低配置**：只想写某一集 → 装 `short-drama-script` ＋ `short-drama-script-audit`。
**完整配置**：上面五个。

### 格式选择（重要，先看这一条）

本仓库只采用**一种**剧本格式：**场次本**——一集一个 `第N集.txt`，
场标题 `【N-1 日 内 母场景·子视图】`，只有人物行／`△`／`▲`／对白四类行，
不写镜号与 `[转场]` 之类的标签。门禁、派生件、交付包、PDF 全部建立在这套格式上。

创建台与开发层里保留了另一条**可选的 Markdown 方言线**（`$short-drama-write` → `剧集/<EP>/剧本.md`，
带 `[SFX]`／`[转场]` 等生产标签）。**那条线没有随本仓库分发**，而且与场次本**互不通用**——
门禁脚本只认 `第N集.txt`。所以：

- 要用本仓库的门禁与派生件 → 一律走 `$short-drama-script`；
- 同一部剧里不要混用两种格式。

---

## 二、前置条件

- 一台装了 **Codex**（桌面 App 或 CLI）的机器；skill 放在 `~/.codex/skills/` 下即被读取。
- Python 3.9+（脚本只用标准库，无第三方依赖）。

---

## 三、安装

### 方式 A：脚本安装（推荐）

```bash
git clone https://github.com/beautyaiClub/short-drama-skills.git
cd short-drama-skills
./sync.sh              # 仓库 → ~/.codex/skills（装全部 5 个）
./sync.sh --check      # 只比对差异，不动文件
```

### 方式 B：手动安装

```bash
git clone https://github.com/beautyaiClub/short-drama-skills.git
cp -R short-drama-skills/short-drama \
      short-drama-skills/short-drama-develop \
      short-drama-skills/short-drama-script \
      short-drama-skills/short-drama-script-audit \
      short-drama-skills/short-drama-review \
      ~/.codex/skills/
```

### 装完自检

```bash
ls ~/.codex/skills | grep short-drama        # 应看到 5 个
python3 ~/.codex/skills/short-drama/scripts/selftest.py
python3 ~/.codex/skills/short-drama-develop/scripts/selftest.py
python3 ~/.codex/skills/short-drama-review/scripts/selftest.py
```

三个 selftest 全过（17＋5＋8 项），说明安装完整。

---

## 四、五分钟上手：从零跑一部剧

```bash
# 0. 建项目目录（例：我的剧）
mkdir -p ~/Documents/我的剧 && cd ~/Documents/我的剧

# 1. 创建台：初始化骨架（配置、目录、模板）——由 short-drama 负责
#    在 Codex 里说：「用 short-drama 新建项目《我的剧》，60 集 × 90 秒，竖屏 9:16」

# 2. 开发层：把点子落成创作简报／故事引擎／分集地图——short-drama-develop
#    在 Codex 里说：「用 short-drama-develop 做改编方案与分集地图」

# 3. 写剧本：一集一个文件（第一集.txt、第二集.txt…）——short-drama-script
#    在 Codex 里说：「用 short-drama-script 写第三集」，写完它会自检格式

# 4. 跑门禁（FAIL 必须为 0）
python3 ~/.codex/skills/short-drama-script-audit/scripts/audit_plain_script.py .

# 5. 重建派生件（场次表＋台词对照本，不许手写）
python3 ~/.codex/skills/short-drama-script/scripts/build_derived_docs.py .

# 6. 时长自查（按《全局设定》声明的成片规格反推篇幅）
python3 ~/.codex/skills/short-drama-script/scripts/estimate_duration.py 第三集.txt --spec 90

# 7. 交内容审查：每两集一次——short-drama-script-audit / short-drama-review
#    在 Codex 里说：「用 short-drama-script-audit 审第 3–4 集」

# 8. 打包交付
python3 ~/.codex/skills/short-drama-script/scripts/pack_delivery.py . --label r1
```

**铁律三条**：

1. **写手不给自己签字**——写完必须交给审查 skill 出一份审查记录，落在 `审查/`。
2. **派生件不许手改**——`分集场次表`／`台词对照本` 由脚本生成；改了正本就重跑 `build_derived_docs.py`。
3. **门禁 FAIL 不为 0 不要往下走**——先修，再写下一集。

---

## 五、只写某一集（最小流程）

```bash
cd <已有的项目目录>
# 1) 先读这一集要动的账：境界／道具／伤害／时间（看《逐集规格》或《整体大纲》）
# 2) 写 第N集.txt（一集一场、场标题带子视图、每句台词带语气提示）
python3 ~/.codex/skills/short-drama-script/scripts/build_derived_docs.py .
python3 ~/.codex/skills/short-drama-script-audit/scripts/audit_plain_script.py .
```

写之前必读两份：

- `short-drama-script/references/format-spec.md`——格式标准（怎么排场、怎么写人物行、标点怎么用）
- `short-drama-script/references/write-checklist.md`——写作自检清单（左栏是别人踩过的坑）

---

## 六、项目里会有什么（以《黑戒》为例）

```text
我的剧/
|-- 第一集.txt … 第七十二集.txt      正本（一集一文件）
|-- 我的剧-全局设定.txt               画风／格式规范／资产命名表（S 场景／CH 人物／PR 道具）
|-- 我的剧-第一季整体大纲.txt         故事引擎／人物弧线／分集地图／集间衔接
|-- 我的剧-人物总表.txt               人物唯一入口（A 级有弧线／B 级功能位／C 级群像）
|-- 我的剧-台词对照本.txt             派生件（脚本生成）
|-- 我的剧-分集场次表.txt             派生件（脚本生成）
|-- 我的剧-发声标签.txt               开口的无名角色（工人甲／护士乙…）
|-- 项目开发/                         创作简报、故事引擎、形态卡、决策记录
|-- 审查/                             每一轮的审查记录（不覆盖）
|-- 交付/                             交付包 zip、PDF、旧版本/
`-- 旧稿-…/  归档-…/                  历史稿与废弃稿（不当正本参考）
```

交付物通常三样：**交付包 zip**（全项目）、**全剧本 PDF**、**中文字幕稿 PDF**；
按需再加**剧情通读本 PDF**（小说体，给制作团队通读）。

---

## 七、不装 skill 也能写：给外包写手的「最小包」

如果对方只是代写剧本，不必让他装整套。给他四样就够开工：

1. `short-drama-script/references/format-spec.md`——格式标准（可另存成「格式速查一页纸」）
2. `short-drama-script/references/write-checklist.md`——写作自检清单
3. **一个已完成的项目当范例**（连 `审查/` 记录一起给，让他照着格式与密度填）
4. 门禁命令：`python3 ~/.codex/skills/short-drama-script-audit/scripts/audit_plain_script.py <项目>`

验收标准一句话：**门禁 `FAIL 0`，且每一集正文落在声明规格反推的字数区间内。**

---

## 八、常见问题

**Q：门禁报 FAIL 怎么办？**
按报错信息逐条改；`FAIL` 分格式（场标题／说话人／旧格式字段／派生件脱钩）与项目层（支持文档缺失）两类。
`WARN` 不阻断，但要在审查记录里逐条裁定（接受／改）。

**Q：创建台说写 `剧本.md`，你们却说 `第N集.txt`，听谁的？**
听本仓库的：`第N集.txt`（场次本）。创建台与开发层里那句是指另一条 Markdown 方言线，未随仓库分发，
且格式与门禁不兼容。这条已在 INSTALL 的「格式选择」与两个 skill 的路由行里写明。

**Q：能改 `分集场次表`／`台词对照本` 吗？**
不能。它们是派生件，脚本按正本重建；手改会在下一次门禁里被判「与正本脱钩」。

**Q：`format-spec.md` 在两个 skill 里各有一份？**
是**逐字节同源副本**：改一处必须改两处。审查脚本会做 hash 比对，漂移会报出来。

**Q：一集要写多长？**
先在《全局设定》里写一行 `成片规格：单集 90 秒`，脚本按 `秒 ≈ 15 + 0.077×正文字数` 反推目标区间。
90 秒 ≈ 正文 915–1032 字。**偏短补 `▲` 可演动作（加台词只按半价计入），偏长先砍动作。**

**Q：夜戏有上限吗？**
全季夜戏不超过 30–35%（按项目口径写进《全局设定》）；夜戏必须点明实体光源（火／灯／月／车灯）。

**Q：人物称呼要统一吗？**
以《全局设定》的资产命名表为准，全剧不许出现第二套叫法（人名、场景子视图、道具名都是）。

---

## 九、维护（改 skill 之后）

```bash
cd short-drama-skills
# 改仓库里的文件（不要直接改 ~/.codex/skills）
./sync.sh                 # 仓库 → 安装副本
./sync.sh --check         # 确认两处一致
python3 short-drama-script-audit/scripts/audit_plain_script.py <一个真项目>   # 回归
git add -A && git commit -m "..." && git push
```

误改了安装副本时，用 `./sync.sh --pull` 把安装目录的改动收回仓库。
