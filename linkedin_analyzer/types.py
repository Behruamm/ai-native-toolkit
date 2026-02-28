from typing import List, Dict, Optional, Literal, Any
from pydantic import BaseModel, ConfigDict

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
    url: str = ""


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
    ageAdjustedScore: float
    rank: int
    ageAdjustedRank: int
    url: str = ""


class TextPatternMetrics(BaseModel):
    avgWordCount: float
    avgLineCount: float
    postsWithCTA: int
    postsWithQuestions: int
    postsWithLists: int
    postsWithHook: int
    ctaEngagementLift: float  # percentage lift vs non-CTA posts


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


# Section 4: Comment Analysis
class TopCommenter(BaseModel):
    name: str
    count: int


class CommentAnalysis(BaseModel):
    avgCommentLength: float
    spamRatio: float
    genuineRatio: float
    topCommenters: List[TopCommenter]
    available: bool = False
    note: str = ""


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
    avgHookLength: float  # avg word count of first sentence
    hookTypes: List[HookTypeBreakdown]  # type distribution
    urgencyRate: float  # % of hooks with urgency words
    topFirstWords: List[WordCount]  # top 10 first words
    topHookWords: List[WordCount]  # top 10 non-stopword words in hooks


class CTATypeBreakdown(BaseModel):
    type: Literal["Comment-gated", "Follow", "DM", "Save/Share", "Link", "None"]
    count: int
    percentage: float
    avgReactions: float


class CTAAnalysis(BaseModel):
    ctaTypes: List[CTATypeBreakdown]
    topActionWords: List[WordCount]
    bestCTAType: str
    noCTARate: float  # % of posts with no CTA


# ============================================================
# NEW: Word Frequency
# ============================================================


class WordFrequency(BaseModel):
    word: str
    count: int


# ============================================================
# NEW: Hook & CTA Strategy (LLM semantic analysis)
# ============================================================


class StrategyExample(BaseModel):
    text: str
    url: str = ""
    score: float = 0.0


class StrategyPattern(BaseModel):
    name: str
    description: str
    engagementLevel: Literal["high", "medium", "low"]


class HookStrategy(BaseModel):
    formula: str
    patterns: List[StrategyPattern]
    bestExamples: List[StrategyExample]


class CTAStrategy(BaseModel):
    formula: str
    patterns: List[StrategyPattern]
    bestExamples: List[StrategyExample]


# ============================================================
# NEW: Chunk Analysis (for optimized pipeline)
# ============================================================


class ChunkAnalysisResult(BaseModel):
    """Result from analyzing a single chunk of posts."""
    pillar_candidates: List[str]
    archetype_candidates: List[str]
    hook_patterns: List[StrategyPattern]
    cta_patterns: List[StrategyPattern]
    post_assignments: List[Dict[str, Any]]
    summary_bullets: List[str]


class AgentWorkflow(BaseModel):
    """An AI agent workflow a solo operator can use to replicate a content pillar."""
    name: str          # e.g. "Research Agent for Thought Leadership"
    pillar: str        # which content pillar this maps to
    archetype: str     # which post archetype it generates
    description: str   # what the agent does and why it creates leverage
    prompt_skeleton: str  # a starter prompt/workflow skeleton


class StealThisHook(BaseModel):
    """A pre-written LinkedIn hook tailored to the profile's best archetypes."""
    hook: str          # the ready-to-use hook line
    archetype: str     # which archetype this is based on
    why_it_works: str  # one sentence on the psychology behind it


class ConsolidatedAnalysis(BaseModel):
    """Consolidated result from all chunks."""
    pillars: List[ContentPillar]
    archetypes: List[PostArchetype]
    hookStrategy: HookStrategy
    ctaStrategy: CTAStrategy
    executiveSummary: str
    bigStrategicOpportunity: str = ""


# ============================================================
# FULL ANALYSIS — the complete report data structure
# ============================================================


class FullAnalysis(BaseModel):
    model_config = ConfigDict(extra="ignore")
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
    scoredPostsAgeAdjusted: List[ScoredPost]
    textPatterns: TextPatternMetrics

    # Section 2: Content Strategy (AI)
    executiveSummary: str
    bigStrategicOpportunity: str = ""
    contentPillars: List[ContentPillar]
    postArchetypes: List[PostArchetype]

    # Section 3: Deep Dive (deterministic only - no AI analysis)
    topPosts: List[ScoredPost]
    worstPosts: List[ScoredPost]

    # Section 4: Comment Analysis (deterministic)
    commentAnalysis: CommentAnalysis

    # Section 5: Text Analysis (deterministic)
    wordFrequency: List[WordFrequency]

    # Section 6: Hook & CTA Blueprint (deterministic + AI)
    hookAnalysis: HookAnalysis
    ctaAnalysis: CTAAnalysis
    hookStrategy: HookStrategy
    ctaStrategy: CTAStrategy

    # Section 7: AI-Native Blueprint (new)
    agentWorkflows: List[AgentWorkflow] = []
    stealTheseHooks: List[StealThisHook] = []


# ============================================================
# POST DECONSTRUCTION — single-post viral analysis
# ============================================================


class PostDeconstructionAI(BaseModel):
    whyItWorked: str           # 2-3 sentence explanation
    contentPillar: str         # e.g. "Founder Vulnerability"
    archetype: str             # e.g. "Personal Story"
    hookFormula: str           # reusable hook pattern
    ctaFormula: str            # reusable CTA pattern
    replicationGuide: List[str]  # step-by-step bullet points


class PostDeconstruction(BaseModel):
    postUrl: str
    authorName: str
    authorHeadline: str
    analyzedAt: str

    # Raw stats
    type: str
    text: str
    numLikes: int
    numComments: int
    numShares: int
    postedAtISO: str

    # Deterministic pattern analysis
    hook: str
    hookType: str
    hookLength: int            # word count of hook
    cta: str
    ctaType: str

    # AI analysis (None when --skip-ai)
    ai: Optional[PostDeconstructionAI] = None

