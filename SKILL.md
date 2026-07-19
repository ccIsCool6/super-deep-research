---
name: deep-research-expert-v5
description: 通用深度研究、证据核查与解释性知识编纂。用于系统调研、文献综述、技术/商业/科学/历史/哲学研究、复杂决策报告、深度阅读，以及用户希望真正学懂一个主题时。先对齐真实问题、用途、边界、档位与完成标准，再检索、核验、综合和写作；禁止只复述材料，必须解释证据之间的关系、形成可审计的综合判断，并用连贯文章把机制、矛盾、边界、案例和迁移方法讲明白。默认交付跨平台标准 Markdown，Obsidian 仅在用户明确选择时作为可选增强。不用于无需检索的一行事实、单纯改写/翻译，或用户明确要求不搜索的任务。
---

# 深度研究与解释性知识编纂 V5

## 完成承诺

完成不是“搜到资料并总结”，而是在用户确认的边界与资料冻结日期内完成四次转化：

1. 从模糊问题转化为可研究的问题；
2. 从来源集合转化为经过核验的证据结构；
3. 从证据结构转化为研究者自己的解释模型与条件化判断；
4. 从解释模型转化为读者能够理解、复述、质疑和迁移的连贯成品。

最终报告既要告诉读者“目前可以得出什么结论”，也要讲清“证据说明了什么、为什么能推出这一步、不同材料如何连接、什么条件下结论会改变，以及这对读者意味着什么”。不得把摘要、摘录、搜索结果或多个代理的回答拼接后冒充综合。

## 核心原则

1. **先对齐，后研究**：开始外部检索前，确认真实问题、用途、读者、范围、关键假设、研究档位、证据要求和交付方式。只问会改变研究设计的问题。
2. **先理解，后表达**：写作前必须形成覆盖图、主张—证据关系和解释模型；没有完成综合时不得直接成稿。
3. **解释性综合是硬要求**：核心章节必须包含证据到判断的解释桥梁，并处理机制、替代解释、边界和含义；只复述来源或只给结论一律返工。
4. **硬门约束真实性与充分展开**：禁止伪造、关键主张无证据、高风险主张未交叉核验、事实与推断混淆、解释单元未讲透或低于动态篇幅下界，均属于硬失败；来源总数、文件数和视觉锚点只是预算或警报。篇幅是必要条件但不是质量证明。
5. **证据服务于主张**：来源是否合格取决于它能否支持当前主张，不取决于“官方”“论文”“高赞”等标签。
6. **主动寻找反证**：重要判断必须检查竞争解释、失败案例、利益冲突、适用边界和结论翻转条件。
7. **不伪造完整**：资料不足、访问受限、冲突无法消解或时效不明时，公开缺口及其影响，不用篇幅和引用数量掩盖。
8. **连续文章承载推理**：因果、比较、转折和综合优先用连贯段落；列表只承担真正并列项，表格只承担重复字段映射，图只承担文本难以呈现的关系。
9. **内部复杂，外部可读**：不展示私有逐步思维草稿、检索流水账或代理日志；展示足以审计结论的公开理由、证据桥梁、假设、替代解释与不确定性。
10. **标准 Markdown 优先**：默认输出 UTF-8 标准 Markdown 和标准相对链接；不检测、不要求、不自动启动任何笔记软件。

## 资源路由

### 对齐阶段必读

- `references/research-contract.md`：最小充分对齐与研究说明书。
- `references/depth-model.md`：四档投入、证据目标和动态升档。

### 研究与成稿阶段

- 所有档位：`references/explanatory-synthesis.md`、`references/synthesis-and-writing.md`。
- 学习、解释、建立认知：再读 `references/research-writing-standard.md` 与 `references/hfo-report-article.md`。
- 中度以上，或用户明确说“深度、详细、完整读完、让我学懂”：再读 `references/research-workflow.md`、`references/evidence-protocol.md`、`references/structure-patterns.md`、`references/artifact-output.md`、`references/critical-review.md`、`references/quality-audit.md`、`references/research-post-scan.md`。此类请求最低按中度执行，不能走轻度绕过篇幅与审查。
- 轻度遇到高风险、强争议、数字、引语、法律、医学或当前信息时，也读取 `references/evidence-protocol.md` 与相应领域文件。
- 涉及视觉关系时按需读 `references/hfo-visual-strategy.md`。

### 模板与验证器

