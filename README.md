# Super Deep Research

This repository packages the `deep-research-expert-v5` skill: a rigorous research, evidence-checking, explanatory synthesis, and long-form knowledge compilation workflow for Codex/Trae-style local skill environments.

The skill is built for research tasks where a shallow answer is not enough. It forces the agent to align the real question, use case, boundaries, evidence standard, depth tier, and completion criteria before doing external research. It then requires evidence-constrained synthesis, critical review, dynamic depth checks, and validation scripts for medium-or-heavier deliverables.

## What This Skill Is For

Use it when you want to:

- deeply understand a field or topic;
- produce a research report, literature review, or decision memo;
- analyze technical, business, scientific, historical, philosophical, legal, or policy questions;
- read and explain long documents while tracking source coverage;
- convert scattered sources into a coherent learning path or knowledge base;
- force the agent to explain mechanisms, contradictions, boundaries, cases, counterarguments, and transfer methods.

Do not use it for one-line facts, simple rewriting, translation, or tasks where you explicitly do not want searching or source checking.

## Repository Layout

```text
deep-research-expert-v5/
├── SKILL.md
├── agents/
│   └── openai.yaml
├── assets/
│   ├── claim-evidence-ledger.template.csv
│   ├── critical-review-record.template.json
│   ├── depth-contract.template.json
│   ├── document-coverage.template.csv
│   ├── explanatory-synthesis.template.md
│   ├── research-state.template.json
│   └── source-ledger.template.csv
├── references/
│   ├── critical-review.md
│   ├── explanatory-synthesis.md
│   ├── research-contract.md
│   ├── depth-model.md
│   ├── evidence-protocol.md
│   └── ...
├── scripts/
│   ├── validate_coverage.py
│   ├── validate_deliverable.py
│   ├── validate_depth.py
│   ├── validate_package.py
│   ├── validate_research.py
│   └── validate_review.py
└── tests/
    └── test_*.py
```

## Install

### Codex

Clone the repository and copy it into your local Codex skills directory under the skill name:

```bash
git clone https://github.com/ccIsCool6/super-deep-research.git
mkdir -p "$HOME/.codex/skills"
cp -R super-deep-research "$HOME/.codex/skills/deep-research-expert-v5"
```

Restart Codex. Then invoke:

```text
$deep-research-expert-v5
```

### Trae Or Other Local Skill Runtimes

Copy the repository folder into the runtime's skills folder and keep the root folder name as:

```text
deep-research-expert-v5
```

The folder name matters because `SKILL.md` declares `name: deep-research-expert-v5`, and the package validator checks that the folder name matches the skill name.

## Recommended Downloads

Install these before serious use:

- **Codex, Trae, or another local skill runtime**: required to load `SKILL.md` and route the reference files.
- **Python 3.9+**: required by the validation scripts. Python 3.10+ is recommended.
- **Git**: recommended for cloning, versioning research outputs, and updating the skill.
- **Obsidian**: optional. This V5 skill defaults to cross-platform standard Markdown and does not require Obsidian. If a user explicitly chooses Obsidian-native output, it can use Obsidian-style links/callouts/properties as an enhancement.
- **A web-enabled agent environment**: required for live research. The skill defines the method; the agent still needs permission and tools to browse or fetch sources.

Useful links:

- Obsidian: https://obsidian.md/download
- Python: https://www.python.org/downloads/
- Git: https://git-scm.com/downloads

## Validate The Skill Package

From the repository root:

```bash
python3 scripts/validate_package.py .
python3 -m unittest discover tests
```

The package validator checks frontmatter, routed resources, portability, JSON/CSV validity, Python syntax, stale marketplace artifacts, generated caches, and platform-specific assumptions.

## Validate Research Deliverables

Medium, heavy, and super-heavy outputs should run the relevant validators from the skill root. Typical POSIX commands:

```bash
python3 scripts/scan_readability.py <deliverable-path>
python3 scripts/validate_deliverable.py <deliverable-path> --tier <medium|heavy|super-heavy> --profile standard --h1-policy error
python3 scripts/validate_research.py --sources <source-ledger.csv> --claims <claim-evidence-ledger.csv> --tier <medium|heavy|super-heavy>
python3 scripts/validate_coverage.py --ledger <document-coverage.csv> --expected-items <count> --core-question-id <Q1> --central-unit-id <U1> --source-units <S1=total-pages>
python3 scripts/validate_review.py --record <review-record.json> --deliverable <deliverable-path> --contract <depth-contract.json> --review-type evidence-logic
python3 scripts/validate_depth.py --contract <depth-contract.json> --deliverable <deliverable-path> --tier <medium|heavy|super-heavy>
```

On Windows, use `py -3` instead of `python3` when available.

## Depth Tiers

| Tier | Typical Use | Key Constraint |
|---|---|---|
| Light | Clear, bounded question | Fast answer with evidence discipline |
| Medium | Systematic topic explanation | Explanatory synthesis and validation |
| Heavy | Complex/high-cost problem | Stronger evidence, review, and depth gates |
| Super-heavy | Field-level or book-level knowledge engineering | Highest rigor and coverage expectations |

The tier is not a word-count preset. The skill uses dynamic depth contracts to prevent under-explained work and filler.

## Design Commitments

- Align before research.
- Research before writing.
- Synthesize instead of stitching summaries.
- Separate fact, source claim, inference, advice, and uncertainty.
- Track claim-evidence relationships.
- Check source coverage for long-document reading.
- Run independent critical review for medium-and-above work when the environment supports it.
- Default to portable Markdown, not Obsidian-only syntax.
- Do not fake completeness when sources are missing or evidence is weak.

## License

MIT
