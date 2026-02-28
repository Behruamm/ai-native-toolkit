import asyncio
import json
from datetime import datetime
from typing import Optional

from .scraper import scrape_company_people
from .cleaner import clean_candidates
from .ai_insights import (
    get_provider,
    rank_top_candidates,
    generate_outreach_drafts,
    analyze_team_structure,
    generate_executive_summary,
)
from .types import TalentReport


async def run_scout(
    company_url: str,
    target_title: str,
    skip_ai: bool = False,
    local_file_json: Optional[str] = None,
    limit: Optional[int] = None,
) -> TalentReport:
    """
    Full talent scouting pipeline:
    1. Scrape company people (or load from file)
    2. Clean + filter candidates
    3. AI: rank top 5, generate outreach drafts, analyze team structure
    4. Assemble TalentReport
    """
    print(f"[TalentScout] Scouting '{target_title}' at {company_url or local_file_json}")

    # 1. Scrape or Load
    if local_file_json:
        with open(local_file_json, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
        if isinstance(raw_data, list):
            raw_candidates = raw_data
        else:
            raw_candidates = raw_data.get("candidates", raw_data.get("items", []))
    else:
        if not company_url:
            raise ValueError("Must provide either company_url or local_file_json")
        print(f"[TalentScout] Scraping via Apify (this may take 1-3 minutes)...")
        raw_candidates = scrape_company_people(
            company_url=company_url,
            target_title=target_title,
            limit=limit,
        )

    print(f"[TalentScout] Raw candidates fetched: {len(raw_candidates)}")

    # 2. Clean + Filter
    candidates = clean_candidates(raw_candidates, target_title, limit=limit or 200)
    print(f"[TalentScout] Candidates after filtering: {len(candidates)}")

    if not candidates:
        raise ValueError(
            f"No valid candidates found for '{target_title}' at {company_url}. "
            "Try broadening the title filter."
        )

    # 3. AI Analysis
    provider = None if skip_ai else get_provider()

    if provider:
        print(f"[TalentScout] Using AI Provider: {provider.__class__.__name__}")

        # Phase 1 parallel: ranking + team structure analysis
        print("[TalentScout] Ranking top candidates and analyzing team structure...")
        rank_task = rank_top_candidates(provider, candidates, target_title, company_url)
        team_task = analyze_team_structure(provider, candidates, target_title, company_url)

        results = await asyncio.gather(rank_task, team_task, return_exceptions=True)

        top5 = results[0] if not isinstance(results[0], Exception) else []
        team_insights = results[1] if not isinstance(results[1], Exception) else []

        if isinstance(results[0], Exception):
            print(f"[TalentScout] WARNING: Ranking failed: {results[0]}")
        if isinstance(results[1], Exception):
            print(f"[TalentScout] WARNING: Team analysis failed: {results[1]}")

        # Phase 2: outreach drafts + executive summary (need top5 first)
        print("[TalentScout] Generating outreach drafts and executive summary...")

        # Extract company name from URL for messaging
        company_name = company_url.rstrip("/").split("/")[-1].replace("-", " ").title()

        draft_task = generate_outreach_drafts(provider, top5, target_title, company_name)
        summary_task = generate_executive_summary(provider, candidates, top5, target_title, company_url)

        phase2 = await asyncio.gather(draft_task, summary_task, return_exceptions=True)

        outreach_drafts = phase2[0] if not isinstance(phase2[0], Exception) else []
        exec_summary = phase2[1] if not isinstance(phase2[1], Exception) else ""

        if isinstance(phase2[0], Exception):
            print(f"[TalentScout] WARNING: Outreach drafts failed: {phase2[0]}")
        if isinstance(phase2[1], Exception):
            print(f"[TalentScout] WARNING: Executive summary failed: {phase2[1]}")

    else:
        print("[TalentScout] Skipping AI generation. Using placeholders.")
        top5 = []
        team_insights = []
        outreach_drafts = []
        exec_summary = "AI analysis skipped via --skip-ai flag."

    # 4. Assemble report
    return TalentReport(
        companyUrl=company_url,
        targetTitle=target_title,
        scoutedAt=datetime.utcnow().isoformat() + "Z",
        totalCandidatesFound=len(candidates),
        candidates=candidates,
        top5=top5,
        outreachDrafts=outreach_drafts,
        teamInsights=team_insights,
        executiveSummary=exec_summary,
    )
