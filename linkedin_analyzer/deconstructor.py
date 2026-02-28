"""
Single-post viral deconstructor.
Answers: "Why did this specific post perform so well?"
"""

from datetime import datetime, timezone
from typing import Optional

from .scraper import extract
from .cleaner import clean_apify_posts
from .metrics import (
    extract_hook_text,
    classify_hook_type,
    extract_cta_text,
    classify_cta_type,
)
from .ai_insights import get_provider, extract_json, clean_for_llm
from .types import PostDeconstruction, PostDeconstructionAI


async def _ai_deconstruct(
    text: str,
    post_type: str,
    num_likes: int,
    num_comments: int,
    num_shares: int,
    hook: str,
    cta: str,
) -> Optional[PostDeconstructionAI]:
    provider = get_provider()
    if provider is None:
        return None

    clean_text = clean_for_llm(text)

    prompt = f"""You are a LinkedIn content strategist. Deconstruct why this post performed well.

POST STATS:
- Type: {post_type}
- Likes: {num_likes}
- Comments: {num_comments}
- Shares: {num_shares}

HOOK (opening):
{hook}

CTA (closing):
{cta}

FULL POST:
{clean_text}

Return ONLY a JSON object:
{{
  "whyItWorked": "2-3 sentences explaining the core reasons this post outperformed. Be specific to the actual content.",
  "contentPillar": "The main content theme (e.g. Founder Lessons, AI Automation, Career Advice)",
  "archetype": "The post format/structure (e.g. Personal Story, Tactical List, Contrarian Take, Behind-the-Scenes)",
  "hookFormula": "The reusable hook pattern as a template (e.g. 'I [did X] and learned [insight]')",
  "ctaFormula": "The reusable CTA pattern as a template (e.g. 'Ask reflective question + invite comment')",
  "replicationGuide": [
    "Step 1: ...",
    "Step 2: ...",
    "Step 3: ...",
    "Step 4: ..."
  ]
}}

Be specific and actionable. Return ONLY valid JSON."""

    raw = await provider.generate(prompt)
    try:
        data = extract_json(raw)
        return PostDeconstructionAI(
            whyItWorked=str(data.get("whyItWorked", "Analysis unavailable")),
            contentPillar=str(data.get("contentPillar", "General")),
            archetype=str(data.get("archetype", "General")),
            hookFormula=str(data.get("hookFormula", "Analysis unavailable")),
            ctaFormula=str(data.get("ctaFormula", "Analysis unavailable")),
            replicationGuide=list(data.get("replicationGuide", [])),
        )
    except Exception:
        return None


async def deconstruct_post(
    post_url: str,
    skip_ai: bool = False,
    limit_per_source: Optional[int] = None,
    deep_scrape: bool = True,
) -> PostDeconstruction:
    # Scrape the single post URL
    raw = extract(
        post_url,
        limit_per_source=limit_per_source or 1,
        deep_scrape=deep_scrape,
    )

    posts_raw = raw.get("posts", [])
    if not posts_raw:
        raise ValueError(f"No post data returned for URL: {post_url}")

    # Clean posts — use the first post (the target post)
    posts = clean_apify_posts(posts_raw, limit=1)
    if not posts:
        raise ValueError("Could not parse post data from scraper response.")

    post = posts[0]

    # Deterministic analysis
    hook = extract_hook_text(post.text)
    hook_type = classify_hook_type(hook)
    hook_length = len(hook.split())

    cta = extract_cta_text(post.text)
    cta_type = classify_cta_type(cta)

    # AI analysis
    ai_result: Optional[PostDeconstructionAI] = None
    if not skip_ai:
        ai_result = await _ai_deconstruct(
            text=post.text,
            post_type=post.type,
            num_likes=post.numLikes,
            num_comments=post.numComments,
            num_shares=post.numShares,
            hook=hook,
            cta=cta,
        )

    return PostDeconstruction(
        postUrl=post.url or post_url,
        authorName=post.authorName,
        authorHeadline=post.authorHeadline,
        analyzedAt=datetime.now(timezone.utc).isoformat(),
        type=post.type,
        text=post.text,
        numLikes=post.numLikes,
        numComments=post.numComments,
        numShares=post.numShares,
        postedAtISO=post.postedAtISO,
        hook=hook,
        hookType=hook_type,
        hookLength=hook_length,
        cta=cta,
        ctaType=cta_type,
        ai=ai_result,
    )
