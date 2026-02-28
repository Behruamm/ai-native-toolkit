import os
import json
import re
from typing import List, Any

from .types import (
    Candidate,
    RankedCandidate,
    OutreachDraft,
    TeamStructureInsight,
)


# ============================================================
# PROVIDER SELECTION (mirrors linkedin_analyzer pattern)
# ============================================================


def get_provider():
    if os.environ.get("GEMINI_API_KEY"):
        from linkedin_analyzer.providers.gemini import GeminiProvider
        return GeminiProvider()
    elif os.environ.get("OPENAI_API_KEY"):
        from linkedin_analyzer.providers.openai_provider import OpenAIProvider
        return OpenAIProvider()
    elif os.environ.get("ANTHROPIC_API_KEY"):
        from linkedin_analyzer.providers.anthropic_provider import AnthropicProvider
        return AnthropicProvider()
    return None


# ============================================================
# JSON EXTRACTION HELPER
# ============================================================


def extract_json(raw: str) -> Any:
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        pass

    for match in re.finditer(r"[\[{]", raw):
        try:
            decoder = json.JSONDecoder()
            obj, _ = decoder.raw_decode(raw[match.start():])
            return obj
        except json.JSONDecodeError:
            continue

    raise ValueError("No valid JSON found in LLM response")


# ============================================================
# AI TASKS
# ============================================================


def _candidates_context(candidates: List[Candidate], limit: int = 50) -> str:
    rows = []
    for i, c in enumerate(candidates[:limit]):
        rows.append({
            "index": i,
            "name": c.name,
            "title": c.title,
            "location": c.location,
            "profileUrl": c.profileUrl,
            "summary": c.summary[:200] if c.summary else "",
        })
    return json.dumps(rows, ensure_ascii=False, indent=2)


async def rank_top_candidates(
    provider,
    candidates: List[Candidate],
    target_title: str,
    company_url: str,
) -> List[RankedCandidate]:
    """
    Use LLM to rank the top 5 most valuable candidates.
    """
    context = _candidates_context(candidates, limit=60)

    prompt = f"""You are a senior technical recruiter and talent intelligence analyst.
You are scouting for "{target_title}" roles at the company: {company_url}

Here are the matched candidates:
{context}

Your job: Identify the TOP 5 highest-value targets. Prioritize candidates who:
1. Hold senior-level titles (Senior, Lead, Staff, Principal, Director)
2. Have specific, relevant seniority signals in their title
3. Appear to be in influential or specialized roles
4. Are NOT currently in a recruiting, HR, or ops function

Return ONLY a JSON array of exactly 5 objects:
[
  {{
    "rank": 1,
    "name": "Full Name",
    "title": "Their current title",
    "location": "Their location",
    "profileUrl": "Their LinkedIn URL",
    "whyTarget": "1-2 sentences: exactly why this person is a high-value recruit. Be specific about their seniority, specialization, or influence.",
    "outreachAngle": "The one specific hook or angle to use in a DM to this person — what would make them interested in a conversation?"
  }},
  ...
]

Rules:
- Rank 1 = highest priority target
- Be specific and concrete — no generic descriptions
- outreachAngle must be personalized to their title/background, not generic
- Return ONLY valid JSON array, no markdown"""

    raw = await provider.generate(prompt)
    try:
        data = extract_json(raw)
        if not isinstance(data, list):
            raise ValueError("Expected JSON array")
        ranked = []
        for item in data:
            if isinstance(item, dict):
                ranked.append(RankedCandidate(
                    rank=int(item.get("rank", 0) or 0),
                    name=str(item.get("name", "")),
                    title=str(item.get("title", "")),
                    location=str(item.get("location", "")),
                    profileUrl=str(item.get("profileUrl", "")),
                    whyTarget=str(item.get("whyTarget", "")),
                    outreachAngle=str(item.get("outreachAngle", "")),
                ))
        return ranked[:5]
    except Exception:
        return []


