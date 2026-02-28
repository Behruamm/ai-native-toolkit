import os
import time
from datetime import datetime, timezone
import httpx
from typing import Dict, Any, List, Optional, Union


APIFY_BASE = "https://api.apify.com/v2"
ACTOR_ID = "supreme_coder~linkedin-post"


def _coerce_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def _parse_timestamp(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        ts = float(value)
        if ts > 1e12:
            return int(ts)
        if ts > 1e9:
            return int(ts * 1000)
        return int(ts)
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return int(dt.timestamp() * 1000)
        except Exception:
            return 0
    return 0


def _normalize_post(raw: Dict[str, Any]) -> Dict[str, Any]:
    def pick(*keys: str) -> Any:
        for key in keys:
            if key in raw and raw[key] is not None:
                return raw[key]
        return None

    post_type = pick("type", "postType", "mediaType", "contentType") or "text"
    if post_type == "linkedinVideo":
        post_type = "video"

    author = raw.get("author")
    author_name = (
        pick("authorName", "authorFullName", "name")
        or (author.get("name") if isinstance(author, dict) else None)
        or (author if isinstance(author, str) else None)
        or "LinkedIn User"
    )
    first_name = author.get("firstName") if isinstance(author, dict) else None
    last_name = author.get("lastName") if isinstance(author, dict) else None
    if (first_name or last_name) and author_name == "LinkedIn User":
        author_name = f"{first_name or ''} {last_name or ''}".strip()

    headline = (
        (author.get("headline") if isinstance(author, dict) else None)
        or (author.get("occupation") if isinstance(author, dict) else None)
        or ""
    )

    posted_iso = pick("postedAtISO", "createdAtISO", "dateISO", "postedAt", "date")
    posted_ts = pick(
        "postedAtTimestamp",
        "timestamp",
        "postDateTimestamp",
        "createdAtTimestamp",
        "createdAt",
    )

    return {
        "type": post_type,
        "text": pick("text", "content", "postText", "body", "shareText") or "",
        "numLikes": _coerce_int(
            pick(
                "numLikes",
                "likes",
                "likeCount",
                "likesCount",
                "reactions",
                "reactionsCount",
                "reactionCount",
                "numReactions",
            )
        ),
        "numComments": _coerce_int(
            pick("numComments", "comments", "commentCount", "commentsCount")
        ),
        "numShares": _coerce_int(
            pick("numShares", "shares", "shareCount", "reposts", "repostCount")
        ),
        "postedAtTimestamp": _parse_timestamp(posted_ts or posted_iso),
        "postedAtISO": posted_iso or "",
        "authorName": author_name,
        "author": {
            "firstName": first_name,
            "lastName": last_name,
            "occupation": headline,
        }
        if headline or first_name or last_name
        else None,
        "comments": raw.get("comments") or [],
        "images": raw.get("images") or raw.get("imageUrls") or [],
        "document": raw.get("document"),
        "url": pick("url", "postUrl", "link", "shareUrl") or "",
        "urn": pick("urn", "postUrn") or "",
    }


def _normalize_posts(raw_posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [_normalize_post(p) for p in raw_posts]


def extract(
    profile_url: Union[str, List[str]],
    api_key: str | None = None,
    limit_per_source: Optional[int] = None,
    scrape_until: Optional[str] = None,
    deep_scrape: bool = True,
    raw_data: bool = False,
) -> Dict[str, Any]:
    """
    Scrapes LinkedIn posts via Apify and returns raw post data and profile info.
    """
    token = api_key or os.environ.get("APIFY_API_KEY")
    if not token:
        raise ValueError("APIFY_API_KEY not configured or passed")

    if isinstance(profile_url, str):
        urls = [profile_url]
    else:
        urls = profile_url

    payload: Dict[str, Any] = {
        "urls": urls,
        "deepScrape": deep_scrape,
        "rawData": raw_data,
    }
    if limit_per_source is not None:
        payload["limitPerSource"] = limit_per_source
    if scrape_until:
        payload["scrapeUntil"] = scrape_until

    # 1. Start the actor run
    with httpx.Client() as client:
        run_res = client.post(
            f"{APIFY_BASE}/acts/{ACTOR_ID}/runs",
            params={"token": token},
            json=payload,
            timeout=30.0,
        )

        if run_res.status_code != 201:
            raise RuntimeError(
                f"Failed to start Apify actor: {run_res.status_code} {run_res.text}"
            )

        run_data = run_res.json()["data"]
        run_id = run_data["id"]
        status = run_data["status"]

        # 2. Poll until completion (every 5s, max 120s)
        max_wait = 120
        start_time = time.time()

        while status in ("RUNNING", "READY"):
            if time.time() - start_time > max_wait:
                raise TimeoutError("Scraping timed out")

            time.sleep(5)

            status_res = client.get(
                f"{APIFY_BASE}/actor-runs/{run_id}",
                params={"token": token},
                timeout=10.0,
            )
            status_data = status_res.json()["data"]
            status = status_data["status"]

        if status != "SUCCEEDED":
            raise RuntimeError(f"Scraping failed with status: {status}")

        # 3. Fetch dataset items
        dataset_id = run_data["defaultDatasetId"]
        items_res = client.get(
            f"{APIFY_BASE}/datasets/{dataset_id}/items",
            params={"token": token, "format": "json"},
            timeout=30.0,
        )

        if items_res.status_code != 200:
            raise RuntimeError("Failed to fetch dataset items")

        posts_raw = items_res.json()

        if not posts_raw:
            raise ValueError("No posts found for this profile")

        normalized = _normalize_posts(posts_raw)
        first_post = normalized[0]
        name = first_post.get("authorName") or "LinkedIn User"

        author_data = first_post.get("author", {})
        headline = (
            author_data.get("occupation") if isinstance(author_data, dict) else None
        )
        headline = headline or "LinkedIn Professional"

        return {
            "profileUrl": urls[0] if urls else "",
            "name": name,
            "headline": headline,
            "posts": normalized,
        }
