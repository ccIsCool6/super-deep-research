# Super Deep Research

`Super Deep Research` 是一个面向 Codex、Claude Code、Trae 以及其他主流 Agent 的深度研究 Skill。它的正式名称是 `deep-research-expert-v5`，目标不是让 AI 更快地“搜一搜并总结”，而是让 AI 像一个严谨的研究助理一样，先把问题问清楚，再查证、综合、解释，最后交付一份人真的能读懂、能判断、能复用的研究成果。

这个仓库本质上是一套可迁移的研究方法包。只要你的 Agent 能读取本地文件、遵循 `SKILL.md` 里的说明，并在需要时使用搜索、文件读取和命令行工具，就可以使用它。不同 Agent 的“安装方式”可能不同，但核心用法相同：让 Agent 先读取这个 Skill，再按它的流程完成研究。

它适合用在这些场景：

- 你想系统理解一个领域、行业、人物、技术、理论或争议问题；
- 你要做研究报告、文献综述、决策备忘录、学习材料或知识库；
- 你不满足于“列几个观点”，而是希望 AI 讲清楚机制、证据、边界、反例和适用条件；
- 你有一份或多份长文档，希望 AI 不只是摘重点，而是完整梳理论证结构，并说明哪些部分被覆盖、哪些部分证据不足；
- 你希望输出结果像一个专业人士写给人看的文章，而不是搜索结果、资料摘要和项目符号的堆叠。

它不适合用来做一行事实查询、简单翻译、普通改写，或者任何你明确不希望搜索和核验来源的任务。

## 它解决的核心问题

很多研究型 AI 工具的问题不是“不聪明”，而是太容易直接回答。用户问一个模糊问题，它就立刻开始搜索；搜到一些材料后，就把材料摘要拼起来；最后看起来内容很多，但真正的问题、证据强度、适用边界和结论条件并没有被讲清楚。

`Super Deep Research` 的设计思路相反：它先拦住这个冲动。

在正式研究前，它会先澄清：你到底想解决什么问题，这份结果要给谁看，错误成本有多高，哪些范围要纳入，哪些不做，时间、地区、版本和证据标准是什么。这个过程不是为了拖慢，而是为了防止 AI 在错误的问题上高效产出。

研究开始后，它会要求 AI 把资料转化为证据结构，而不是把资料逐条复述。它会区分事实、来源观点、AI 的综合判断、建议和未知项；会检查关键主张有没有证据支撑；会主动寻找反方解释和边界条件；会把多个来源之间的关系讲出来，说明它们是互相支持、互相冲突、递进补充，还是处在不同层次。

最后成稿时，它追求的是“人类友好”的解释性输出：读者不只是知道结论，还能理解为什么是这个结论，什么时候这个结论会失效，以及如何把这套理解迁移到新问题上。

## 和普通研究型 Skill 的区别

普通研究型 Skill 往往强调检索、摘要和整理。`Super Deep Research` 更强调研究质量的过程控制。

它最重要的区别有四点。

第一，它先澄清问题，再开始研究。很多低质量研究的根源不是资料不够，而是问题本身没定义清楚。这个 Skill 会先确认真实用途、读者、范围、档位和完成标准，避免一上来就跑偏。

第二，它要求解释性综合，而不是摘要拼接。好的研究不是“资料 A 说了什么，资料 B 说了什么”，而是解释 A 和 B 放在一起后，如何改变我们对问题的判断。

第三，它有质量门禁。中等强度以上的任务会被要求经过更严格的证据、覆盖、深度和批判审查。你不需要理解所有内部机制，只要知道它不是单纯靠 AI 自信地写完，而是设计了多道检查来防止伪完整、弱证据和空泛结论。

第四，它默认输出跨平台 Markdown。你可以直接在 GitHub、VS Code、Typora、Obsidian 或其他 Markdown 工具里阅读。Obsidian 是可选增强，不是强制依赖。

## 最大亮点

