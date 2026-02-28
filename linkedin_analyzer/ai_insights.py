import os
import json
import re
from typing import List, Dict, Any

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
    AgentWorkflow,
    StealThisHook,
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

    big_opportunity = str(
        data.get("bigStrategicOpportunity")
        or data.get("big_strategic_opportunity")
        or ""
    )

    return ConsolidatedAnalysis(
        pillars=pillars,
        archetypes=archetypes,
        hookStrategy=hook_strategy,
        ctaStrategy=cta_strategy,
        executiveSummary=exec_summary,
        bigStrategicOpportunity=big_opportunity,
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

    prompt = f"""You are a senior LinkedIn content strategist. Analyze these {len(chunk)} LinkedIn posts and identify the underlying content system.

Posts:
{context}

IMPORTANT: Weight your analysis toward posts with higher likes/comments — they reveal what actually resonates.

Return ONLY a JSON object with:
{{
  "pillar_candidates": [
    {{"name": "AI Automation", "description": "Practical how-to content on automating business workflows — drives authority and inbound leads"}},
    ...
  ],
  "archetype_candidates": ["Listicle", "Personal Story", ...],
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
- Each pillar_candidate must have both "name" and "description" — description explains WHY this topic drives engagement
- Base engagementLevel on the actual likes/comments you see in the posts
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
        for pc in result.pillar_candidates:
            if isinstance(pc, dict):
                all_pillar_candidates.append(pc)
            else:
                all_pillar_candidates.append({"name": str(pc), "description": ""})
        all_archetype_candidates.extend(result.archetype_candidates)
        all_hook_patterns.extend(result.hook_patterns)
        all_cta_patterns.extend(result.cta_patterns)
        all_summary_bullets.extend(result.summary_bullets)

    hook_cta_context = build_hook_cta_context(posts, scored_posts, limit=50)

    prompt = f"""You are a senior content strategist and AI-native business advisor consolidating a LinkedIn profile analysis.
Your tone is sharp, opinionated, and ROI-focused. You're writing for a reader who wants to understand WHY this profile wins — not just WHAT they post.

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
    {{
      "name": "AI Automation",
      "description": "Sharp, opinionated description of what this pillar is, WHY it drives engagement, and what strategic ROI it creates for the creator (e.g. 'Positions them as the go-to operator in AI — every post here compounds authority and inbound')",
      "percentageOfPosts": 40,
      "engagementLevel": "high"
    }},
    ...
  ],
  "archetypes": [
    {{
      "name": "Listicle",
      "description": "Describe not just the format but WHY this archetype converts — the psychology and engagement mechanic behind it",
      "count": 45,
      "engagementLevel": "high"
    }},
    ...
  ],
  "hookStrategy": {{
    "formula": "One punchy, actionable sentence summarizing the hook formula — make it sound like a trade secret",
    "patterns": [
      {{"name": "Money Hook", "description": "Specific mechanism: why this pattern stops the scroll and what it triggers in the reader", "engagementLevel": "high"}},
      ...
    ],
    "bestExamples": [
      {{"text": "I spent $10,000...", "url": "https://...", "score": 3.2}},
      ...
    ]
  }},
  "ctaStrategy": {{
    "formula": "One punchy, actionable sentence summarizing the CTA formula",
    "patterns": [
      {{"name": "Comment-gated", "description": "Why this drives algorithmic reach AND builds the creator's authority simultaneously", "engagementLevel": "high"}},
      ...
    ],
    "bestExamples": [
      {{"text": "Comment 'YES'...", "url": "https://...", "score": 2.8}},
      ...
    ]
  }},
  "executiveSummary": "3-4 OPINIONATED sentences. Lead with what this creator is doing that most people aren't. Name the strategic moat. Quantify the edge where possible. Do NOT just list what they post — explain the SYSTEM behind it and why it compounds over time.",
  "bigStrategicOpportunity": "2-3 sentences identifying the single biggest untapped opportunity this creator has. Be specific and bold — what's the one move that would 2x their impact? This should feel like advice from a $10k/hr consultant."
}}

