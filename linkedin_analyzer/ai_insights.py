import os
import json
import re
from typing import List, Dict, Any, Tuple

from .types import (
    CleanPost,
    ScoredPost,
    ContentPillar,
    PostArchetype,
    HookStrategy,
    CTAStrategy,
    ChunkAnalysisResult,
    ConsolidatedAnalysis,
    StrategyPattern,
)
from .providers.base import LLMProvider
from .metrics import extract_hook_text, extract_cta_text


def get_provider() -> LLMProvider | None:
    if os.environ.get("GEMINI_API_KEY"):
        from .providers.gemini import GeminiProvider

        return GeminiProvider()
    elif os.environ.get("OPENAI_API_KEY"):
        from .providers.openai_provider import OpenAIProvider

        return OpenAIProvider()
    elif os.environ.get("ANTHROPIC_API_KEY"):
        from .providers.anthropic_provider import AnthropicProvider

        return AnthropicProvider()
    return None


def extract_json(raw: str) -> Any:
    """
    Tries to find the first valid JSON array or object in the response.
    Uses JSONDecoder to properly extract valid JSON instead of greedy regex.
    """
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


def build_hook_cta_context(
    posts: List[CleanPost],
    scored_posts: List[ScoredPost],
    limit: int = 50,
) -> str:
    scored_sorted = sorted(
        scored_posts, key=lambda p: p.ageAdjustedScore, reverse=True
    )
    if limit and limit > 0:
        scored_sorted = scored_sorted[:limit]

    rows = []
    for scored in scored_sorted:
        idx = scored.index
        if idx < 0 or idx >= len(posts):
            continue
        p = posts[idx]
        rows.append(
            {
                "index": idx,
                "url": p.url,
                "hook": extract_hook_text(p.text),
                "cta": extract_cta_text(p.text),
                "likes": p.numLikes,
                "comments": p.numComments,
                "shares": p.numShares,
                "score": scored.ageAdjustedScore,
            }
        )
    return json.dumps(rows, ensure_ascii=False, indent=2)


CHUNK_SIZE = 40
URL_REGEX = re.compile(r"https?://\S+", re.IGNORECASE)


def chunk_posts(posts: List[CleanPost], size: int = CHUNK_SIZE) -> List[List[CleanPost]]:
    return [posts[i : i + size] for i in range(0, len(posts), size)]