这个 Skill 最强的地方，不是让答案显得更长，而是让研究成果更像“可以被人使用的知识”。

它会逼 AI 做三件普通回答经常跳过的事：

1. 把问题定义清楚，避免答非所问；
2. 把证据和判断连接起来，避免只堆资料；
3. 把结果写成人能理解、能质疑、能迁移的解释，而不是只给结论。

如果你的目标是“真正搞懂一个复杂问题”，这比单纯追求搜索数量、引用数量或文章长度更重要。

## 最佳使用方式

想让它发挥最好效果，提问时不要只写“帮我研究一下 X”。你可以直接提供下面这些信息，不需要很正式，但越清楚，结果越好：

```text
我想研究的主题：
我真正要解决的问题：
结果要给谁看：
我目前已经知道什么：
我最困惑的地方：
希望重点覆盖哪些范围：
明确不需要覆盖什么：
时间、地区、版本或行业边界：
我希望输出成什么形式：
我能接受的研究深度：轻度 / 中度 / 重度 / 超级重度
```

例如：

```text
$deep-research-expert-v5

我想系统研究 AI Agent 在个人知识管理里的真实价值。
读者是已经用过 Obsidian 和 ChatGPT 的普通知识工作者。
我最困惑的是：Agent 到底解决了什么新问题，哪些只是自动化噱头。
请重点比较信息收集、笔记整理、知识连接、长期复用这几个环节。
不需要泛泛介绍大模型历史。
希望输出一份适合普通人读懂的中文研究报告，最好有结论、证据、边界和实践建议。
研究强度建议你推荐。
```

如果你有 PDF、网页、论文、报告、书籍摘录或已有笔记，也可以一起给它。资料越明确，它越能减少无效搜索，把精力放在解释、核验和综合上。

## 研究强度怎么选

这个 Skill 会根据任务推荐研究强度。你也可以一开始就指定。

| 强度 | 适合场景 | 你可以期待什么 |
|---|---|---|
| 轻度 | 一个边界清楚的问题 | 快速但有证据意识的回答 |
| 中度 | 系统理解一个主题 | 更完整的解释、结构和来源核验 |
| 重度 | 高成本、强争议或复杂决策 | 更严格的证据、反方检查、边界说明和质量门禁 |
| 超级重度 | 领域级、书籍级、知识库级研究 | 尽可能完整地建立认知地图、证据结构和长期可复用成果 |

强度不是简单的字数开关。好的研究不是越长越好，而是该讲清的机制、证据、边界和反例都没有被省略。

## 使用前建议准备

必需：

- Codex、Claude Code、Trae 或其他能读取本地指令文件的主流 Agent；
- 可以联网和读取资料的 AI 代理环境。如果你希望它做实时研究，就要允许它搜索、打开网页或读取你提供的文件；
- Git，用来下载和更新本仓库。

推荐：

- Python 3.9 或更高版本。Skill 自带了一些检查工具，用于确认包结构和研究成果是否满足基本要求；
- Obsidian。如果你喜欢用双链、Callout 和知识库管理，可以把它作为阅读和沉淀研究成果的工具。但它不是必需品，本 Skill 默认使用普通 Markdown。

下载地址：

- Obsidian: https://obsidian.md/download
- Python: https://www.python.org/downloads/
- Git: https://git-scm.com/downloads

## 安装方法

把仓库下载到本地：

```bash
git clone https://github.com/ccIsCool6/super-deep-research.git
```

### Codex

复制到 Codex 的 skills 目录，并保持目录名为 `deep-research-expert-v5`：

```bash
mkdir -p "$HOME/.codex/skills"
cp -R super-deep-research "$HOME/.codex/skills/deep-research-expert-v5"
```

重启 Codex 后，在对话中使用：

```text
$deep-research-expert-v5
```

### Claude Code

Claude Code 不一定使用和 Codex 完全相同的 skills 目录机制。最稳妥的方式是把这个仓库放进你的项目目录或常用工具目录，然后在 Claude Code 里明确要求它读取主说明文件：

