# AI Native Toolkit: LinkedIn Analyzer

A powerful Python-based LinkedIn Content Strategy Analyzer. Analyze full profiles or deconstruct individual viral posts — then generate AI-driven growth strategies.

Designed for creators, entrepreneurs, and AI agents.

## Features

- **Profile Analysis**: Cadence, engagement, post type breakdown, content pillars, archetypes, hook/CTA formulas.
- **Viral Post Deconstructor**: Reverse-engineer any single LinkedIn post — why it worked, hook/CTA formulas, replication guide.
- **AI Insights**: Executive summaries, content pillars, post archetypes, hook/CTA strategies powered by Gemini, OpenAI, or Anthropic.
- **8-Page PDF Report**: Professional, visual report generated using `fpdf2`.
- **Agent Native**: Built-in skill definitions for Claude Code, Codex, Cursor, Antigravity, OpenClaw, and ZeroClaw.

## Installation

```bash
# Clone the repository
git clone https://github.com/behramshukur/ai-native-toolkit.git
cd ai-native-toolkit

# Install in editable mode
pip install -e .
```

## Setup

You need an [Apify API Key](https://apify.com/) and at least one LLM Provider key:

```bash
export APIFY_API_KEY='your_apify_key'
export GEMINI_API_KEY='your_gemini_key'  # or OPENAI_API_KEY or ANTHROPIC_API_KEY
```

## CLI Usage

### 1. Extract Raw Data

```bash
linkedin-analyzer extract --url <profile_url>
# Optional: --limit-per-source 10 --scrape-until 2025-01-01 --deep-scrape --raw-data
```

### 2. Analyze a Profile

```bash
linkedin-analyzer profile --url <profile_url> --output analysis.json
# Optional: --limit-per-source 10 --scrape-until 2025-01-01 --skip-ai
```

### 3. Deconstruct a Single Post

```bash
linkedin-analyzer post --url <post_url> --output deconstruct.json
# Optional: --skip-ai
```

### 4. Generate PDF Report

```bash
linkedin-analyzer pdf --file analysis.json --output report.pdf
# Or run from URL directly:
linkedin-analyzer pdf --url <profile_url> --output report.pdf
```

## Sample Output

A real PDF report is included so you can see the output before running anything:

- [jon_report_v2.pdf](jon_report_v2.pdf) — 8-page PDF report (100 posts, 8 weeks, 3,777 reactions, AI-generated content pillars, archetypes, hook/CTA strategies)

## Agent Integrations

This toolkit installs as a native skill for AI agents. The install script auto-detects which agents are on your system and copies the right files.

```bash
# Clone the repo (if you haven't already)
git clone https://github.com/Behruamm/ai-native-toolkit.git
cd ai-native-toolkit

# Install the toolkit
pip install -e .

# Install skill for all detected agents
python integrations/install.py --agent all

# Or install for a specific agent
python integrations/install.py --agent claude-code
```

See which agents are detected on your system:

```bash
python integrations/install.py --list
```

Supported agents and install locations:

- **Claude Code**: `~/.claude/skills/linkedin-analyzer/`
- **Codex**: `~/.codex/skills/linkedin-analyzer/`
- **Cursor**: `~/.cursor/rules/linkedin-analyzer.mdc`
- **Antigravity**: `~/.gemini/antigravity/skills/linkedin-analyzer/`
- **OpenClaw**: `~/.openclaw/skills/linkedin-analyzer/`
- **ZeroClaw**: `~/.zeroclaw/workspace/skills/linkedin-analyzer/`

After installing, restart your agent and ask it to analyze a LinkedIn profile.
