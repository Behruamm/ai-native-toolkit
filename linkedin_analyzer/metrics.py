import math
import re
from typing import List, Dict, Any, Tuple
from datetime import datetime, timezone

from .types import (
    CleanPost,
    CadenceMetrics,
    EngagementMetrics,
    PostTypeStats,
    ScheduleMetrics,
    ScoredPost,
    TextPatternMetrics,
    CommentAnalysis,
    HookAnalysis,
    HookTypeBreakdown,
    CTAAnalysis,
    CTATypeBreakdown,
    WordFrequency,
    WordCount,
)

# ============================================================
# Helpers
# ============================================================


def median(arr: List[float]) -> float:
    if not arr:
        return 0.0
    sorted_arr = sorted(arr)
    n = len(sorted_arr)
    mid = n // 2
    if n % 2 != 0:
        return float(sorted_arr[mid])
    else:
        return float(round((sorted_arr[mid - 1] + sorted_arr[mid]) / 2.0))


def mean(arr: List[float]) -> float:
    return float(sum(arr) / len(arr)) if arr else 0.0


def stddev(arr: List[float]) -> float:
    if len(arr) < 2:
        return 0.0
    m = mean(arr)
    variance = sum((x - m) ** 2 for x in arr) / len(arr)
    return math.sqrt(variance)


def zscore(value: float, m: float, s: float) -> float:
    if s <= 0:
        return 0.0
    return (value - m) / s


def round1(n: float) -> float:
    return round(n * 10.0) / 10.0


DAYS = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]

# ============================================================
# 1.1 Content Cadence
# ============================================================


def compute_cadence(posts: List[CleanPost]) -> CadenceMetrics:
    if not posts:
        return CadenceMetrics(
            totalPosts=0,
            periodStart="",
            periodEnd="",
            weeksCovered=0,
            postsPerWeek=0.0,
            avgDaysBetweenPosts=0.0,
        )

    timestamps = sorted([p.postedAtTimestamp for p in posts if p.postedAtTimestamp > 0])

    if not timestamps:
        return CadenceMetrics(
            totalPosts=len(posts),
            periodStart="",
            periodEnd="",
            weeksCovered=0,
            postsPerWeek=0.0,
            avgDaysBetweenPosts=0.0,
        )

    oldest = timestamps[0]
    newest = timestamps[-1]
    ms_span = newest - oldest
    weeks_covered = round1(ms_span / (7 * 24 * 60 * 60 * 1000))

    # Avg gap between consecutive posts
    total_gap = 0
    for i in range(1, len(timestamps)):
        total_gap += timestamps[i] - timestamps[i - 1]

    avg_gap_ms = total_gap / (len(timestamps) - 1) if len(timestamps) > 1 else 0
    avg_days_between_posts = round1(avg_gap_ms / (24 * 60 * 60 * 1000))

    return CadenceMetrics(
        totalPosts=len(posts),
        periodStart=datetime.fromtimestamp(oldest / 1000.0, tz=timezone.utc).strftime(
            "%Y-%m-%d"
        ),
        periodEnd=datetime.fromtimestamp(newest / 1000.0, tz=timezone.utc).strftime(
            "%Y-%m-%d"
        ),
        weeksCovered=int(math.ceil(weeks_covered)),
        postsPerWeek=round1(len(posts) / weeks_covered) if weeks_covered > 0 else 0.0,
        avgDaysBetweenPosts=avg_days_between_posts,
    )


# ============================================================
# 1.2 Engagement Metrics
# ============================================================


def compute_engagement(posts: List[CleanPost]) -> EngagementMetrics:
    if not posts:
        return EngagementMetrics(
            totalReactions=0,
            totalComments=0,
            totalReposts=0,
            avgReactions=0.0,
            avgComments=0.0,
            avgReposts=0.0,
            medianReactions=0.0,
            medianComments=0.0,
        )

    likes = [float(p.numLikes) for p in posts]
    comments = [float(p.numComments) for p in posts]
    shares = [float(p.numShares) for p in posts]

    total_reactions = int(sum(likes))
    total_comments = int(sum(comments))
    total_reposts = int(sum(shares))
    count = len(posts)

    return EngagementMetrics(
        totalReactions=total_reactions,
        totalComments=total_comments,
        totalReposts=total_reposts,
        avgReactions=round(total_reactions / count),
        avgComments=round(total_comments / count),
        avgReposts=round(total_reposts / count),
        medianReactions=median(likes),
        medianComments=median(comments),
    )


