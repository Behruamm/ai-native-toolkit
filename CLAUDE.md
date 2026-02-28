# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Native Toolkit is a LinkedIn Content Strategy Analyzer that extracts LinkedIn posts via Apify, computes deterministic metrics (cadence, engagement, post types, hooks, CTAs), generates AI-powered insights (content pillars, archetypes, formulas), and produces an 8-page PDF report. It's designed as both a CLI tool and an installable skill for AI agents (Claude Code, Codex, Cursor, etc.).

## Environment Setup

**Required Environment Variables:**
- `APIFY_API_KEY` - Required for scraping LinkedIn data
- At least one LLM provider key:
  - `GEMINI_API_KEY` (preferred, checked first)
  - `OPENAI_API_KEY` (fallback)
  - `ANTHROPIC_API_KEY` (fallback)

**Installation:**
```bash
# Install in editable mode for development
pip install -e .

# For production
pip install .
```

**Python Version:** Requires Python >=3.10 (see pyproject.toml)

## Common Commands

### Development Workflow
```bash
# Install dependencies
pip install -e .

# Run tests
pytest

# Run a single test
pytest tests/test_cleaner.py::test_clean_apify_posts_basic

# Extract raw data only (no analysis)
linkedin-analyzer extract --url <profile_url>

# Run full analysis (deterministic + AI)
linkedin-analyzer profile --url <profile_url> --output analysis.json

# Skip AI insights (deterministic only)
linkedin-analyzer profile --url <profile_url> --skip-ai --output analysis.json

# Generate PDF from existing analysis
linkedin-analyzer pdf --file analysis.json --output report.pdf

# Run analysis from local JSON (skip scraping)
linkedin-analyzer profile --file local_posts.json --output analysis.json

# Deconstruct a single post + generate PDF
linkedin-analyzer post --url <post_url> --pdf report.pdf

# Deconstruct a single post, JSON only
linkedin-analyzer post --url <post_url> --output deconstruct.json
```

### Scraping Controls
```bash
# Limit posts per source
--limit-per-source 10

# Only scrape recent posts
--scrape-until 2025-01-01

# Control deep scraping
--deep-scrape  # Scrape additional post information (default: true)

# Get raw Apify data
--raw-data  # Return unprocessed data from scraper
```

### Agent Integration
```bash
# Install as a skill for all detected AI agents
python integrations/install.py --agent all

# Install for specific agent
python integrations/install.py --agent claude-code

# List detected agents on system
python integrations/install.py --list
```

## Architecture Overview

### Pipeline Flow
1. **Scraper** ([scraper.py](linkedin_analyzer/scraper.py)) - Calls Apify actor `supreme_coder~linkedin-post`, polls for completion, normalizes raw post data
2. **Cleaner** ([cleaner.py](linkedin_analyzer/cleaner.py)) - Converts Apify posts to `CleanPost` schema, extracts author headline from first post
3. **Metrics** ([metrics.py](linkedin_analyzer/metrics.py)) - Computes deterministic analytics (cadence, engagement, post types, schedule, scoring, text patterns, hooks, CTAs, word frequency)
4. **AI Insights** ([ai_insights.py](linkedin_analyzer/ai_insights.py)) - Generates content pillars, archetypes, executive summary, top/worst post analysis, hook/CTA formulas and strategies
5. **Pipeline** ([pipeline.py](linkedin_analyzer/pipeline.py)) - Orchestrates the full flow: scrape → clean → metrics → AI (parallel where possible)
6. **PDF Report** ([pdf_report.py](linkedin_analyzer/pdf_report.py)) - Generates professional 8-page PDF using fpdf2

### LLM Provider System
The toolkit uses a provider abstraction ([providers/base.py](linkedin_analyzer/providers/base.py)) with three implementations:
- **GeminiProvider** - Uses Google Gemini API (checked first)
- **OpenAIProvider** - Uses OpenAI API
- **AnthropicProvider** - Uses Anthropic Claude API

Selection priority: Gemini > OpenAI > Anthropic (based on env var presence)

All providers implement `async def generate(prompt: str, system: str = "") -> str`

### AI Insight Generation Strategy
AI insights are generated in two phases:
1. **Parallelized Sequential Phase**: Content strategy (pillars/archetypes) - chunks processed concurrently, then consolidated
2. **Parallel Phase**: All other insights (executive summary, top/worst post analysis, hook/CTA formulas) via `asyncio.gather()`

Chunking strategy: Posts are split into chunks of 40 (`CHUNK_SIZE`) to avoid token limits when analyzing large datasets.

**Performance Optimizations (2026-02-28):**
- Pillar/archetype extraction now runs in parallel across all chunks (5x speedup)
- Category assignments parallelized (5x speedup)
- Executive summary chunks parallelized (5x speedup)
- Overall analysis time reduced by 40-50% (30s → 15-20s for 50 posts)