```text
请先读取 super-deep-research/SKILL.md，并按 deep-research-expert-v5 的流程执行这次研究。
```

如果你的 Claude Code 工作流支持项目级说明文件，也可以在项目说明里写明：需要深度研究时，优先读取这个仓库的 `SKILL.md`，再按其中的资源路由读取 `references/` 下的必要文件。

### Trae 和其他主流 Agent

如果你使用的是 Trae 或其他本地 Skill 运行环境，把整个仓库文件夹复制到对应的 skills 目录即可。关键是最终文件夹名要叫：

```text
deep-research-expert-v5
```

如果某个 Agent 没有专门的 Skill 安装机制，也可以把仓库作为普通本地文件夹使用。启动研究前，让 Agent 先读取 `SKILL.md`；当它需要更细的研究、证据、写作或审查规则时，再按 `SKILL.md` 指向的路径读取 `references/`、`assets/` 和 `scripts/`。这样做不会得到平台原生的自动路由体验，但仍然能复用这套研究方法。

## 仓库里有什么

你不需要理解所有文件才能使用它。只要知道大致分工即可：

- `SKILL.md` 是 Skill 的主说明，决定它什么时候被调用、如何工作、交付标准是什么；
- `references/` 放的是研究流程、证据标准、写作标准和不同领域的补充规则；
- `assets/` 放的是研究状态、来源记录、证据记录、深度契约和审查记录的模板；
- `scripts/` 放的是检查工具，用来验证包结构和部分研究交付物；
- `tests/` 放的是基础测试，帮助确认这个 Skill 包没有明显损坏。

## 如何确认安装正常

进入仓库根目录，运行：

```bash
python3 scripts/validate_package.py .
python3 -m unittest discover tests
```

在 Windows 上，如果 `python3` 不可用，可以尝试：

```powershell
py -3 scripts\validate_package.py .
py -3 -m unittest discover tests
```

这些检查不能保证每一次研究结果都天然正确，因为事实正确还取决于资料质量、搜索权限和用户给定的边界。但它可以确认这个 Skill 包本身的结构、引用、配置和基础脚本是可运行的。

## 如何检查研究交付物

普通使用者不一定需要手动运行下面这些命令；但如果你要把中度、重度或超级重度研究成果用于重要决策、公开发布、课程、知识库沉淀，建议保留这些检查。

常用 POSIX 命令：

```bash
python3 scripts/scan_readability.py <交付路径>
python3 scripts/validate_deliverable.py <交付路径> --tier <medium|heavy|super-heavy> --profile standard --h1-policy error
python3 scripts/validate_research.py --sources <source-ledger.csv> --claims <claim-evidence-ledger.csv> --tier <medium|heavy|super-heavy>
python3 scripts/validate_coverage.py --ledger <document-coverage.csv> --expected-items <count> --core-question-id <Q1> --central-unit-id <U1> --source-units <S1=total-pages>
python3 scripts/validate_review.py --record <review-record.json> --deliverable <交付路径> --contract <depth-contract.json> --review-type evidence-logic
python3 scripts/validate_depth.py --contract <depth-contract.json> --deliverable <交付路径> --tier <medium|heavy|super-heavy>
```

Windows 上可以优先把 `python3` 替换为 `py -3`。这些命令的作用不是替你判断所有事实是否正确，而是检查结构、覆盖、台账和深度门禁是否出现明显缺口。

## 关于“万无一失”

没有任何研究工具可以承诺 100% 万无一失。真正可靠的研究不是靠一句保证，而是靠清晰的问题、可追溯的证据、边界说明、反方检查和交付前的质量门禁。

`Super Deep Research` 的价值正在这里：它不是假装 AI 永远正确，而是尽量把 AI 容易出错的地方提前暴露出来，并要求 AI 在结论里说明证据从哪里来、哪些地方仍不确定、什么条件会改变判断。

## License

MIT
