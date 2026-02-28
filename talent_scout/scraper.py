import os
import time
import httpx
from typing import Dict, Any, List, Optional


APIFY_BASE = "https://api.apify.com/v2"
ACTOR_ID = "harvestapi/linkedin-company-employees"


def _coerce_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_candidate(raw: Dict[str, Any]) -> Dict[str, Any]:
    def pick(*keys: str) -> Any:
        for key in keys:
            if key in raw and raw[key] is not None:
                return raw[key]
        return None

    first = _coerce_str(pick("firstName", "first_name"))
    last = _coerce_str(pick("lastName", "last_name"))
    name = _coerce_str(pick("name", "fullName", "full_name"))
    if not name and (first or last):
        name = f"{first} {last}".strip()
    if not name:
        name = "LinkedIn Member"

    profile_url = _coerce_str(
        pick("linkedinUrl", "profileUrl", "linkedin_url", "url", "profileLink")
    )

    # headline is the job title field for harvestapi/linkedin-company-employees
    title = _coerce_str(
        pick("headline", "title", "jobTitle", "job_title", "occupation", "currentTitle")
    )

    # location is a nested object: {"linkedinText": "...", "parsed": {...}}
    raw_location = pick("location", "geoLocation", "geo_location")
    if isinstance(raw_location, dict):
        location = _coerce_str(
            raw_location.get("linkedinText")
            or raw_location.get("city")
            or raw_location.get("country")
        )
    else:
        location = _coerce_str(raw_location)

    # profilePicture is a nested object: {"url": "...", "sizes": [...]}
    raw_avatar = pick("profilePicture", "avatarUrl", "avatar_url", "profileImage", "photo")
    if isinstance(raw_avatar, dict):
        avatar = _coerce_str(raw_avatar.get("url"))
    else:
        avatar = _coerce_str(raw_avatar)

    summary = _coerce_str(pick("about", "summary", "description", "bio"))

    return {
        "name": name,
        "firstName": first,
        "lastName": last,
        "title": title,
        "location": location,
        "profileUrl": profile_url,
        "linkedinUrl": profile_url,
        "avatarUrl": avatar,
        "summary": summary,
    }


def scrape_company_people(
    company_url: str,
    target_title: str,
    api_key: Optional[str] = None,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Scrapes LinkedIn company employees via Apify harvestapi/linkedin-company-employees.
    Returns a list of normalized candidate dicts.
    """
    token = api_key or os.environ.get("APIFY_API_KEY")
    if not token:
        raise ValueError("APIFY_API_KEY not configured or passed")

    payload: Dict[str, Any] = {
        "companies": [company_url],
        "jobTitles": [target_title],
        "recentlyChangedJobs": False,
    }
    if limit is not None:
        payload["maxItems"] = limit

    with httpx.Client() as client:
        # 1. Start actor run
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

        # 2. Poll until completion (every 5s, max 180s — people scrape is slower)
        max_wait = 180
        start_time = time.time()

        while status in ("RUNNING", "READY"):
            if time.time() - start_time > max_wait:
                raise TimeoutError("Talent scraping timed out after 3 minutes")

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

        # 3. Fetch dataset
        dataset_id = run_data["defaultDatasetId"]
        items_res = client.get(
            f"{APIFY_BASE}/datasets/{dataset_id}/items",
            params={"token": token, "format": "json"},
            timeout=30.0,
        )

        if items_res.status_code != 200:
            raise RuntimeError("Failed to fetch dataset items")

        raw_items = items_res.json()

        if not raw_items:
            raise ValueError(
                f"No people found at {company_url} for title '{target_title}'"
            )

        return [_normalize_candidate(item) for item in raw_items]