# ============================================================
# 1.3 Post Type Breakdown
# ============================================================


def compute_post_types(posts: List[CleanPost]) -> List[PostTypeStats]:
    if not posts:
        return []

    groups = {}
    for p in posts:
        if p.type not in groups:
            groups[p.type] = {"count": 0, "totalLikes": 0, "totalComments": 0}
        groups[p.type]["count"] += 1
        groups[p.type]["totalLikes"] += p.numLikes
        groups[p.type]["totalComments"] += p.numComments

    stats = []
    total_posts = len(posts)
    for p_type, g in groups.items():
        stats.append(
            PostTypeStats(
                type=p_type,
                count=g["count"],
                percentage=round((g["count"] / total_posts) * 100),
                avgReactions=round(g["totalLikes"] / g["count"]),
                avgComments=round(g["totalComments"] / g["count"]),
            )
        )

    return sorted(stats, key=lambda x: x.count, reverse=True)


# ============================================================
# 1.4 Posting Schedule
# ============================================================


def compute_schedule(posts: List[CleanPost]) -> ScheduleMetrics:
    posts_by_day = {}
    posts_by_hour = {}
    engagement_by_day = {}
    engagement_by_hour = {}

    for p in posts:
        if p.postedAtTimestamp <= 0:
            continue

        dt = datetime.fromtimestamp(p.postedAtTimestamp / 1000.0, tz=timezone.utc)
        day = DAYS[dt.weekday()]
        hour = dt.hour

        posts_by_day[day] = posts_by_day.get(day, 0) + 1
        posts_by_hour[hour] = posts_by_hour.get(hour, 0) + 1

        if day not in engagement_by_day:
            engagement_by_day[day] = {"total": 0, "count": 0}
        engagement_by_day[day]["total"] += p.numLikes
        engagement_by_day[day]["count"] += 1

        if hour not in engagement_by_hour:
            engagement_by_hour[hour] = {"total": 0, "count": 0}
        engagement_by_hour[hour]["total"] += p.numLikes
        engagement_by_hour[hour]["count"] += 1

    best_day = (
        max(posts_by_day.items(), key=lambda x: x[1])[0] if posts_by_day else "N/A"
    )
    best_hour = (
        max(posts_by_hour.items(), key=lambda x: x[1])[0] if posts_by_hour else 0
    )

    highest_eng_day = "N/A"
    if engagement_by_day:
        highest_eng_day = max(
            engagement_by_day.keys(),
            key=lambda d: engagement_by_day[d]["total"] / engagement_by_day[d]["count"],
        )

    highest_eng_hour = 0
    if engagement_by_hour:
        highest_eng_hour = max(
            engagement_by_hour.keys(),
            key=lambda h: engagement_by_hour[h]["total"]
            / engagement_by_hour[h]["count"],
        )

    return ScheduleMetrics(
        postsByDay=posts_by_day,
        postsByHour=posts_by_hour,
        bestDay=best_day,
        bestHour=best_hour,
        highestEngagementDay=highest_eng_day,
        highestEngagementHour=highest_eng_hour,
    )


# ============================================================
# 1.5 Engagement Scoring & Ranking
# ============================================================


