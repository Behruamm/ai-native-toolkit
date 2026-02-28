import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
import json

from .scraper import extract
from .cleaner import clean_apify_posts
from .metrics import (
    compute_cadence,
    compute_engagement,
    compute_post_types,
    compute_schedule,
    score_and_rank_posts,
    compute_text_patterns,
    analyze_comments,
    analyze_hooks,
    analyze_ctas,
    compute_word_frequency,
)
from .ai_insights import (
    get_provider,
    chunk_posts,
    analyze_chunk_optimized,
    consolidate_chunk_results,
    generate_agent_strategy,
    generate_steal_this_hooks,
    build_hook_cta_context,
)
from .types import FullAnalysis, HookStrategy, CTAStrategy


async def run_full(
    profile_url: str = "",
    skip_ai: bool = False,
    local_file_json: Optional[str] = None,
    limit_per_source: Optional[int] = None,
    scrape_until: Optional[str] = None,
    deep_scrape: bool = True,
    raw_data: bool = False,
) -> FullAnalysis:
    """
    Orchestrates the entire analysis pipeline.
    If local_file_json is provided, it uses that instead of scraping.
    If skip_ai is True, it fills AI sections with placeholder data.
    """
    print(f"[Analysis] Starting run for {profile_url or local_file_json}")

    # 1. Scrape or Load
    if local_file_json:
        with open(local_file_json, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
            posts_raw = raw_data.get("posts", [])
    else:
        if not profile_url:
            raise ValueError("Must provide either profile_url or local_file_json")
        scraped = extract(
            profile_url,
            limit_per_source=limit_per_source,
            scrape_until=scrape_until,
            deep_scrape=deep_scrape,
            raw_data=raw_data,
        )
        posts_raw = scraped["posts"]

    if not posts_raw:
        raise ValueError("No posts found to analyze")

    # 2. Clean
    raw_count = len(posts_raw)
    posts = clean_apify_posts(posts_raw, limit_per_source or 50)
    if not posts:
        raise ValueError("After cleaning, no valid posts remained")

    # Log truncation warning
    if raw_count > len(posts):
        print(f"[Analysis] WARNING: Analyzing {len(posts)}/{raw_count} posts (truncated to limit)")

    # 3. Deterministic Metrics
    cadence = compute_cadence(posts)
    engagement = compute_engagement(posts)
    post_types = compute_post_types(posts)
    schedule = compute_schedule(posts)
    scored_posts, scored_posts_age = score_and_rank_posts(posts)

    # Validate we have posts to analyze
    if not scored_posts_age:
        raise ValueError("No posts available for scoring and analysis")

    text_patterns = compute_text_patterns(posts)
    comment_analysis = analyze_comments(posts)
    hook_analysis = analyze_hooks(posts)
    cta_analysis = analyze_ctas(posts)
    word_freq = compute_word_frequency(posts)

    # 4. AI Insights (OPTIMIZED APPROACH)
    provider = None if skip_ai else get_provider()

    if provider:
        print(f"[Analysis] Using AI Provider: {provider.__class__.__name__}")

        # PHASE 1: Chunk Analysis (parallel)
        print(f"[Analysis] Analyzing {len(posts)} posts in chunks of 40...")
        chunks = chunk_posts(posts, size=40)
        print(f"[Analysis] Created {len(chunks)} chunks")

        chunk_tasks = [
            analyze_chunk_optimized(provider, chunk, i * 40)
            for i, chunk in enumerate(chunks)
        ]

        try:
            chunk_results = await asyncio.gather(*chunk_tasks, return_exceptions=True)

            # Filter out exceptions
            valid_chunk_results = []
            for i, res in enumerate(chunk_results):
                if isinstance(res, Exception):
                    print(f"[Analysis] WARNING: Chunk {i} failed: {res}")
                else:
                    valid_chunk_results.append(res)

            if not valid_chunk_results:
                raise Exception("All chunk analyses failed")

        except Exception as e:
            print(f"[Analysis] WARNING: Chunk analysis failed: {e}")
            valid_chunk_results = []

        # PHASE 2: Consolidation
        if valid_chunk_results:
            print(f"[Analysis] Consolidating {len(valid_chunk_results)} chunk results...")
            try:
                consolidated = await consolidate_chunk_results(
                    provider, valid_chunk_results, posts, scored_posts_age
                )
                content_pillars = consolidated.pillars
                post_archetypes = consolidated.archetypes
                hook_strategy = consolidated.hookStrategy
                cta_strategy = consolidated.ctaStrategy
                exec_summary = consolidated.executiveSummary
                big_opportunity = consolidated.bigStrategicOpportunity
            except Exception as e:
                print(f"[Analysis] WARNING: Consolidation failed: {e}")
                content_pillars = []
                post_archetypes = []
                hook_strategy = HookStrategy(formula="Analysis failed", patterns=[], bestExamples=[])
                cta_strategy = CTAStrategy(formula="Analysis failed", patterns=[], bestExamples=[])
                exec_summary = "Analysis consolidation failed"
                big_opportunity = ""
        else:
            content_pillars = []
            post_archetypes = []
            hook_strategy = HookStrategy(formula="Analysis failed", patterns=[], bestExamples=[])
            cta_strategy = CTAStrategy(formula="Analysis failed", patterns=[], bestExamples=[])
            exec_summary = "Chunk analysis failed"
            big_opportunity = ""

        # PHASE 3: Agent strategy + steal-this hooks (parallel)
        profile_name_tmp = posts[0].authorName if posts[0].authorName else "this creator"
        top_hooks_ctx = build_hook_cta_context(posts, scored_posts_age, limit=10)

        print("[Analysis] Generating AI-Native Blueprint and Steal-These Hooks...")
        agent_task = generate_agent_strategy(
            provider, profile_name_tmp, content_pillars, post_archetypes
        )
        hooks_task = generate_steal_this_hooks(
            provider, profile_name_tmp, post_archetypes, hook_strategy, top_hooks_ctx
        )
        agent_results = await asyncio.gather(agent_task, hooks_task, return_exceptions=True)

        agent_workflows = agent_results[0] if not isinstance(agent_results[0], Exception) else []
        steal_hooks = agent_results[1] if not isinstance(agent_results[1], Exception) else []
        if isinstance(agent_results[0], Exception):
            print(f"[Analysis] WARNING: Agent strategy failed: {agent_results[0]}")
        if isinstance(agent_results[1], Exception):
            print(f"[Analysis] WARNING: Steal-hooks failed: {agent_results[1]}")

    else:
        # Skip AI — provide placeholders
        print("[Analysis] Skipping AI generation. Using placeholders.")
        content_pillars = []
        exec_summary = "AI analysis skipped via --skip-ai flag."
        big_opportunity = ""
        post_archetypes = []
        hook_strategy = HookStrategy(formula="AI skipped", patterns=[], bestExamples=[])
        cta_strategy = CTAStrategy(formula="AI skipped", patterns=[], bestExamples=[])
        agent_workflows = []
        steal_hooks = []

    # 4. Assemble FullAnalysis
    profile_name = posts[0].authorName if posts[0].authorName else "LinkedIn Creator"
    profile_hl = posts[0].authorHeadline if posts[0].authorHeadline else "Creator"

    top_limit = min(5, len(scored_posts_age))
    top_posts = scored_posts_age[:top_limit]
    worst_posts = sorted(scored_posts_age, key=lambda p: p.ageAdjustedScore)[
        :top_limit
    ]

    analysis = FullAnalysis(
        profileName=profile_name,
        profileHeadline=profile_hl,
        analyzedAt=datetime.utcnow().isoformat() + "Z",
        cadence=cadence,
        engagement=engagement,
        postTypes=post_types,
        schedule=schedule,
        scoredPosts=scored_posts,
        scoredPostsAgeAdjusted=scored_posts_age,
        textPatterns=text_patterns,
        commentAnalysis=comment_analysis,
        executiveSummary=exec_summary,
        bigStrategicOpportunity=big_opportunity,
        contentPillars=content_pillars,
        postArchetypes=post_archetypes,
        topPosts=top_posts,
        worstPosts=worst_posts,
        wordFrequency=word_freq,
        hookAnalysis=hook_analysis,
        ctaAnalysis=cta_analysis,
        hookStrategy=hook_strategy,
        ctaStrategy=cta_strategy,
        agentWorkflows=agent_workflows,
        stealTheseHooks=steal_hooks,
    )

    return analysis