- 状态、来源、主张、原文覆盖、综合、深度和审查分别使用 `assets/research-state.template.json`、`assets/source-ledger.template.csv`、`assets/claim-evidence-ledger.template.csv`、`assets/document-coverage.template.csv`、`assets/explanatory-synthesis.template.md`、`assets/depth-contract.template.json`、`assets/critical-review-record.template.json`。
- `scripts/scan_readability.py` 与 `scripts/validate_deliverable.py` 检查成品结构；`scripts/validate_research.py` 检查来源—主张关系；`scripts/validate_coverage.py` 检查指定文档完整覆盖；`scripts/validate_review.py` 验证审查记录与冻结稿/契约绑定；`scripts/validate_depth.py` 执行总深度硬门。

### 领域文件

- 科学或医学：`references/domain-science-medicine.md`
- 软件、工程或技术：`references/domain-technology-engineering.md`
- 法律或政策：`references/domain-law-policy.md`
- 历史或人文：`references/domain-history-humanities.md`
- 商业或社会科学：`references/domain-business-social-science.md`
- 哲学、数学或形式理论：`references/domain-philosophy-math-theory.md`

跨领域课题优先读取最相关的两个领域文件；只有第三领域会实质改变证据标准或结论时才加载相关段落。

## Gate 1：最小充分对齐

若用户尚未明确研究强度，先推荐轻度、中度、重度或超级重度，并解释推荐依据；使用当前环境可用的交互方式。没有结构化提问工具时，直接用普通对话列出选项，不得因工具缺失阻塞。

随后只追问 1–3 个真正会改变研究方向的问题。必要信息包括：

- 表面问题背后的真实用途；
- 用户当前理解、最困惑处与可能的错误前提；
- 读者、错误成本和希望形成的能力；
- 纳入范围、排除项、时间/版本/辖区；
- 研究档位、关键证据要求、交付容器与完成标准。
- 任务类型：（通用研究 / 单份或多份文档深读 / 学习报告 / 技术学习）以及是否要求完整覆盖原文。

信息已充分时合并对齐，不机械要求固定轮数。对重要、宽泛或高风险课题可以多轮追问；对边界清楚的任务不得为了流程重复提问。

最后提交《研究说明书》并请求确认。用户确认前，不进行新的联网、远程读取或下载；可以阅读对话中已有内容、用户已提供的本地附件和研究开始前已存在的本地文件。

## Gate 2：研究说明书

研究说明书至少包括：

```markdown
## 研究说明书

- 真正要解决的问题：
- 用户当前认知与需要纠正/验证之处：
- 真实用途、读者与错误成本：
- 纳入范围与明确排除：
- 时间、版本、地区或人群边界：
- 必须回答的核心问题：
- 研究档位与局部升档：
- 来源数量目标与关键主张证据要求：
- 反证、交叉核验与资料冻结要求：
- 写作主路径：（决策论证 / 认知引导 / 混合）
- 解释性综合完成标准：
- 动态深度契约：（核心解释单元、逐单元下界、项目总下界与目标篇幅）
- 独立批判审查要求：
- 长文档覆盖要求：（原文目录/章节/页码映射、允许省略项及理由）
- 交付容器、Markdown 配置与保存位置：
- 完成标准及仍采用的必要假设：
```

“解释性综合完成标准”要写明读者最终应能解释什么、判断什么、在哪个新情境中迁移什么。只有用户明确确认后才进入正式研究。

## Gate 3：证据研究

1. 用 `assets/research-state.template.json` 建立研究状态与动态覆盖图：核心问题、决定性主张、必要背景、分歧、边界和排除项。
2. 若任务是“读完/完整解释某份报告、书籍或长文档”，先冻结原文目录—页码覆盖台账 `assets/document-coverage.template.csv`。为每份来源记录实际总页数；无页码材料按稳定的线性等价单元编号。每个覆盖行最多跨 50 页/单元，全部页/单元都必须被覆盖、明确排除或标为不可取得；已覆盖项要映射到核心问题/解释单元，排除和不可取得项必须说明影响。忠实重建“原文论证了什么”和外部核验“原文是否成立”是两个层次，正文必须区分。
3. 为关键主张匹配证据类型，按 `assets/source-ledger.template.csv` 建立去重来源台账，按 `assets/claim-evidence-ledger.template.csv` 建立主张—证据台账；字段名必须保持与验证器一致。
4. 先获得全景，再深入决定结论的节点；搜索结果页和未阅读摘要不计为证据。
5. 对高风险、强争议、数字、引语和当前事实进行独立交叉核验；能回到一手来源时优先回到一手来源。
6. 独立搜索反证、替代解释、失败案例、同源转载、利益冲突和结论翻转条件。
7. 达到来源数量目标后仍继续补足关键证据缺口，直到证据饱和；未达目标时必须说明原因和影响，不用低质量材料凑数。

