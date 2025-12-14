"""Demographic inference and filtering for Instagram profiles."""

import os
import re
from datetime import datetime
from typing import Optional
import structlog
import gender_guesser.detector as gender_detector
from openai import OpenAI

from ..models import InstagramProfile, DemographicCriteria, Gender

logger = structlog.get_logger()


class DemographicFilter:
    """
    Infers demographic information from Instagram profiles and filters them.

    Uses multiple signals:
    1. First name -> Gender (using gender-guesser library)
    2. Bio text analysis -> Age hints, gender hints
    3. Optional: AI-powered analysis for more accurate inference
    """

    # Patterns for extracting age from bios
    AGE_PATTERNS = [
        r"\b(\d{1,2})\s*(?:years?\s*old|y/?o|yrs)\b",  # "25 years old", "25 y/o"
        r"\b(?:age|aged?)\s*:?\s*(\d{1,2})\b",  # "age: 25", "aged 25"
        r"\b(?:born\s*(?:in\s*)?)?(?:19|20)(\d{2})\b",  # "born 1985" -> calculate age
        r"\b(\d{1,2})(?:st|nd|rd|th)?\s*(?:birthday|bday)\b",  # "40th birthday"
    ]

    # Keywords suggesting male
    MALE_KEYWORDS = [
        "dad", "father", "husband", "son", "boy", "man", "guy", "male",
        "grandpa", "grandfather", "uncle", "brother", "mr", "sir",
        "he/him", "businessman", "actor", "king"
    ]

    # Keywords suggesting female
    FEMALE_KEYWORDS = [
        "mom", "mother", "wife", "daughter", "girl", "woman", "lady", "female",
        "grandma", "grandmother", "aunt", "sister", "mrs", "ms", "miss",
        "she/her", "businesswoman", "actress", "queen", "mama"
    ]

    def __init__(self, openai_api_key: Optional[str] = None, use_ai: bool = True):
        """
        Initialize the demographic filter.

        Args:
            openai_api_key: OpenAI API key for AI-powered analysis
            use_ai: Whether to use AI for enhanced inference
        """
        self.gender_detector = gender_detector.Detector()
        self.use_ai = use_ai

        if use_ai:
            api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
            if api_key:
                self.openai_client = OpenAI(api_key=api_key)
            else:
                logger.warning("OpenAI API key not provided, AI analysis disabled")
                self.use_ai = False
                self.openai_client = None
        else:
            self.openai_client = None

        logger.info("Initialized demographic filter", use_ai=self.use_ai)

    def analyze_profile(self, profile: InstagramProfile) -> InstagramProfile:
        """
        Analyze a profile and infer demographic information.

        Args:
            profile: Instagram profile to analyze

        Returns:
            Profile with inferred demographics populated
        """
        # Extract first name from full name
        first_name = self._extract_first_name(profile.full_name)

        # Infer gender from name
        name_gender, name_confidence = self._infer_gender_from_name(first_name)

        # Infer gender from bio keywords
        bio_gender, bio_confidence = self._infer_gender_from_bio(profile.biography)

        # Combine gender signals
        if bio_confidence > name_confidence:
            profile.inferred_gender = bio_gender
            profile.gender_confidence = bio_confidence
        else:
            profile.inferred_gender = name_gender
            profile.gender_confidence = name_confidence

        # Infer age from bio
        age_range, age_confidence = self._infer_age_from_bio(profile.biography)
        if age_range:
            profile.inferred_age_min, profile.inferred_age_max = age_range
            profile.age_confidence = age_confidence

        # Use AI for enhanced analysis if enabled and confidence is low
        if self.use_ai and (profile.gender_confidence < 0.6 or profile.age_confidence < 0.6):
            self._ai_enhanced_analysis(profile)

        profile.demographic_analysis = {
            "first_name": first_name,
            "name_gender": name_gender.value if name_gender else None,
            "name_confidence": name_confidence,
            "bio_gender": bio_gender.value if bio_gender else None,
            "bio_confidence": bio_confidence,
            "age_signals": self._find_age_signals(profile.biography),
        }

        logger.debug(
            "Analyzed profile demographics",
            username=profile.username,
            gender=profile.inferred_gender.value,
            gender_conf=profile.gender_confidence,
            age_range=profile.estimated_age_range,
            age_conf=profile.age_confidence,
        )

        return profile

    def filter_profiles(
        self,
        profiles: list[InstagramProfile],
        criteria: DemographicCriteria,
    ) -> list[InstagramProfile]:
        """
        Filter profiles based on demographic criteria.

        Args:
            profiles: List of profiles to filter
            criteria: Demographic criteria to match

        Returns:
            List of profiles matching the criteria
        """
        logger.info("Filtering profiles", total=len(profiles), criteria=str(criteria))

        # First analyze all profiles
        analyzed = [self.analyze_profile(p) for p in profiles]

        # Then filter
        matched = [p for p in analyzed if p.matches_criteria(criteria)]

        logger.info("Filtered profiles", matched=len(matched), total=len(profiles))
        return matched

    def _extract_first_name(self, full_name: str) -> str:
        """Extract first name from full name."""
        if not full_name:
            return ""
        # Take first word, remove emojis and special chars
        name = re.sub(r"[^\w\s]", "", full_name).strip()
        parts = name.split()
        return parts[0] if parts else ""

    def _infer_gender_from_name(self, first_name: str) -> tuple[Gender, float]:
        """Infer gender from first name using gender-guesser."""
        if not first_name:
            return Gender.UNKNOWN, 0.0

        result = self.gender_detector.get_gender(first_name)

        gender_map = {
            "male": (Gender.MALE, 0.9),
            "mostly_male": (Gender.MALE, 0.75),
            "female": (Gender.FEMALE, 0.9),
            "mostly_female": (Gender.FEMALE, 0.75),
            "andy": (Gender.UNKNOWN, 0.3),  # Androgynous
            "unknown": (Gender.UNKNOWN, 0.0),
        }

        return gender_map.get(result, (Gender.UNKNOWN, 0.0))

    def _infer_gender_from_bio(self, bio: str) -> tuple[Gender, float]:
        """Infer gender from bio keywords."""
        if not bio:
            return Gender.UNKNOWN, 0.0

        bio_lower = bio.lower()

        male_score = sum(1 for kw in self.MALE_KEYWORDS if kw in bio_lower)
        female_score = sum(1 for kw in self.FEMALE_KEYWORDS if kw in bio_lower)

        if male_score > female_score:
            confidence = min(0.9, 0.5 + (male_score * 0.15))
            return Gender.MALE, confidence
        elif female_score > male_score:
            confidence = min(0.9, 0.5 + (female_score * 0.15))
            return Gender.FEMALE, confidence
        else:
            return Gender.UNKNOWN, 0.0

    def _infer_age_from_bio(self, bio: str) -> tuple[Optional[tuple[int, int]], float]:
        """Infer age range from bio text."""
        if not bio:
            return None, 0.0

        current_year = datetime.now().year

        for pattern in self.AGE_PATTERNS:
            match = re.search(pattern, bio, re.IGNORECASE)
            if match:
                value = int(match.group(1))

                # Check if it's a birth year
                if value < 100 and "born" in bio.lower():
                    # Two-digit year
                    if value > 50:
                        birth_year = 1900 + value
                    else:
                        birth_year = 2000 + value
                    age = current_year - birth_year
                elif value > 1900:
                    # Four-digit year (from pattern)
                    age = current_year - (1900 + value)
                else:
                    age = value

                # Sanity check
                if 13 <= age <= 100:
                    # Return a range around the detected age
                    return (max(13, age - 2), min(100, age + 2)), 0.85

        return None, 0.0

    def _find_age_signals(self, bio: str) -> list[str]:
        """Find all age-related signals in bio for debugging."""
        signals = []
        if not bio:
            return signals

        for pattern in self.AGE_PATTERNS:
            matches = re.findall(pattern, bio, re.IGNORECASE)
            signals.extend(matches)

        return signals

    def _ai_enhanced_analysis(self, profile: InstagramProfile) -> None:
        """Use AI to enhance demographic analysis."""
        if not self.openai_client:
            return

        prompt = f"""Analyze this Instagram profile and estimate demographics.

Full Name: {profile.full_name}
Bio: {profile.biography}
Followers: {profile.follower_count}
Is Business Account: {profile.is_business}

Based on the available information, provide your best estimate:
1. Gender (male/female/unknown)
2. Gender confidence (0.0-1.0)
3. Age range (min-max, or null if cannot determine)
4. Age confidence (0.0-1.0)

Respond in JSON format only:
{{"gender": "male|female|unknown", "gender_confidence": 0.X, "age_min": X, "age_max": X, "age_confidence": 0.X}}
"""

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                max_tokens=100,
            )

            import json
            result = json.loads(response.choices[0].message.content)

            # Update profile if AI is more confident
            ai_gender_conf = result.get("gender_confidence", 0)
            ai_age_conf = result.get("age_confidence", 0)

            if ai_gender_conf > profile.gender_confidence:
                gender_str = result.get("gender", "unknown")
                profile.inferred_gender = Gender(gender_str) if gender_str in ["male", "female"] else Gender.UNKNOWN
                profile.gender_confidence = ai_gender_conf

            if ai_age_conf > profile.age_confidence:
                profile.inferred_age_min = result.get("age_min")
                profile.inferred_age_max = result.get("age_max")
                profile.age_confidence = ai_age_conf

            logger.debug("AI enhanced analysis completed", username=profile.username)

        except Exception as e:
            logger.warning("AI analysis failed", error=str(e))