### Data Models (types.py)
Key Pydantic models:
- **ApifyPost** - Raw output from Apify scraper
- **CleanPost** - Normalized post after cleaning
- **FullAnalysis** - Complete report structure containing all metrics and insights
- **ScoredPost** - Post with engagement scoring (raw + age-adjusted)
- **HookAnalysis/CTAAnalysis** - Deterministic hook/CTA patterns
- **HookStrategy/CTAStrategy** - AI-generated semantic patterns with examples
- **ContentPillar/PostArchetype** - AI-identified content categories
- **PostDeconstruction** - Single-post viral analysis output
- **PostDeconstructionAI** - AI insights for single post (whyItWorked, archetype, formulas, replication guide)

### CLI Entry Point
The CLI ([cli.py](linkedin_analyzer/cli.py)) has three commands:
- `extract` - Scrape only, output raw JSON
- `profile` - Full profile analysis pipeline, output JSON
- `post` - Deconstruct a single viral post, output JSON; supports `--pdf` to also generate a 2-page PDF (deconstruction + CTA page)
- `pdf` - Generate PDF (can run full pipeline or use existing JSON)

All commands support `--url` (scrape) or `--file` (use local JSON).

## Key Implementation Patterns

### Post Scoring Algorithm
Posts receive two scores (see [metrics.py](linkedin_analyzer/metrics.py)):
1. **engagementScore** = (likes + 2×comments + 3×shares) / median_engagement
2. **ageAdjustedScore** = engagementScore × age_decay_factor (0.5-1.0 based on post recency)

Age decay gives 50% weight to oldest posts, 100% to newest, to account for time-based performance differences.

### Hook & CTA Detection
- **Hook**: First sentence of post text (see `extract_hook_text()`)
- **CTA**: Last paragraph if it contains action words like "comment", "follow", "DM", "share", "link" (see `extract_cta_text()`)

Hook types: Question, Number/List, Statement, Story, Provocative
CTA types: Comment-gated, Follow, DM, Save/Share, Link, None

### Error Handling in AI Pipeline
AI tasks use `asyncio.gather(*tasks, return_exceptions=True)` to prevent one failure from blocking others. Results are checked with `isinstance(res, Exception)` and fallback placeholders are provided.

### Text Cleaning for AI Analysis
URLs and hashtags are stripped from post text before pillar/archetype analysis to reduce noise (see `clean_for_pillars()`).

## Important Constraints

- **Apify Actor ID**: Hardcoded as `supreme_coder~linkedin-post` in [scraper.py](linkedin_analyzer/scraper.py:9)
- **Polling Timeout**: Scraper waits max 120s for Apify run completion
- **Default deep_scrape**: Set to `True` if not explicitly specified in CLI
- **Profile Metadata**: Extracted from first post's author data (name, headline)
- **AI Skip Mode**: When `--skip-ai` is used, placeholders are inserted for all AI-generated fields

## Agent Skill System

This toolkit is designed to be installable as a "skill" for AI agents. The integration files are in [integrations/](integrations/) with SKILL.md definitions for each agent.

Supported agents:
- **Claude Code**: Installs to `~/.claude/skills/linkedin-analyzer/SKILL.md`
- **Codex**: Installs to `~/.codex/skills/linkedin-analyzer/`
- **Cursor**: Installs as `.cursor/rules/linkedin-analyzer.mdc`
- **Antigravity**: Installs to `~/.gemini/antigravity/skills/`
- **OpenClaw**: Installs to `~/.openclaw/skills/`
- **ZeroClaw**: Installs to `~/.zeroclaw/workspace/skills/`

The install script ([integrations/install.py](integrations/install.py)) auto-detects which agents are present on the system by checking their home directories.

## Testing

Test files are in [tests/](tests/). Currently has basic cleaner tests.

Run tests with:
```bash
pytest
pytest tests/test_cleaner.py -v
```

## Programmatic Usage

Example from [examples/basic_extract.py](examples/basic_extract.py):
```python
import asyncio
from linkedin_analyzer.pipeline import run_full
from linkedin_analyzer.pdf_report import generate_pdf

async def main():
    # Run analysis
    analysis = await run_full(
        profile_url="https://linkedin.com/in/username",
        skip_ai=False,  # or True for deterministic only
        limit_per_source=50
    )

    # Generate PDF
    pdf_bytes = generate_pdf(analysis)
    with open("report.pdf", "wb") as f:
        f.write(pdf_bytes)

asyncio.run(main())
```

## Common Issues

**No posts found**: Check that Apify actor has correct permissions and the profile URL is public.

**AI generation fails**: Verify LLM API key is set and has sufficient quota. The pipeline will continue with placeholders.

**Import errors**: Ensure package is installed with `pip install -e .`
