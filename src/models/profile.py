"""Data models for Instagram profiles and demographic filtering."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from datetime import datetime


class Gender(Enum):
    MALE = "male"
    FEMALE = "female"
    UNKNOWN = "unknown"


@dataclass
class InstagramProfile:
    """Represents an Instagram user profile with inferred demographics."""

    # Core profile data (from Apify)
    username: str
    user_id: str
    full_name: str
    biography: str
    follower_count: int
    following_count: int
    post_count: int
    is_verified: bool
    is_business: bool
    profile_pic_url: str
    external_url: Optional[str] = None

    # Inferred demographics
    inferred_gender: Gender = Gender.UNKNOWN
    inferred_age_min: Optional[int] = None
    inferred_age_max: Optional[int] = None
    gender_confidence: float = 0.0
    age_confidence: float = 0.0

    # Metadata
    scraped_at: datetime = field(default_factory=datetime.now)
    demographic_analysis: Optional[dict] = None

    @property
    def estimated_age_range(self) -> Optional[tuple[int, int]]:
        """Return the estimated age range if available."""
        if self.inferred_age_min and self.inferred_age_max:
            return (self.inferred_age_min, self.inferred_age_max)
        return None

    def matches_criteria(self, criteria: "DemographicCriteria") -> bool:
        """Check if this profile matches the given demographic criteria."""
        # Check gender
        if criteria.gender and criteria.gender != Gender.UNKNOWN:
            if self.inferred_gender != criteria.gender:
                return False
            if self.gender_confidence < criteria.min_confidence:
                return False

        # Check age range
        if criteria.age_min is not None or criteria.age_max is not None:
            if self.inferred_age_min is None or self.inferred_age_max is None:
                return False
            if self.age_confidence < criteria.min_confidence:
                return False

            # Check if age ranges overlap
            if criteria.age_min is not None and self.inferred_age_max < criteria.age_min:
                return False
            if criteria.age_max is not None and self.inferred_age_min > criteria.age_max:
                return False

        # Check follower count
        if criteria.min_followers is not None:
            if self.follower_count < criteria.min_followers:
                return False
        if criteria.max_followers is not None:
            if self.follower_count > criteria.max_followers:
                return False

        return True


@dataclass
class DemographicCriteria:
    """Criteria for filtering profiles by demographics."""

    gender: Optional[Gender] = None
    age_min: Optional[int] = None
    age_max: Optional[int] = None
    min_followers: Optional[int] = None
    max_followers: Optional[int] = None
    min_confidence: float = 0.5  # Minimum confidence score for demographic inference

    def __str__(self) -> str:
        parts = []
        if self.gender and self.gender != Gender.UNKNOWN:
            parts.append(f"gender={self.gender.value}")
        if self.age_min is not None:
            parts.append(f"age>={self.age_min}")
        if self.age_max is not None:
            parts.append(f"age<={self.age_max}")
        if self.min_followers is not None:
            parts.append(f"followers>={self.min_followers}")
        if self.max_followers is not None:
            parts.append(f"followers<={self.max_followers}")
        return f"DemographicCriteria({', '.join(parts)})"


@dataclass
class OutreachResult:
    """Result of an outreach attempt to a profile."""

    profile: InstagramProfile
    photos_liked: int = 0
    dm_sent: bool = False
    dm_message: Optional[str] = None
    success: bool = False
    error: Optional[str] = None
    completed_at: datetime = field(default_factory=datetime.now)
