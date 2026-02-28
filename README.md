# AI Native Toolkit

Two Python CLI tools for LinkedIn intelligence — built for creators, recruiters, and AI agents.

## Tools

### `linkedin-analyzer` — Content Strategy Analyzer

Analyze full LinkedIn profiles or deconstruct individual viral posts to extract content strategy, hooks, CTAs, and AI-generated growth blueprints.

### `talent-scout` — Competitor Talent Intelligence

Scrape a competitor's LinkedIn company people page, filter by job title, rank the top 5 targets with AI, generate personalized outreach DMs, and produce a competitive team brief.

---

## Features

### linkedin-analyzer

- **Profile Analysis**: Cadence, engagement, post type breakdown, content pillars, archetypes, hook/CTA formulas
- **Viral Post Deconstructor**: Reverse-engineer any LinkedIn post — why it worked, hook/CTA formulas, replication guide
- **AI Insights**: Executive summaries, content pillars, archetypes, hook/CTA strategies via Gemini, OpenAI, or Anthropic
- **8-Page PDF Report**: Professional dark-theme report via `fpdf2`. Use `--no-cta` to omit the offer page
- **Agent Native**: Skill definitions for Claude Code, Codex, Cursor, Antigravity, OpenClaw, and ZeroClaw

### talent-scout

- **Competitor Scraping**: Pulls employee lists from any LinkedIn company people page via Apify
- **AI Ranking**: Identifies the top 5 highest-value targets by seniority and specialization
- **Personalized DMs**: Ready-to-send LinkedIn outreach messages per target (under 300 chars)
- **Team Structure Insights**: 3-5 competitive intelligence observations about hiring patterns
- **6-Page PDF Brief**: Cover, exec summary, ranked candidates, DM drafts, team insights, full candidate list

---

## Installation

```bash
git clone https://github.com/behramshukur/ai-native-toolkit.git
cd ai-native-toolkit
pip install -e .
```

## Setup

Requires an [Apify API Key](https://apify.com/) and at least one LLM provider key:

```bash
export APIFY_API_KEY='your_apify_key'
export GEMINI_API_KEY='your_gemini_key'  # or OPENAI_API_KEY or ANTHROPIC_API_KEY
```

---

## CLI Usage — linkedin-analyzer

### Extract raw data

```bash
linkedin-analyzer extract --url <profile_url>
# Optional: --limit-per-source 10 --scrape-until 2025-01-01 --deep-scrape --raw-data
```

### Analyze a profile

```bash
linkedin-analyzer profile --url <profile_url> --output analysis.json
# Optional: --limit-per-source 10 --scrape-until 2025-01-01 --skip-ai
```

### Deconstruct a single post

```bash
# JSON only
linkedin-analyzer post --url <post_url> --output deconstruct.json

# JSON + PDF
linkedin-analyzer post --url <post_url> --pdf report.pdf

# Without CTA page
linkedin-analyzer post --url <post_url> --pdf report.pdf --no-cta
```

### Generate PDF report

```bash
linkedin-analyzer pdf --file analysis.json --output report.pdf

# Without CTA page
linkedin-analyzer pdf --file analysis.json --output report.pdf --no-cta
```

---

## CLI Usage — talent-scout

### Full scout (scrape + AI + PDF)

```bash
talent-scout scout \
  --url "https://www.linkedin.com/company/google/people/" \
  --title "Senior Software Engineer" \
  --output report.json \
  --pdf brief.pdf
```

### Extract raw candidates only

```bash
talent-scout extract \
  --url "https://www.linkedin.com/company/stripe/people/" \
  --title "Product Manager" \
  --output raw_candidates.json
```

### Generate PDF from existing JSON

```bash
talent-scout pdf --file report.json --output brief.pdf
```

### Optional flags

- `--limit N` — max candidates to retrieve
- `--skip-ai` — skip LLM ranking and outreach generation
- `--file path.json` — use local JSON instead of scraping

---

## Sample Output

A real PDF report is included so you can see the output before running anything:

- [jon_report_v2.pdf](jon_report_v2.pdf) — 8-page profile report (100 posts, 8 weeks, 3,777 reactions)

---

## Agent Integrations

Both tools install as native skills for AI agents. The install script auto-detects which agents are on your system.

```bash
# Install skills for all detected agents
python integrations/install.py --agent all

# Install for a specific agent
python integrations/install.py --agent claude-code

# See which agents are detected
python integrations/install.py --list
```

Install locations:

| Agent | linkedin-analyzer | talent-scout |
| --- | --- | --- |
| Claude Code | `~/.claude/skills/linkedin-analyzer/` | `~/.claude/skills/talent-scout/` |
| Codex | `~/.codex/skills/linkedin-analyzer/` | — |
| Cursor | `~/.cursor/rules/linkedin-analyzer.mdc` | — |
| Antigravity | `~/.gemini/antigravity/skills/linkedin-analyzer/` | — |
| OpenClaw | `~/.openclaw/skills/linkedin-analyzer/` | — |
| ZeroClaw | `~/.zeroclaw/workspace/skills/linkedin-analyzer/` | — |

After installing, restart your agent and ask it to analyze a LinkedIn profile or scout a competitor.