def score_and_rank_posts(
    posts: List[CleanPost],
) -> Tuple[List[ScoredPost], List[ScoredPost]]:
    if not posts:
        return [], []

    likes = [float(p.numLikes) for p in posts]
    comments = [float(p.numComments) for p in posts]
    shares = [float(p.numShares) for p in posts]

    like_mean = mean(likes)
    comment_mean = mean(comments)
    share_mean = mean(shares)

    like_std = stddev(likes)
    comment_std = stddev(comments)
    share_std = stddev(shares)

    now_ms = datetime.now(timezone.utc).timestamp() * 1000.0
    ms_per_day = 24 * 60 * 60 * 1000.0

    like_rates = []
    comment_rates = []
    share_rates = []
    rate_by_index = {}

    for i, p in enumerate(posts):
        if p.postedAtTimestamp <= 0:
            print(f"[Metrics] WARNING: Invalid timestamp (<=0) for post index {i}, using default age")
            age_days = 1.0
        elif float(p.postedAtTimestamp) > now_ms:
            print(f"[Metrics] WARNING: Future timestamp detected for post index {i}, using default age")
            age_days = 1.0
        else:
            age_days = max((now_ms - float(p.postedAtTimestamp)) / ms_per_day, 1.0)
        like_rate = p.numLikes / age_days
        comment_rate = p.numComments / age_days
        share_rate = p.numShares / age_days

        like_rates.append(like_rate)
        comment_rates.append(comment_rate)
        share_rates.append(share_rate)
        rate_by_index[i] = (like_rate, comment_rate, share_rate)

    like_rate_mean = mean(like_rates)
    comment_rate_mean = mean(comment_rates)
    share_rate_mean = mean(share_rates)

    like_rate_std = stddev(like_rates)
    comment_rate_std = stddev(comment_rates)
    share_rate_std = stddev(share_rates)

    scored: List[ScoredPost] = []
    for i, p in enumerate(posts):
        like_rate, comment_rate, share_rate = rate_by_index[i]

        norm_score = (
            zscore(float(p.numLikes), like_mean, like_std)
            + zscore(float(p.numComments), comment_mean, comment_std)
            + zscore(float(p.numShares), share_mean, share_std)
        )
        age_score = (
            zscore(float(like_rate), like_rate_mean, like_rate_std)
            + zscore(float(comment_rate), comment_rate_mean, comment_rate_std)
            + zscore(float(share_rate), share_rate_mean, share_rate_std)
        )

        scored.append(
            ScoredPost(
                index=i,
                text=p.text,
                type=p.type,
                numLikes=p.numLikes,
                numComments=p.numComments,
                numShares=p.numShares,
                postedAtISO=p.postedAtISO,
                engagementScore=norm_score,
                ageAdjustedScore=age_score,
                rank=0,
                ageAdjustedRank=0,
                url=p.url,
            )
        )

    by_norm = sorted(scored, key=lambda x: x.engagementScore, reverse=True)
    for i, p in enumerate(by_norm):
        p.rank = i + 1

    by_age = sorted(scored, key=lambda x: x.ageAdjustedScore, reverse=True)
    for i, p in enumerate(by_age):
        p.ageAdjustedRank = i + 1

    return by_norm, by_age


# ============================================================
# 1.6 Text Pattern Analysis
# ============================================================

CTA_REGEX = re.compile(
    r"\b(comment|repost|share|follow|link in|DM|message me|tag someone|drop a)\b",
    re.IGNORECASE,
)
LIST_REGEX = re.compile(r"^[→•\-\d]+\.?\s", re.MULTILINE)
QUESTION_REGEX = re.compile(r"\?")
URL_REGEX = re.compile(r"https?://\S+", re.IGNORECASE)
HASHTAG_LINE = re.compile(r"^\s*#")

HOOK_CHAR_LIMIT = 200
HOOK_MAX_LINES = 3
CTA_MIN_SENTENCE_LEN = 30


def extract_hook_text(text: str) -> str:
    if not text:
        return ""
    lines = [line.rstrip() for line in text.splitlines()]
    snippet = "\n".join(lines[:HOOK_MAX_LINES]).strip() if lines else text.strip()
    if len(snippet) > HOOK_CHAR_LIMIT:
        snippet = snippet[:HOOK_CHAR_LIMIT].rstrip()
    return snippet


def remove_trailing_hashtags(text: str) -> str:
    lines = text.splitlines()
    while lines and (HASHTAG_LINE.match(lines[-1]) or not lines[-1].strip()):
        lines.pop()
    return "\n".join(lines).strip()


def extract_cta_text(text: str) -> str:
    if not text:
        return ""
    cleaned = URL_REGEX.sub("", text)
    cleaned = remove_trailing_hashtags(cleaned)
    sentences = re.split(r"(?<=[.!?])\s+|\n+", cleaned.strip())
    sentences = [s.strip() for s in sentences if s.strip()]
    if not sentences:
        return ""
    last = sentences[-1]
    if len(last) < CTA_MIN_SENTENCE_LEN and len(sentences) >= 2:
        last = f"{sentences[-2]} {last}".strip()
    return last


def has_hook(text: str) -> bool:
    return bool(extract_hook_text(text))


