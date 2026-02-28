from typing import List, Dict, Any
from .types import ApifyPost, CleanPost, CleanComment


def clean_apify_posts(
    raw_posts: List[Dict[str, Any]], limit: int = 50
) -> List[CleanPost]:
    """
    Takes raw Apify output, slices to latest 50 posts,
    strips unnecessary fields (author details, image URLs, reaction arrays).
    """
    # Apify returns newest-first, take the latest `limit` posts
    sliced = raw_posts[:limit]

    cleaned_posts: List[CleanPost] = []

    for raw_post in sliced:
        # Validate against ApifyPost model optionally, but here we just extract safely
        post_type = raw_post.get("type", "text")

        # Normalize video type name
        if post_type == "linkedinVideo":
            post_type = "video"

        comments_data = raw_post.get("comments", [])
        cleaned_comments = []
        for c in comments_data:
            cleaned_comments.append(
                CleanComment(text=c.get("text", ""), time=c.get("time", None))
            )

        author_data = raw_post.get("author", {})
        author_headline = (
            author_data.get("occupation", "") if isinstance(author_data, dict) else ""
        )

        clean_post = CleanPost(
            type=post_type,  # type: ignore
            text=raw_post.get("text", ""),
            numLikes=raw_post.get("numLikes", 0),
            numComments=raw_post.get("numComments", 0),
            numShares=raw_post.get("numShares", 0),
            postedAtTimestamp=raw_post.get("postedAtTimestamp", 0),
            postedAtISO=raw_post.get("postedAtISO", ""),
            authorName=raw_post.get("authorName", ""),
            authorHeadline=author_headline,
            comments=cleaned_comments,
            url=raw_post.get("url", "") or "",
        )
        cleaned_posts.append(clean_post)

    return cleaned_posts
