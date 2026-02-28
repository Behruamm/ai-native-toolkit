from typing import List, Dict, Optional, Any
from pydantic import BaseModel, ConfigDict


# ============================================================
# RAW APIFY OUTPUT — memo23/linkedin-company-people-scraper
# ============================================================


class ApifyCandidate(BaseModel):
    """Raw output from the Apify company people scraper."""
    model_config = ConfigDict(extra="ignore")

    name: Optional[str] = None
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    title: Optional[str] = None           # job title
    location: Optional[str] = None
    profileUrl: Optional[str] = None
    linkedinUrl: Optional[str] = None
    avatarUrl: Optional[str] = None
    connectionDegree: Optional[str] = None
    summary: Optional[str] = None


# ============================================================
# CLEANED CANDIDATE — after normalization
# ============================================================


class Candidate(BaseModel):
    """Normalized candidate profile."""
    name: str
    title: str
    location: str
    profileUrl: str
    avatarUrl: str = ""
    summary: str = ""


# ============================================================
# AI ANALYSIS OUTPUTS
# ============================================================


class RankedCandidate(BaseModel):
    """A candidate with an AI-assigned priority rank."""
    rank: int
    name: str
    title: str
    location: str
    profileUrl: str
    whyTarget: str          # 1-2 sentences: why this person is a high-value target
    outreachAngle: str      # the specific hook angle for the DM


class OutreachDraft(BaseModel):
    """A personalized LinkedIn DM draft for a candidate."""
    candidateName: str
    profileUrl: str
    subject: str            # short subject line / opener
    message: str            # the full DM body (under 300 chars for LinkedIn)


class TeamStructureInsight(BaseModel):
    """AI insight about the competitor's team structure for a given role."""
    observation: str        # e.g. "Google has 40 senior SWEs in London, mostly from Meta"
    pattern: str            # e.g. "Strong preference for ex-FAANG backgrounds"
    implication: str        # e.g. "Signals rapid international expansion"


# ============================================================
# FULL TALENT REPORT
# ============================================================


class TalentReport(BaseModel):
    model_config = ConfigDict(extra="ignore")

    # Metadata
    companyUrl: str
    targetTitle: str
    scoutedAt: str
    totalCandidatesFound: int

    # Raw candidate list (all matches after filtering)
    candidates: List[Candidate]

    # AI outputs
    top5: List[RankedCandidate] = []
    outreachDrafts: List[OutreachDraft] = []
    teamInsights: List[TeamStructureInsight] = []
    executiveSummary: str = ""