async def generate_outreach_drafts(
    provider,
    top5: List[RankedCandidate],
    target_title: str,
    company_name: str,
) -> List[OutreachDraft]:
    """
    Generate personalized LinkedIn DM drafts for each top candidate.
    """
    candidates_data = [
        {
            "name": c.name,
            "title": c.title,
            "location": c.location,
            "profileUrl": c.profileUrl,
            "outreachAngle": c.outreachAngle,
        }
        for c in top5
    ]

    prompt = f"""You are a world-class technical recruiter writing LinkedIn outreach messages.
You need to recruit people currently working as "{target_title}" at {company_name}.

Write one personalized DM for each of the following candidates:
{json.dumps(candidates_data, ensure_ascii=False, indent=2)}

Each DM must:
- Start with a genuine, specific observation about their role (not "I saw your profile")
- Reference their specific outreachAngle
- Be soft and conversational — this is NOT a job ad, it's a feeler message
- Be under 300 characters (LinkedIn InMail limit for cold outreach)
- End with ONE low-commitment ask (e.g. "Would you be open to a quick chat?")

Return ONLY a JSON array:
[
  {{
    "candidateName": "Their full name",
    "profileUrl": "Their LinkedIn URL",
    "subject": "Short subject line (max 8 words)",
    "message": "The full DM message under 300 chars"
  }},
  ...
]

Return ONLY valid JSON array, no markdown."""

    raw = await provider.generate(prompt)
    try:
        data = extract_json(raw)
        if not isinstance(data, list):
            raise ValueError("Expected JSON array")
        drafts = []
        for item in data:
            if isinstance(item, dict):
                drafts.append(OutreachDraft(
                    candidateName=str(item.get("candidateName", "")),
                    profileUrl=str(item.get("profileUrl", "")),
                    subject=str(item.get("subject", "")),
                    message=str(item.get("message", "")),
                ))
        return drafts
    except Exception:
        return []


async def analyze_team_structure(
    provider,
    candidates: List[Candidate],
    target_title: str,
    company_url: str,
) -> List[TeamStructureInsight]:
    """
    Generate 3-5 strategic insights about the competitor's team structure.
    """
    context = _candidates_context(candidates, limit=80)

    prompt = f"""You are a competitive intelligence analyst studying the talent profile of a competitor company.
Company: {company_url}
Role you're analyzing: "{target_title}"

Here is the full list of matched employees:
{context}

Analyze this team and return 3-5 strategic insights about their team structure, hiring patterns, and what it reveals about their business strategy.

Return ONLY a JSON array:
[
  {{
    "observation": "A specific factual observation about the team (e.g. 'Over 60% of Senior Engineers are based in London')",
    "pattern": "The underlying pattern this reveals (e.g. 'Strong preference for European talent, likely tied to GDPR compliance needs')",
    "implication": "What this means strategically for a competitor (e.g. 'They are building a dedicated EU engineering hub — expect product localization focus in 2025')"
  }},
  ...
]

Rules:
- Be specific — reference actual data from the candidate list (locations, title seniority, etc.)
- Each insight should feel like a $10k/hr consultant's observation
- Return ONLY valid JSON array, no markdown"""

    raw = await provider.generate(prompt)
    try:
        data = extract_json(raw)
        if not isinstance(data, list):
            raise ValueError("Expected JSON array")
        insights = []
        for item in data:
            if isinstance(item, dict):
                insights.append(TeamStructureInsight(
                    observation=str(item.get("observation", "")),
                    pattern=str(item.get("pattern", "")),
                    implication=str(item.get("implication", "")),
                ))
        return insights[:5]
    except Exception:
        return []


async def generate_executive_summary(
    provider,
    candidates: List[Candidate],
    top5: List[RankedCandidate],
    target_title: str,
    company_url: str,
) -> str:
    """
    Generate a 2-3 sentence executive summary of the talent scouting run.
    """
    prompt = f"""You are a talent intelligence analyst writing a briefing for a hiring manager.

Company scouted: {company_url}
Target role: "{target_title}"
Total matching employees found: {len(candidates)}
Top 5 targets identified: {", ".join(c.name for c in top5)}

Write a 2-3 sentence executive summary that:
1. States what was found (volume, seniority distribution)
2. Names the highest-priority target and why
3. Gives one actionable next step

Be crisp, confident, and specific. No fluff. Return ONLY the plain text summary (no JSON, no markdown)."""

    try:
        return (await provider.generate(prompt)).strip()
    except Exception:
        return f"Found {len(candidates)} matching '{target_title}' profiles. Top target: {top5[0].name if top5 else 'N/A'}."
