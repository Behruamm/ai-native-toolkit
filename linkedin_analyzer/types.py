from typing import List, Dict, Optional, Literal, Any
from pydantic import BaseModel, Field

# ============================================================
# RAW APIFY OUTPUT — what comes back from the scraper
# ============================================================

class ApifyComment(BaseModel):
    text: str
    time: int

class ApifyAuthor(BaseModel):
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    occupation: Optional[str] = None

class ApifyDocument(BaseModel):
    coverPages: Optional[List[str]] = None

class ApifyPost(BaseModel):
    type: Literal["image", "text", "linkedinVideo", "document", "article"]
    text: str
    numLikes: int
    numComments: int
    numShares: int
    postedAtTimestamp: int
    postedAtISO: str
    authorName: str
    author: Optional[ApifyAuthor] = None
    comments: Optional[List[ApifyComment]] = None
    images: Optional[List[str]] = None
    document: Optional[ApifyDocument] = None
    url: Optional[str] = None
    urn: Optional[str] = None

# ============================================================
# CLEANED POST — after our cleaning step strips unnecessary data
# ============================================================

class CleanComment(BaseModel):
    text: str
    time: Optional[int] = None

class CleanPost(BaseModel):
    type: Literal["image", "text", "video", "document", "article"]
    text: str
    numLikes: int
    numComments: int
    numShares: int
    postedAtTimestamp: int
    postedAtISO: str
    authorName: str
    authorHeadline: str
    comments: List[CleanComment]

# ============================================================
# ANALYSIS RESULTS — output of the deterministic + AI pipeline
# ============================================================

# Section 1: Performance Snapshot (Python/TS — deterministic)
class CadenceMetrics(BaseModel):
    totalPosts: int
    periodStart: str
    periodEnd: str
    weeksCovered: int
    postsPerWeek: float
    avgDaysBetweenPosts: float

class EngagementMetrics(BaseModel):
    totalReactions: int
    totalComments: int
    totalReposts: int
    avgReactions: float
    avgComments: float
    avgReposts: float
    medianReactions: float
    medianComments: float

class PostTypeStats(BaseModel):
    type: str
    count: int
    percentage: float
    avgReactions: float
    avgComments: float

class ScheduleMetrics(BaseModel):
    postsByDay: Dict[str, int]
    postsByHour: Dict[int, int]
    bestDay: str
    bestHour: int
    highestEngagementDay: str
    highestEngagementHour: int

class ScoredPost(BaseModel):
    index: int
    text: str
    type: str
    numLikes: int
    numComments: int
    numShares: int
    postedAtISO: str
    engagementScore: float
    rank: int

class TextPatternMetrics(BaseModel):
    avgWordCount: float
    avgLineCount: float
    postsWithCTA: int
    postsWithQuestions: int
    postsWithLists: int
    postsWithHook: int
    ctaEngagementLift: float # percentage lift vs non-CTA posts

# Section 2: Content Strategy (Gemini AI)
class ContentPillar(BaseModel):
    name: str
    description: str
    percentageOfPosts: float
    engagementLevel: Literal["high", "medium", "low"]

class PostArchetype(BaseModel):
    name: str
    description: str
    count: int
    engagementLevel: Literal["high", "medium", "low"]

# Section 3: Deep Dive
class TopPostAnalysis(BaseModel):
    post: ScoredPost
    whyItWorked: List[str] # 3 bullet points from Gemini

class WorstPostAnalysis(BaseModel):
    post: ScoredPost
    whyItFlopped: str # 1-2 sentences from Gemini

# Section 4: Comment Analysis
class TopCommenter(BaseModel):
    name: str
    count: int

class CommentAnalysis(BaseModel):
    avgCommentLength: float
    spamRatio: float
    genuineRatio: float
    topCommenters: List[TopCommenter]

# ============================================================
# NEW: Hook & CTA Analysis
# ============================================================