def compute_text_patterns(posts: List[CleanPost]) -> TextPatternMetrics:
    if not posts:
        return TextPatternMetrics(
            avgWordCount=0,
            avgLineCount=0,
            postsWithCTA=0,
            postsWithQuestions=0,
            postsWithLists=0,
            postsWithHook=0,
            ctaEngagementLift=0,
        )

    total_words = 0
    total_lines = 0
    with_cta = 0
    with_question = 0
    with_list = 0
    with_hook = 0

    cta_eng = 0
    cta_count = 0
    non_cta_eng = 0
    non_cta_count = 0

    for p in posts:
        words = len([w for w in re.split(r"\s+", p.text) if w])
        lines = len(p.text.split("\n"))
        total_words += words
        total_lines += lines

        cta_text = extract_cta_text(p.text)
        has_cta = bool(CTA_REGEX.search(cta_text))
        if has_cta:
            with_cta += 1
            cta_eng += p.numLikes + p.numComments
            cta_count += 1
        else:
            non_cta_eng += p.numLikes + p.numComments
            non_cta_count += 1

        if QUESTION_REGEX.search(p.text):
            with_question += 1
        if LIST_REGEX.search(p.text):
            with_list += 1
        if has_hook(p.text):
            with_hook += 1

    avg_cta_eng = cta_eng / cta_count if cta_count > 0 else 0
    avg_non_cta_eng = non_cta_eng / non_cta_count if non_cta_count > 0 else 0
    cta_lift = (
        round(((avg_cta_eng - avg_non_cta_eng) / avg_non_cta_eng) * 100)
        if avg_non_cta_eng > 0
        else 0
    )

    return TextPatternMetrics(
        avgWordCount=round(total_words / len(posts)),
        avgLineCount=round(total_lines / len(posts)),
        postsWithCTA=with_cta,
        postsWithQuestions=with_question,
        postsWithLists=with_list,
        postsWithHook=with_hook,
        ctaEngagementLift=float(cta_lift),
    )


# ============================================================
# Section 4: Comment Analysis
# ============================================================


def analyze_comments(posts: List[CleanPost]) -> CommentAnalysis:
    # Comment text from Apify is sampled and incomplete; avoid semantic analysis.
    return CommentAnalysis(
        avgCommentLength=0.0,
        spamRatio=0.0,
        genuineRatio=0.0,
        topCommenters=[],
        available=False,
        note="Comment text is sampled and incomplete; semantic analysis disabled.",
    )


# ============================================================
# 5: Word Frequency (NLP — stopwords removed)
# ============================================================

STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "but",
    "in",
    "on",
    "at",
    "to",
    "for",
    "of",
    "with",
    "that",
    "this",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "have",
    "has",
    "had",
    "do",
    "does",
    "did",
    "will",
    "would",
    "could",
    "should",
    "may",
    "might",
    "i",
    "you",
    "he",
    "she",
    "it",
    "we",
    "they",
    "my",
    "your",
    "our",
    "their",
    "its",
    "me",
    "him",
    "her",
    "us",
    "them",
    "what",
    "how",
    "when",
    "where",
    "who",
    "which",
    "if",
    "as",
    "so",
    "by",
    "from",
    "up",
    "about",
    "into",
    "than",
    "then",
    "just",
    "more",
    "also",
    "can",
    "all",
    "not",
    "no",
    "there",
    "here",
    "get",
    "got",
    "like",
    "even",
    "out",
    "one",
    "now",
    "want",
    "need",
    "new",
    "make",
    "made",
    "know",
}


def compute_word_frequency(posts: List[CleanPost]) -> List[WordFrequency]:
    freq = {}
    for p in posts:
        text = re.sub(r"[^a-z0-9\s]", " ", p.text.lower())
        words = [w for w in re.split(r"\s+", text) if len(w) > 2 and w not in STOPWORDS]
        for w in words:
            freq[w] = freq.get(w, 0) + 1

    sorted_freq = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:25]
    return [WordFrequency(word=w, count=c) for w, c in sorted_freq]


# ============================================================
# 6: Hook Analysis
# ============================================================

URGENCY_WORDS = re.compile(
    r"\b(today|now|stop|never|always|mistake|warning|urgent|immediately|right now|breaking|instantly)\b",
    re.IGNORECASE,
)


