import re
from typing import List, Dict, Any

from .types import Candidate


# Titles that indicate the person is not a real candidate (intern, recruiter, etc.)
_EXCLUDE_TITLE_PATTERNS = [
    r"\bintern\b",
    r"\brecruit(er|ing|ment)?\b",
    r"\btalent acquisition\b",
    r"\bhr\b",
    r"\bhuman resources\b",
    r"\bpeople ops\b",
    r"\bstaffing\b",
    r"\bhead hunter\b",
    r"\bhead-hunter\b",
]

_EXCLUDE_RE = re.compile("|".join(_EXCLUDE_TITLE_PATTERNS), re.IGNORECASE)


def _is_relevant(raw: Dict[str, Any], target_title: str) -> bool:
    """Return True if the candidate should be kept."""
    title = str(raw.get("title") or "").strip()
    if not title:
        return False

    # Filter out noise roles
    if _EXCLUDE_RE.search(title):
        return False

    return True


def clean_candidates(
    raw_list: List[Dict[str, Any]],
    target_title: str,
    limit: int = 200,
) -> List[Candidate]:
    """
    Validate, filter, and normalize raw Apify candidate dicts into Candidate models.
    """
    cleaned: List[Candidate] = []

    for raw in raw_list:
        if not _is_relevant(raw, target_title):
            continue

        profile_url = str(raw.get("profileUrl") or raw.get("linkedinUrl") or "").strip()
        if not profile_url:
            continue  # No profile URL = not actionable

        cleaned.append(
            Candidate(
                name=str(raw.get("name") or "LinkedIn Member").strip(),
                title=str(raw.get("title") or "").strip(),
                location=str(raw.get("location") or "").strip(),
                profileUrl=profile_url,
                avatarUrl=str(raw.get("avatarUrl") or "").strip(),
                summary=str(raw.get("summary") or "").strip(),
            )
        )

        if len(cleaned) >= limit:
            break

    return cleaned