class HookTypeBreakdown(BaseModel):
    type: Literal["Question", "Number/List", "Statement", "Story", "Provocative"]
    count: int
    percentage: float
    avgReactions: float

class WordCount(BaseModel):
    word: str
    count: int

class HookAnalysis(BaseModel):
    avgHookLength: float               # avg word count of first sentence
    hookTypes: List[HookTypeBreakdown] # type distribution
    urgencyRate: float                 # % of hooks with urgency words
    topFirstWords: List[WordCount]     # top 10 first words
    topHookWords: List[WordCount]      # top 10 non-stopword words in hooks

class CTATypeBreakdown(BaseModel):
    type: Literal["Comment-gated", "Follow", "DM", "Save/Share", "Link", "None"]
    count: int
    percentage: float
    avgReactions: float

class CTAAnalysis(BaseModel):
    ctaTypes: List[CTATypeBreakdown]
    topActionWords: List[WordCount]
    bestCTAType: str
    noCTARate: float                   # % of posts with no CTA

# ============================================================
# NEW: Word Frequency
# ============================================================

class WordFrequency(BaseModel):
    word: str
    count: int

# ============================================================
# NEW: CTA Formula (from Gemini)
# ============================================================

class CTAFormula(BaseModel):
    formula: str
    examples: List[str]

# ============================================================
# NEW: Master Growth Strategy (from Gemini)
# ============================================================

class WeakArea(BaseModel):
    observation: str
    fix: str

class FunnelStage(BaseModel):
    stage: Literal["Awareness", "Engagement", "Conversion"]
    description: str
    contentType: str

class MasterStrategy(BaseModel):
    weeklyPlan: str
    weakAreas: List[WeakArea]
    positioningAdvice: str
    contentFunnel: List[FunnelStage]

# ============================================================
# FULL ANALYSIS — the complete report data structure
# ============================================================

class FullAnalysis(BaseModel):
    # Profile info
    profileName: str
    profileHeadline: str
    analyzedAt: str

    # Section 1: Performance Snapshot (deterministic)
    cadence: CadenceMetrics
    engagement: EngagementMetrics
    postTypes: List[PostTypeStats]
    schedule: ScheduleMetrics
    scoredPosts: List[ScoredPost]
    textPatterns: TextPatternMetrics

    # Section 2: Content Strategy (Gemini)
    executiveSummary: str
    contentPillars: List[ContentPillar]
    postArchetypes: List[PostArchetype]

    # Section 3: Deep Dive (deterministic + Gemini)
    topPost: TopPostAnalysis
    worstPost: WorstPostAnalysis

    # Section 4: Comment Analysis (deterministic)
    commentAnalysis: CommentAnalysis

    # Section 5: Text Analysis (deterministic)
    wordFrequency: List[WordFrequency]

    # Section 6: Hook & CTA Blueprint (deterministic + Gemini)
    hookAnalysis: HookAnalysis
    ctaAnalysis: CTAAnalysis
    hookFormula: str
    ctaFormula: CTAFormula

    # Section 7: Growth Strategy (Gemini)
    masterStrategy: MasterStrategy

# ============================================================
# CLEANED OUTPUT — aggregated for the preview route
# ============================================================

class ScrapedProfile(BaseModel):
    profileUrl: str
    name: str
    headline: str
    posts: List[ApifyPost]

# ============================================================
# PREVIEW — subset shown before email gate
# ============================================================

class AnalysisPreview(BaseModel):
    profileUrl: str
    profileName: str
    profileHeadline: str
    totalPosts: int
    avgLikes: float
    avgComments: float
    topPost: ApifyPost
    postingFrequency: str
    dominantMediaType: str
    contentThemes: List[str]
    summary: str
    scrapedAt: str
    postTypeBreakdown: Dict[str, float]
    postingByDay: Dict[str, float]

AnalysisPreviewData = AnalysisPreview