def classify_hook_type(hook: str) -> str:
    if "?" in hook:
        return "Question"

    # Needs re module to simulate TS behaviour properly
    if re.search(r"^\d+[\s\.\:]", hook.lstrip()) or re.search(
        r"\b\d+\s+(ways|tips|reasons|steps|mistakes|things)\b", hook, re.IGNORECASE
    ):
        return "Number/List"

    if re.search(r"\b(i |my |we )\b", hook, re.IGNORECASE) and re.search(
        r"\b(learned|realized|discovered|made|built|failed|quit|left)\b",
        hook,
        re.IGNORECASE,
    ):
        return "Story"

    if URGENCY_WORDS.search(hook) or re.search(
        r"\b(unpopular opinion|hot take|controversial|most people|everyone|nobody)\b",
        hook,
        re.IGNORECASE,
    ):
        return "Provocative"

    return "Statement"


def analyze_hooks(posts: List[CleanPost]) -> HookAnalysis:
    if not posts:
        return HookAnalysis(
            avgHookLength=0,
            hookTypes=[],
            urgencyRate=0,
            topFirstWords=[],
            topHookWords=[],
        )

    hooks = []
    for p in posts:
        hook_text = extract_hook_text(p.text)
        hooks.append({"hook": hook_text, "post": p})

    # Avg hook length
    total_words = sum(len([w for w in re.split(r"\s+", h["hook"]) if w]) for h in hooks)
    avg_hook_length = round(total_words / len(hooks)) if hooks else 0

    # Hook type breakdown
    type_map = {}
    for h in hooks:
        t = classify_hook_type(h["hook"])
        if t not in type_map:
            type_map[t] = {"count": 0, "totalReactions": 0}
        type_map[t]["count"] += 1
        type_map[t]["totalReactions"] += h["post"].numLikes

    hook_types = []
    for t, v in type_map.items():
        hook_types.append(
            HookTypeBreakdown(
                type=t,  # type: ignore
                count=v["count"],
                percentage=round((v["count"] / len(hooks)) * 100),
                avgReactions=round(v["totalReactions"] / v["count"]),
            )
        )
    hook_types.sort(key=lambda x: x.count, reverse=True)

    # Urgency rate
    urgency_count = sum(1 for h in hooks if URGENCY_WORDS.search(h["hook"]))
    urgency_rate = round((urgency_count / len(hooks)) * 100) if hooks else 0

    # Top first words
    first_word_map = {}
    for h in hooks:
        words = re.split(r"\s+", h["hook"])
        fw = re.sub(r"[^a-z]", "", words[0].lower()) if words else ""
        if fw:
            first_word_map[fw] = first_word_map.get(fw, 0) + 1

    top_fw = sorted(first_word_map.items(), key=lambda x: x[1], reverse=True)[:10]
    top_first_words = [WordCount(word=w, count=c) for w, c in top_fw]

    # Top hook words
    hook_word_map = {}
    for h in hooks:
        words = [
            w
            for w in re.split(r"\s+", re.sub(r"[^a-z0-9\s]", " ", h["hook"].lower()))
            if len(w) > 2 and w not in STOPWORDS
        ]
        for w in words:
            hook_word_map[w] = hook_word_map.get(w, 0) + 1

    top_hw = sorted(hook_word_map.items(), key=lambda x: x[1], reverse=True)[:10]
    top_hook_words = [WordCount(word=w, count=c) for w, c in top_hw]

    return HookAnalysis(
        avgHookLength=avg_hook_length,
        hookTypes=hook_types,
        urgencyRate=urgency_rate,
        topFirstWords=top_first_words,
        topHookWords=top_hook_words,
    )


# ============================================================
# 7: CTA Analysis
# ============================================================

CTA_PATTERNS = [
    (
        "Comment-gated",
        re.compile(
            r"\b(comment|drop a|type|reply)\b.*\b(below|yes|1|get|access|send)\b",
            re.IGNORECASE,
        ),
    ),
    ("Comment-gated", re.compile(r"\b(want|interested)\b.*\bcomment\b", re.IGNORECASE)),
    ("Follow", re.compile(r"\b(follow|hit follow|click follow)\b", re.IGNORECASE)),
    (
        "DM",
        re.compile(r"\b(DM|message me|send me a message|slide into)\b", re.IGNORECASE),
    ),
    ("Save/Share", re.compile(r"\b(save|bookmark|repost|share this)\b", re.IGNORECASE)),
    (
        "Link",
        re.compile(
            r"\b(link in (bio|comments)|click the link|check the link)\b", re.IGNORECASE
        ),
    ),
]


