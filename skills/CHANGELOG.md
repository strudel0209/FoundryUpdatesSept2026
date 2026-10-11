# Kit skills · changelog

Versions of the three Cowork skills shipped in `skills/`. The version line at the top of each
`SKILL.md` must match the newest entry here. Semantic versioning: MAJOR = a change that breaks
existing decks, notebooks or `kit.yaml`; MINOR = new rule, mode or script; PATCH = wording fixes.
A change to the shared visual system or to the Slide wording rules updates **both** deck skills
(and `scripts/deck_lib.py`) in the same release.

## 1.0.0 · 2026-10-11 — first shared release

**All three skills**
- New "Kit and repository setup": the kit is the attached folder holding `kit.yaml`; every path
  is read from it; presenter from the running user's Microsoft 365 profile (or a git-ignored
  `kit.local.yaml`); deliver to `output/`, upload into the kit only on request; Cowork never pushes
  to GitHub — branch and pull request.
- Version line at the top of every `SKILL.md`.
- Hand-offs between the skills are conditional on the target skill being installed.
- References to the personal `azure-ai-architecture-decks` skill removed; from-scratch builds go
  to `azure-ai-deep-dive-deck`.
- No personal names, OneDrive paths or internal package feeds.

**azure-ai-deep-dive-deck** (`SKILL.md` + `scripts/deck_lib.py`, `scripts/deck_qa.py`)
- Slide wording rules 4–6 added (from presenter review): no "Learn says / Learn lists" on slides
  or in notes — "as per official documentation" or no attribution; named actors ("development
  team"), never "agent team"; every row of a slide table answers the table's own question.
- Rules 1–3 kept: noun-phrase titles, plain subtitles, no "you/your" on slides.
- Build step uses the bundled `deck_lib.py` (canonical visual system on python-pptx);
  QA step runs `deck_qa.py` before inspecting every rendered slide.
- Hand-off registers the deck in `decks/DEEP-DIVE-DECKS.md` and `kit.yaml` (diff, on approval).

**foundry-whats-new-deck** (`SKILL.md` + `scripts/deck_qa.py`)
- Slide wording rules 4–6 mirrored; QA checklist extended.
- Changelog path from `kit.yaml` (`decks/CHANGELOG.md`); current edition read from it instead of a
  hard-coded file name; slide 9 in the slide map is now "Priority and Flex processing".
- Multi-maintainer rule: re-read the changelog before APPLY and re-base on a newer edition.

**deck-companion-notebook** (`SKILL.md` + `scripts/kit_check.py`)
- Section 1 reads `kit.yaml` instead of a dated kit snapshot and a fixed OneDrive path.
- Private package index moved out of shared files (`kit.local.yaml` or the contributor's
  `PIP_INDEX_URL`); the shared devcontainer uses PyPI.
- Markdown wording rules aligned with deck rules 4–6 (the old guardrail line read as if
  "development team" were banned).
- Deck changelog path is `decks/CHANGELOG.md`; new `kit.yaml` diff (notebook entry, env entries,
  next notebook number) on every BUILD; pull-request flow with `kit-gate.md`.

## Pre-release history (single user, not shipped)
- 2026-10-10 · `deck-companion-notebook` created; kit_check.py false positives fixed; "No tested
  version yet" pin rule.
- early October 2026 · slide-wording rules 1–3 added to both deck skills.
- 2026-09 · `azure-ai-deep-dive-deck` and `foundry-whats-new-deck` created.
