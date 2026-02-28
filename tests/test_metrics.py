import pytest
from linkedin_analyzer.types import CleanPost, CleanComment
from linkedin_analyzer.metrics import (
    compute_cadence,
    compute_engagement,
    compute_post_types,
    compute_text_patterns,
    analyze_comments,
    analyze_hooks,
)


@pytest.fixture
def sample_posts():
    return [
        CleanPost(
            type="text",
            text="Here are 5 tips for better code.\n\nIt works.",
            numLikes=100,
            numComments=20,
            numShares=5,
            postedAtTimestamp=1672531200000,  # Jan 1 2023
            postedAtISO="2023-01-01T00:00:00Z",
            authorName="Test User",
            authorHeadline="Engineer",
            comments=[CleanComment(text="Great tip!"), CleanComment(text="Thanks")],
        ),
        CleanPost(
            type="video",
            text="Did you know this secret? 🤔\n\nLink in bio to learn more! Drop a comment if you agree.",
            numLikes=500,
            numComments=50,
            numShares=20,
            postedAtTimestamp=1673136000000,  # Jan 8 2023
            postedAtISO="2023-01-08T00:00:00Z",
            authorName="Test User",
            authorHeadline="Engineer",
            comments=[CleanComment(text="Wow so true"), CleanComment(text="yes!!")],
        ),
    ]


def test_compute_cadence(sample_posts):
    metrics = compute_cadence(sample_posts)
    assert metrics.totalPosts == 2
    assert metrics.weeksCovered == 1


def test_compute_engagement(sample_posts):
    metrics = compute_engagement(sample_posts)
    assert metrics.totalReactions == 600
    assert metrics.avgReactions == 300
    assert metrics.medianReactions == 300.0


def test_compute_post_types(sample_posts):
    metrics = compute_post_types(sample_posts)
    assert len(metrics) == 2

    text_stats = next(m for m in metrics if m.type == "text")
    assert text_stats.count == 1
    assert text_stats.percentage == 50.0


def test_compute_text_patterns(sample_posts):
    metrics = compute_text_patterns(sample_posts)
    # Post 1 has list "5 tips", Post 2 has question "?" and CTA "Drop a comment"
    assert metrics.postsWithCTA == 1
    assert metrics.postsWithQuestions == 1
    assert metrics.avgLineCount == 3.0


def test_analyze_comments(sample_posts):
    metrics = analyze_comments(sample_posts)
    # Comment analysis is intentionally disabled (returns placeholders)
    assert metrics.available == False
    assert "sampled and incomplete" in metrics.note


def test_analyze_hooks(sample_posts):
    metrics = analyze_hooks(sample_posts)
    assert (
        len(metrics.hookTypes) > 0
    )  # "Here are 5 tips..." should map to Number/List, "Did you know..." to Question