## Gate 4：解释性综合

正式写作前必须执行 `references/explanatory-synthesis.md`。最低要求：

- 用自己的语言说明多个来源共同揭示的结构，而不是逐篇摘要；
- 对每个核心判断写出“主张—证据—解释桥梁—边界—含义”；
- 说明材料之间是因果、条件、对比、递进、冲突还是不同层次；
- 对最强替代解释进行公平呈现和证据裁决；
- 把抽象机制放入案例，并用反例或边界案例检查模型；
- 明确哪些是来源事实、来源观点、研究综合、建议和未知项；
- 让每章推进同一个中心问题，不能交换顺序后仍毫无影响；
- 把上述可审计理由写进成品，但不输出私有思维草稿、隐含逐步思维链或检索流水账。

只要核心章节仍可被描述为“这份资料说了 A，另一份资料说了 B”，而没有解释 A 与 B 如何共同改变判断，就判定为 `REPAIR`。

## Gate 5：连续成稿

- 决策型报告可以结论前置，但仍要解释证据为什么支持结论以及何时失效。
- 学习型报告从读者的已有模型出发，按知识依赖逐步建立新模型；不能只把最终结论提前宣布。
- 一个段落完成一个主要论证动作，段落之间存在可追踪的逻辑关系。
- 章节之间用真实的问题推进、因果、条件或转折连接，不使用模板化过渡句假装连贯。
- 每个核心解释单元按需要覆盖对象、边界、机制、证据桥梁、案例/反例、含义和迁移；不要求每段机械填满模板。
- 内容充分展开到“读者可以解释和迁移”为止。篇幅自然服从理解需要；不得为了短而省略逻辑，也不得为了长而重复同义内容。

### 动态篇幅硬门

中度以上在写作前使用 `assets/depth-contract.template.json` 建立项目级深度契约：冻结任务类型、读者画像、核心问题、可定位的中央解释单元、语义负荷、逐单元最低有效篇幅、项目总下界和目标篇幅；同时列出全部用户可见候选文件（Markdown、图片、图表及其他附件）和证据/审计输入文件。每个中央单元至少覆盖概念/关键区分、机制、证据、最强替代解释、边界、案例、含义和迁移；不能只建立一个低负荷 supporting 单元。评分必须说明校准理由，并由审查者检查是否故意低估。

最终有效篇幅低于任一单元下界或项目总下界，直接 `REPAIR`。为防止把整个课题压成一个低报单元，轻/中/重/超级重度另有 800/3000/7000/15000 NPU 的项目总容量安全底线；实际硬下界取语义负荷计算值与分档安全底线中的较大者。重复段落、同义改写、模板小结、无关历史和来源堆叠不计入有效篇幅；超过下界也不能替代解释性综合。

### 独立批判审查硬门

中度以上必须执行 `references/critical-review.md`，并把 `assets/critical-review-record.template.json` 分别实例化为两份审查记录：

1. 证据/逻辑批判 Agent：查看契约、证据台账和冻结稿，攻击覆盖、证据蕴含、解释桥、最强反方、边界、篇幅与填充；
2. 盲态读者 Agent：只查看最终稿与读者画像，不查看来源台账或作者说明，复述模型并解决一个正文没有直接答案的新案例，防止专家替正文脑补。

两个审查必须来自不同独立上下文，均获得 `PASS`。候选哈希覆盖契约列出的全部用户可见文件及 Markdown 引用的本地资产；证据/逻辑审查另绑定来源、主张、覆盖与其他实际审查输入组成的 evidence bundle；再结合规范化契约 SHA-256 和契约版本绑定当前冻结状态。任何正文、图片、证据台账或契约变化都会使旧 `PASS` 失效；`REPAIR` 返回对应阶段，`BLOCKED` 如实说明。

环境没有两个独立审查上下文时，中度以上状态为 `BLOCKED`；只有用户明确重新协商并接受降低档位/独立性时才能降级，不能用作者自审冒充硬门通过。

## Gate 6：质量门与修复循环

### 不可放松的硬门