Rules:
- Return exactly 3-5 pillars and exactly 3-4 archetypes — no more, no less
- Merge duplicates and synonyms into the strongest version
- Use consistent naming across pillars and archetypes
- Return ONLY valid JSON, no markdown"""

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
            bigStrategicOpportunity="",
        )


async def generate_agent_strategy(
    provider: LLMProvider,
    profile_name: str,
    pillars: List[ContentPillar],
    archetypes: List[PostArchetype],
) -> List[AgentWorkflow]:
    """
    Generate 3 specific AI agent workflows a solo operator could use
    to replicate this profile's content output — one per top pillar.
    """
    pillars_data = [
        {
            "name": p.name,
            "description": p.description,
            "engagementLevel": p.engagementLevel,
            "percentageOfPosts": p.percentageOfPosts,
        }
        for p in pillars[:3]
    ]
    archetypes_data = [
        {"name": a.name, "description": a.description, "engagementLevel": a.engagementLevel}
        for a in archetypes[:3]
    ]

    prompt = f"""You are designing AI agent workflows for a solo operator who wants to replicate {profile_name}'s LinkedIn content machine using AI.

The creator's top content pillars:
{json.dumps(pillars_data, ensure_ascii=False, indent=2)}

Their top post archetypes:
{json.dumps(archetypes_data, ensure_ascii=False, indent=2)}

Prioritize the pillars with the highest engagementLevel and percentageOfPosts — those are where this creator already has proven leverage.

Design exactly 3 AI agent workflows — one per pillar. Each workflow is a specific, buildable agentic system.

Return ONLY a JSON array:
[
  {{
    "name": "Short memorable agent name (e.g. 'Trend Radar Agent')",
    "pillar": "The content pillar this agent serves",
    "archetype": "The post format/archetype this agent generates",
    "description": "2-3 sentences: What this agent does, what inputs it takes, what it outputs, and WHY it creates 10x leverage for a solo operator. Be specific and concrete — reference the pillar and archetype.",
    "prompt_skeleton": "A 3-5 line starter system prompt or workflow outline a builder could use to create this agent. Make it immediately actionable."
  }},
  ...
]

Rules:
- Each agent must map to a DIFFERENT pillar
- Make the agents feel like real products a founder would pay for
- The prompt_skeleton should be copy-paste ready, not just a description
- Return ONLY valid JSON array, no markdown"""

    raw = await provider.generate(prompt)
    try:
        data = extract_json(raw)
        if not isinstance(data, list):
            raise ValueError("Expected JSON array")
        workflows = []
        for item in data:
            if isinstance(item, dict):
                workflows.append(
                    AgentWorkflow(
                        name=str(item.get("name", "Agent")),
                        pillar=str(item.get("pillar", "")),
                        archetype=str(item.get("archetype", "")),
                        description=str(item.get("description", "")),
                        prompt_skeleton=str(item.get("prompt_skeleton", "")),
                    )
                )
        return workflows[:3]
    except Exception:
        return []


async def generate_steal_this_hooks(
    provider: LLMProvider,
    profile_name: str,
    archetypes: List[PostArchetype],
    hook_strategy: HookStrategy,
    top_posts_context: str,
) -> List[StealThisHook]:
    """
    Generate 5 pre-written LinkedIn hooks tailored to this profile's
    best-performing archetypes — ready to copy, paste, and publish.
    """
    archetypes_data = [
        {"name": a.name, "description": a.description, "engagementLevel": a.engagementLevel}
        for a in archetypes[:3]
    ]

    prompt = f"""You are a world-class LinkedIn ghostwriter. Your job is to write 5 ready-to-publish hook lines tailored to {profile_name}'s content style and best-performing post archetypes.

Their top archetypes:
{json.dumps(archetypes_data, ensure_ascii=False, indent=2)}

Their winning hook formula:
{hook_strategy.formula}

Top performing post hooks for reference:
{top_posts_context}

Write exactly 5 hooks. Each hook must:
- Be a single punchy line (max 15 words) that stops the scroll
- Be specific to one of their archetypes — not generic
- Feel like it belongs in THIS creator's voice
- Create immediate curiosity or tension

Return ONLY a JSON array:
[
  {{
    "hook": "The ready-to-use hook line",
    "archetype": "Which archetype from their list this is modeled on",
    "why_it_works": "One sentence naming exactly one trigger (curiosity gap / loss aversion / social proof / authority / urgency / pain) and explaining how this hook activates it"
  }},
  ...
]

Return ONLY valid JSON array, no markdown."""

    raw = await provider.generate(prompt)
    try:
        data = extract_json(raw)
        if not isinstance(data, list):
            raise ValueError("Expected JSON array")
        hooks = []
        for item in data:
            if isinstance(item, dict):
                hooks.append(
                    StealThisHook(
                        hook=str(item.get("hook", "")),
                        archetype=str(item.get("archetype", "")),
                        why_it_works=str(item.get("why_it_works", "")),
                    )
                )
        return hooks[:5]
    except Exception:
        return []


