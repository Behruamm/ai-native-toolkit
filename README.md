# AI Native Toolkit: LinkedIn Content Analyzer

A native Python toolkit that analyzes any LinkedIn profile's content strategy. Designed both as a standalone CLI tool and as a deployable skill for 6 popular AI agents (Claude Code, OpenAI Codex, Cursor, Google Antigravity, OpenClaw, ZeroClaw).

## Features
- **Deterministic Metrics**: Computes cadence, engagement, formatting, and scheduling profiles.
- **AI Content Strategy**: Employs Gemini, OpenAI, or Anthropic to deduce content pillars, post archetypes, top/worst post analysis, hook/CTA formulas, and master strategies.
- **Agent Integrations**: First-class support for native AI agent deployment.
- **Report Generation**: Exports rich 8-page PDF summaries.

## Getting Started

### Installation

**As a standalone CLI:**
```bash
pip install ai-native-toolkit
```

**As an AI Agent Skill:**
```bash
# Auto-detects installed agents and configures the skill
python integrations/install.py
```

### Usage
Extract raw data:
```bash
linkedin-analyzer extract --url "https://linkedin.com/in/someone"
```

Perform a full analysis:
```bash
linkedin-analyzer analyze --url "https://linkedin.com/in/someone"
```

Generate PDF report:
```bash
linkedin-analyzer pdf --url "https://linkedin.com/in/someone" --output report.pdf
```