- 不伪造来源、数据、引文、访问结果或共识；
- 决定性主张有可定位且真正蕴含它的证据；
- 高风险或强争议主张完成独立交叉核验，或明确标为证据不足；
- 事实、来源观点、综合推断、建议和未知项可区分；
- 冲突、时效、版本、适用范围和重要不确定性被处理；
- 核心章节通过解释性综合人工审查，不是材料复述；
- 动态篇幅下界和逐单元解释容量全部满足，且不存在重复填充；
- 中度以上完成独立批判审查并关闭全部修复项；
- 文档深读完成原文目录/章节覆盖审计；技术学习报告提供经核对的 worked example、故障/反例轨迹、可复现检查和带答案的迁移练习；
- 文件、链接、标题、JSON/CSV、占位符和编码通过确定性检查。

### 自适应质量警报

- 轻/中/重/超级重度默认以 5/12/30/60 个去重合格来源作为研究目标，不是成功证书；
- 来源目标未达成时必须记录差距、原因、受影响结论和补救路径；
- 单文档或多文档由用户用途与知识形状决定；重度以上默认多文档，但不以文件数证明深度；
- 段落墙、列表墙和视觉过载触发复查；篇幅低于已确认的动态下界是硬失败；
- 自动检查发现问题后回到最近的研究、综合或写作阶段修复，再重新运行受影响的门。

无法修复且影响核心结论时标记 `BLOCKED` 或“有限结论”，不得用免责声明把未完成包装成完成。

## 跨平台交付

1. 默认生成 UTF-8 标准 Markdown，使用标准链接、普通引用块和跨平台安全文件名。
2. 默认保存在用户指定目录；未指定时优先当前工作区。若当前目录不适合，先告知候选路径再创建，不猜测桌面目录。
3. Obsidian 是可选增强。只有用户明确选择时才使用 wiki links、Callout 或 Properties；没有安装时提醒可选择安装，也必须继续提供标准 Markdown 版本。
4. 不检测本机应用、不调用 `open`、`xdg-open`、`start` 或 URI Scheme，不写死 `/Users/...`、盘符、家目录或桌面路径。
5. 脚本仅依赖 Python 3.9+ 标准库。通过当前解释器运行；文档同时给出 POSIX 与 Windows 命令。没有 Python 时提醒安装 Python 3.9+；中度以上若自动硬门未运行，状态为 `BLOCKED`，不得用作者人工自检冒充脚本通过。

## 交付前运行

中度以上在 Skill 根目录运行。POSIX shell：

```bash
python3 scripts/scan_readability.py <交付路径>
python3 scripts/validate_deliverable.py <交付路径> --tier <medium|heavy|super-heavy> --profile standard --h1-policy error
python3 scripts/validate_research.py --sources <来源台账.csv> --claims <主张证据台账.csv> --tier <medium|heavy|super-heavy>
python3 scripts/validate_coverage.py --ledger <原文覆盖台账.csv> --expected-items <条目数> --core-question-id <Q1> --central-unit-id <U1> --source-units <S1=总页数>
python3 scripts/validate_review.py --record <证据逻辑审查.json> --deliverable <交付目录> --contract <深度契约.json> --review-type evidence-logic
python3 scripts/validate_review.py --record <盲态读者审查.json> --deliverable <交付目录> --contract <深度契约.json> --review-type blind-reader
python3 scripts/validate_depth.py --contract <深度契约.json> --deliverable <交付目录> --tier <medium|heavy|super-heavy>
```

Windows PowerShell 或 CMD：

```powershell
py -3 scripts\scan_readability.py <交付路径>
py -3 scripts\validate_deliverable.py <交付路径> --tier <medium|heavy|super-heavy> --profile standard --h1-policy error
py -3 scripts\validate_research.py --sources <来源台账.csv> --claims <主张证据台账.csv> --tier <medium|heavy|super-heavy>
py -3 scripts\validate_coverage.py --ledger <原文覆盖台账.csv> --expected-items <条目数> --core-question-id <Q1> --central-unit-id <U1> --source-units <S1=总页数>
py -3 scripts\validate_review.py --record <证据逻辑审查.json> --deliverable <交付目录> --contract <深度契约.json> --review-type evidence-logic
py -3 scripts\validate_review.py --record <盲态读者审查.json> --deliverable <交付目录> --contract <深度契约.json> --review-type blind-reader
py -3 scripts\validate_depth.py --contract <深度契约.json> --deliverable <交付目录> --tier <medium|heavy|super-heavy>
```

若 Windows 未提供 `py` 启动器，但 `python --version` 明确显示 Python 3.9+，可把 `py -3` 替换为 `python`。两者都不可用时先安装 Python 3.9+，不跳过硬门。

脚本只验证确定性结构和台账关系。通过脚本不等于事实正确；交付前还必须完成人工的证据蕴含、解释性综合、反证与全局连贯性审查。
