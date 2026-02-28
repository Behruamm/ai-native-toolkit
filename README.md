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

## Agent Integrations

This toolkit is designed to be a "skill" for AI agents. To install for your preferred agent:

```bash
python integrations/install.py --agent all
```

Supported Agents:
- **Claude Code**: Installs to `~/.claude/skills/`
- **Codex**: Installs to `~/.codex/skills/`
- **Cursor**: Installs as a `.cursorrule`
- **Antigravity**: Installs to `~/.gemini/antigravity/skills/`
- **OpenClaw**: Installs to `~/.openclaw/skills/`
- **ZeroClaw**: Installs to `~/.zeroclaw/workspace/skills/`
