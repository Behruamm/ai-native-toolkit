import pytest
from linkedin_analyzer.cleaner import clean_apify_posts


def test_clean_apify_posts_empty():
    assert clean_apify_posts([]) == []


def test_clean_apify_posts_basic():
    raw_data = [
        {
            "type": "linkedinVideo",
            "text": "Hello world",
            "numLikes": 10,
            "numComments": 2,
            "numShares": 1,
            "postedAtTimestamp": 123456789,
            "postedAtISO": "2023-01-01T00:00:00.000Z",
            "authorName": "Test User",
            "author": {"occupation": "Engineer"},
            "comments": [{"text": "Nice", "time": 123}, {"text": "Cool", "time": 124}],
        }
    ]

    cleaned = clean_apify_posts(raw_data)

    assert len(cleaned) == 1
    post = cleaned[0]

    assert post.type == "video"  # Normalized
    assert post.text == "Hello world"
    assert post.numLikes == 10
    assert post.authorHeadline == "Engineer"
    assert len(post.comments) == 2
    assert post.comments[0].text == "Nice"


def test_clean_apify_posts_limit():
    raw_data = [{"text": f"Post {i}"} for i in range(100)]
    cleaned = clean_apify_posts(raw_data, limit=50)
    assert len(cleaned) == 50