def clean_for_llm(text: str) -> str:
    """Remove URLs before sending to LLM to reduce token waste."""
    cleaned = URL_REGEX.sub("", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _normalize_patterns(items: Any) -> List[Dict[str, Any]]:
    patterns = []
    if not isinstance(items, list):
        return patterns
    for item in items:
        if isinstance(item, dict):
            name = item.get("name") or item.get("pattern") or "Pattern"
            patterns.append(
                {
                    "name": str(name).strip(),
                    "description": str(item.get("description", "")).strip(),
                    "engagementLevel": str(item.get("engagementLevel", "medium")),
                }
            )
        elif isinstance(item, str):
            patterns.append(
                {"name": item.strip(), "description": "", "engagementLevel": "medium"}
            )
    return patterns


def _normalize_examples(items: Any) -> List[Dict[str, Any]]:
    examples = []
    if not isinstance(items, list):
        return examples
    for item in items:
        if isinstance(item, dict):
            examples.append(
                {
                    "text": str(item.get("text", "")).strip(),
                    "url": str(item.get("url", "")).strip(),
                    "score": float(item.get("score", 0.0) or 0.0),
                }
            )
        elif isinstance(item, str):
            examples.append({"text": item.strip(), "url": "", "score": 0.0})
    return examples


def _coerce_consolidated(
    data: Dict[str, Any], posts: List[CleanPost]
) -> ConsolidatedAnalysis:
    pillars_raw = (
        data.get("pillars")
        or data.get("contentPillars")
        or data.get("content_pillars")
        or []
    )
    archetypes_raw = (
        data.get("archetypes")
        or data.get("postArchetypes")
        or data.get("post_archetypes")
        or []
    )

    pillars: List[ContentPillar] = []
    for item in pillars_raw if isinstance(pillars_raw, list) else []:
        if isinstance(item, dict):
            pillars.append(
                ContentPillar(
                    name=str(item.get("name", "General")).strip(),
                    description=str(item.get("description", "")).strip(),
                    percentageOfPosts=float(
                        item.get("percentageOfPosts", item.get("percentage", 0.0)) or 0.0
                    ),
                    engagementLevel=str(item.get("engagementLevel", "medium")),
                )
            )
    if not pillars:
        pillars = [
            ContentPillar(
                name="General",
                description="Content analysis",
                percentageOfPosts=100,
                engagementLevel="medium",
            )
        ]

    archetypes: List[PostArchetype] = []
    for item in archetypes_raw if isinstance(archetypes_raw, list) else []:
        if isinstance(item, dict):
            archetypes.append(
                PostArchetype(
                    name=str(item.get("name", "General")).strip(),
                    description=str(item.get("description", "")).strip(),
                    count=int(item.get("count", 0) or 0),
                    engagementLevel=str(item.get("engagementLevel", "medium")),
                )
            )
    if not archetypes:
        archetypes = [
            PostArchetype(
                name="General",
                description="Post analysis",
                count=len(posts),
                engagementLevel="medium",
            )
        ]

    hook_data = data.get("hookStrategy") or data.get("hook_strategy") or {}
    if not hook_data and "hookPatterns" in data:
        hook_data = {"patterns": data.get("hookPatterns")}
    hook_formula = str(
        hook_data.get("formula") or data.get("hookFormula") or "Analysis unavailable"
    )
    hook_patterns = _normalize_patterns(
        hook_data.get("patterns") or hook_data.get("hookPatterns") or []
    )
    hook_examples = _normalize_examples(
        hook_data.get("bestExamples") or hook_data.get("examples") or []
    )
    hook_strategy = HookStrategy(
        formula=hook_formula, patterns=hook_patterns, bestExamples=hook_examples
    )

    cta_data = data.get("ctaStrategy") or data.get("cta_strategy") or {}
    if not cta_data and "ctaPatterns" in data:
        cta_data = {"patterns": data.get("ctaPatterns")}
    cta_formula = str(
        cta_data.get("formula") or data.get("ctaFormula") or "Analysis unavailable"
    )
    cta_patterns = _normalize_patterns(
        cta_data.get("patterns") or cta_data.get("ctaPatterns") or []
    )
    cta_examples = _normalize_examples(
        cta_data.get("bestExamples") or cta_data.get("examples") or []
    )
    cta_strategy = CTAStrategy(
        formula=cta_formula, patterns=cta_patterns, bestExamples=cta_examples
    )

    exec_summary = str(
        data.get("executiveSummary")
        or data.get("executive_summary")
        or "Analysis unavailable"
    )

    return ConsolidatedAnalysis(
        pillars=pillars,
        archetypes=archetypes,
        hookStrategy=hook_strategy,
        ctaStrategy=cta_strategy,
        executiveSummary=exec_summary,
    )


# ============================================================
# OPTIMIZED PIPELINE: Single-pass chunk analysis + consolidation
# ============================================================


async def analyze_chunk_optimized(
    provider: LLMProvider,
    chunk: List[CleanPost],
    chunk_offset: int = 0,
) -> ChunkAnalysisResult:
    """
    Analyze a chunk of posts in ONE call - extract pillars, archetypes,
    hook patterns, CTA patterns, and assignments all at once.
    """
    parts = []
    for i, p in enumerate(chunk):
        clean_text = clean_for_llm(p.text)
        parts.append(
            f"--- Post {i} ({p.type}, {p.numLikes} likes, {p.numComments} comments) ---\n{clean_text}"
        )
    context = "\n\n".join(parts)

    prompt = f"""Analyze these {len(chunk)} LinkedIn posts comprehensively.

Posts:
{context}

Return ONLY a JSON object with:
{{
  "pillar_candidates": ["AI Automation", "Founder Lessons", ...],  // 3-5 content themes/topics
  "archetype_candidates": ["Listicle", "Personal Story", ...],     // 3-4 post formats
  "hook_patterns": [
    {{"name": "Money Hook", "description": "Mentions specific $ amount", "engagementLevel": "high"}},
    ...
  ],
  "cta_patterns": [
    {{"name": "Comment-gated", "description": "Comment for resource", "engagementLevel": "high"}},
    ...
  ],
  "post_assignments": [
    {{"index": 0, "pillar": "AI Automation", "archetype": "Listicle"}},
    ...
  ],
  "summary_bullets": [
    "Focuses on practical tutorials...",
    "Uses conversational tone...",
    ...
  ]
}}

IMPORTANT:
- Use the exact index numbers 0 to {len(chunk)-1} in post_assignments
- Assign every post to ONE pillar and ONE archetype from your candidates
- Base engagementLevel on the likes/comments you see in the posts
- Return ONLY valid JSON, no markdown or extra text
"""

    raw = await provider.generate(prompt)
    try:
        data = extract_json(raw)
        return ChunkAnalysisResult(**data)
    except Exception:
        return ChunkAnalysisResult(
            pillar_candidates=["General"],
            archetype_candidates=["General"],
            hook_patterns=[],
            cta_patterns=[],
            post_assignments=[
                {"index": i, "pillar": "General", "archetype": "General"}
                for i in range(len(chunk))
            ],
            summary_bullets=["Analysis failed - using fallback data"],
        )


async def consolidate_chunk_results(
    provider: LLMProvider,
    chunk_results: List[ChunkAnalysisResult],
    posts: List[CleanPost],
    scored_posts: List[ScoredPost],
) -> ConsolidatedAnalysis:
    """
    Consolidate all chunk analysis results into final categories and strategies.
    """
    all_pillar_candidates = []
    all_archetype_candidates = []
    all_hook_patterns = []
    all_cta_patterns = []
    all_summary_bullets = []

    for result in chunk_results:
        all_pillar_candidates.extend(result.pillar_candidates)
        all_archetype_candidates.extend(result.archetype_candidates)
        all_hook_patterns.extend(result.hook_patterns)
        all_cta_patterns.extend(result.cta_patterns)
        all_summary_bullets.extend(result.summary_bullets)

    hook_cta_context = build_hook_cta_context(posts, scored_posts, limit=50)

    prompt = f"""You are consolidating multiple chunk analyses into a final LinkedIn content strategy.

Pillar candidates from all chunks:
{json.dumps(all_pillar_candidates, ensure_ascii=False)}

Archetype candidates from all chunks:
{json.dumps(all_archetype_candidates, ensure_ascii=False)}

Hook patterns identified:
{json.dumps([p.model_dump() for p in all_hook_patterns], ensure_ascii=False, indent=2)}

CTA patterns identified:
{json.dumps([p.model_dump() for p in all_cta_patterns], ensure_ascii=False, indent=2)}

Summary bullets from all chunks:
{json.dumps(all_summary_bullets, ensure_ascii=False)}

Hook and CTA data (for best examples):
{hook_cta_context}

Return ONLY a JSON object:
{{
  "pillars": [
    {{"name": "AI Automation", "description": "...", "percentageOfPosts": 40, "engagementLevel": "high"}},
    ...
  ],
  "archetypes": [
    {{"name": "Listicle", "description": "...", "count": 45, "engagementLevel": "high"}},
    ...
  ],
  "hookStrategy": {{
    "formula": "One sentence describing the winning hook approach",
    "patterns": [
      {{"name": "Money Hook", "description": "...", "engagementLevel": "high"}},
      ...
    ],
    "bestExamples": [
      {{"text": "I spent $10,000...", "url": "https://...", "score": 3.2}},
      ...
    ]
  }},
  "ctaStrategy": {{
    "formula": "One sentence describing the winning CTA approach",
    "patterns": [
      {{"name": "Comment-gated", "description": "...", "engagementLevel": "high"}},
      ...
    ],
    "bestExamples": [
      {{"text": "Comment 'YES'...", "url": "https://...", "score": 2.8}},
      ...
    ]
  }},
  "executiveSummary": "3-4 sentences consolidating the summary bullets into one cohesive overview"
}}

Merge duplicates and synonyms. Use consistent naming. Return ONLY JSON."""

    raw = await provider.generate(prompt)
    try:
        data = extract_json(raw)
        try:
            return ConsolidatedAnalysis(**data)
        except Exception:
            return _coerce_consolidated(data, posts)
    except Exception:
        return ConsolidatedAnalysis(
            pillars=[
                ContentPillar(
                    name="General",
                    description="Content analysis",
                    percentageOfPosts=100,
                    engagementLevel="medium",
                )
            ],
            archetypes=[
                PostArchetype(
                    name="General",
                    description="Post analysis",
                    count=len(posts),
                    engagementLevel="medium",
                )
            ],
            hookStrategy=HookStrategy(
                formula="Analysis unavailable", patterns=[], bestExamples=[]
            ),
            ctaStrategy=CTAStrategy(
                formula="Analysis unavailable", patterns=[], bestExamples=[]
            ),
            executiveSummary="Consolidation failed - using fallback data",
        )


async def analyze_best_worst_posts(
    provider: LLMProvider,
    top_posts: List[ScoredPost],
    worst_posts: List[ScoredPost],
    avg_reactions: float,
    avg_comments: float,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Analyze top 5 and worst 5 posts together in one call.
    """
    top_5 = top_posts[:5]
    worst_5 = worst_posts[:5]

    top_data = [
        {
            "text": p.text,
            "likes": p.numLikes,
            "comments": p.numComments,
            "shares": p.numShares,
            "score": round(p.ageAdjustedScore, 2),
        }
        for p in top_5
    ]

    worst_data = [
        {
            "text": p.text,
            "likes": p.numLikes,
            "comments": p.numComments,
            "score": round(p.ageAdjustedScore, 2),
        }
        for p in worst_5
    ]

    prompt = f"""Analyze the best and worst performing LinkedIn posts.

Average performance: {avg_reactions:.0f} reactions, {avg_comments:.0f} comments

TOP 5 POSTS (significantly outperformed average):
{json.dumps(top_data, ensure_ascii=False, indent=2)}

WORST 5 POSTS (underperformed average):
{json.dumps(worst_data, ensure_ascii=False, indent=2)}

Return ONLY a JSON object:
{{
  "topPostsAnalysis": [
    {{"text": "First 50 chars of post...", "reasons": ["Reason 1", "Reason 2", "Reason 3"]}},
    ...
  ],
  "worstPostsAnalysis": [
    {{"text": "First 50 chars of post...", "why_flopped": "1-2 sentence explanation"}},
    ...
  ]
}}

For top posts: Provide exactly 3 specific reasons why each outperformed.
For worst posts: Provide 1-2 sentences explaining why each underperformed.
Be specific to the actual content, not generic."""

    raw = await provider.generate(prompt)
    try:
        data = extract_json(raw)
        top_analysis = data.get("topPostsAnalysis", [])
        worst_analysis = data.get("worstPostsAnalysis", [])
        return (top_analysis, worst_analysis)
    except Exception:
        top_analysis = [
            {"text": p.text[:50], "reasons": ["Analysis unavailable"]} for p in top_5
        ]
        worst_analysis = [
            {"text": p.text[:50], "why_flopped": "Analysis unavailable"}
            for p in worst_5
        ]
        return (top_analysis, worst_analysis)