def classify_cta_type(cta_text: str) -> str:
    last_chunk = cta_text or ""
    for ctype, pattern in CTA_PATTERNS:
        if pattern.search(last_chunk):
            return ctype

    # Also check old CTA_REGEX
    if re.search(
        r"\b(comment|repost|share|follow|link in|DM|message me|tag someone|drop a)\b",
        last_chunk,
        re.IGNORECASE,
    ):
        if re.search(r"comment", last_chunk, re.IGNORECASE):
            return "Comment-gated"
        if re.search(r"follow", last_chunk, re.IGNORECASE):
            return "Follow"
        if re.search(r"DM|message", last_chunk, re.IGNORECASE):
            return "DM"
        if re.search(r"repost|share", last_chunk, re.IGNORECASE):
            return "Save/Share"

    return "None"


def analyze_ctas(posts: List[CleanPost]) -> CTAAnalysis:
    if not posts:
        return CTAAnalysis(
            ctaTypes=[], topActionWords=[], bestCTAType="None", noCTARate=0.0
        )

    type_map = {}
    for p in posts:
        cta_text = extract_cta_text(p.text)
        t = classify_cta_type(cta_text)
        if t not in type_map:
            type_map[t] = {"count": 0, "totalReactions": 0}
        type_map[t]["count"] += 1
        type_map[t]["totalReactions"] += p.numLikes

    cta_types = []
    for t, v in type_map.items():
        cta_types.append(
            CTATypeBreakdown(
                type=t,  # type: ignore
                count=v["count"],
                percentage=round((v["count"] / len(posts)) * 100),
                avgReactions=round(v["totalReactions"] / v["count"]),
            )
        )
    cta_types.sort(key=lambda x: x.avgReactions, reverse=True)

    # Top action words in last 300 chars of each post
    ACTION_WORDS = [
        "comment",
        "follow",
        "dm",
        "save",
        "share",
        "repost",
        "click",
        "link",
        "join",
        "download",
        "grab",
        "get",
        "drop",
        "type",
        "reply",
        "tag",
        "send",
        "check",
        "access",
    ]
    action_word_map = {}
    for p in posts:
        chunk = extract_cta_text(p.text).lower()
        for w in ACTION_WORDS:
            if w in chunk:
                action_word_map[w] = action_word_map.get(w, 0) + 1

    top_aw = sorted(action_word_map.items(), key=lambda x: x[1], reverse=True)[:8]
    top_action_words = [WordCount(word=w, count=c) for w, c in top_aw]

    none_count = type_map.get("None", {}).get("count", 0)
    no_cta_rate = round((none_count / len(posts)) * 100) if posts else 0.0

    best_cta_type = "None"
    for t in cta_types:
        if t.type != "None":
            best_cta_type = t.type
            break

    return CTAAnalysis(
        ctaTypes=cta_types,
        topActionWords=top_action_words,
        bestCTAType=best_cta_type,
        noCTARate=float(no_cta_rate),
    )


def compute_all_metrics(posts: List[CleanPost]) -> Dict[str, Any]:
    scored_posts, scored_posts_age = score_and_rank_posts(posts)
    return {
        "cadence": compute_cadence(posts).model_dump(),
        "engagement": compute_engagement(posts).model_dump(),
        "postTypes": [p.model_dump() for p in compute_post_types(posts)],
        "schedule": compute_schedule(posts).model_dump(),
        "scoredPosts": [p.model_dump() for p in scored_posts],
        "scoredPostsAgeAdjusted": [p.model_dump() for p in scored_posts_age],
        "textPatterns": compute_text_patterns(posts).model_dump(),
        "commentAnalysis": analyze_comments(posts).model_dump(),
        "wordFrequency": [w.model_dump() for w in compute_word_frequency(posts)],
        "hookAnalysis": analyze_hooks(posts).model_dump(),
        "ctaAnalysis": analyze_ctas(posts).model_dump(),
    }
