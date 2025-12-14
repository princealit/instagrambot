"""
Audience Demographics Analyzer

Fetches follower demographics (age, gender, location) from third-party services.
Uses browser automation to access free tiers of tools like Modash and Favikon.

Services supported:
- Modash (10 free searches/day) - https://modash.io/fake-follower-check
- Favikon (unlimited free) - Chrome extension data
- HypeAuditor (limited free reports)
"""

import asyncio
import json
import re
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
import structlog

logger = structlog.get_logger()


@dataclass
class AudienceDemographics:
    """Demographics breakdown of an Instagram account's followers."""

    username: str

    # Gender breakdown (percentages)
    male_percentage: Optional[float] = None
    female_percentage: Optional[float] = None

    # Age breakdown (percentages by age group)
    age_13_17: Optional[float] = None
    age_18_24: Optional[float] = None
    age_25_34: Optional[float] = None
    age_35_44: Optional[float] = None
    age_45_54: Optional[float] = None
    age_55_64: Optional[float] = None
    age_65_plus: Optional[float] = None

    # Top locations (country -> percentage)
    top_countries: dict[str, float] = field(default_factory=dict)

    # Top cities (city -> percentage)
    top_cities: dict[str, float] = field(default_factory=dict)

    # Quality metrics
    fake_follower_percentage: Optional[float] = None
    engagement_rate: Optional[float] = None

    # Metadata
    source: str = "unknown"
    fetched_at: datetime = field(default_factory=datetime.now)
    raw_data: Optional[dict] = None

    def matches_criteria(
        self,
        target_gender: Optional[str] = None,
        min_gender_percentage: float = 40.0,
        target_age_min: Optional[int] = None,
        target_age_max: Optional[int] = None,
        min_age_percentage: float = 30.0,
        target_country: Optional[str] = None,
        min_country_percentage: float = 20.0,
    ) -> tuple[bool, dict]:
        """
        Check if this audience matches targeting criteria.

        Args:
            target_gender: "male" or "female"
            min_gender_percentage: Minimum % of followers matching gender
            target_age_min: Minimum age for target range
            target_age_max: Maximum age for target range
            min_age_percentage: Minimum % of followers in age range
            target_country: Target country (e.g., "United States")
            min_country_percentage: Minimum % from target country

        Returns:
            (matches: bool, details: dict with match info)
        """
        details = {"checks": [], "passed": True}

        # Gender check
        if target_gender:
            if target_gender.lower() == "male" and self.male_percentage:
                matches = self.male_percentage >= min_gender_percentage
                details["checks"].append({
                    "type": "gender",
                    "target": "male",
                    "actual": self.male_percentage,
                    "threshold": min_gender_percentage,
                    "passed": matches,
                })
                if not matches:
                    details["passed"] = False

            elif target_gender.lower() == "female" and self.female_percentage:
                matches = self.female_percentage >= min_gender_percentage
                details["checks"].append({
                    "type": "gender",
                    "target": "female",
                    "actual": self.female_percentage,
                    "threshold": min_gender_percentage,
                    "passed": matches,
                })
                if not matches:
                    details["passed"] = False

        # Age range check
        if target_age_min is not None or target_age_max is not None:
            age_percentage = self._calculate_age_range_percentage(
                target_age_min or 0,
                target_age_max or 100,
            )
            if age_percentage is not None:
                matches = age_percentage >= min_age_percentage
                details["checks"].append({
                    "type": "age",
                    "target_range": f"{target_age_min or 0}-{target_age_max or 100}",
                    "actual": age_percentage,
                    "threshold": min_age_percentage,
                    "passed": matches,
                })
                if not matches:
                    details["passed"] = False

        # Country check
        if target_country and self.top_countries:
            country_pct = self.top_countries.get(target_country, 0)
            # Also check variations (e.g., "US" vs "United States")
            country_variations = self._get_country_variations(target_country)
            for var in country_variations:
                if var in self.top_countries:
                    country_pct = max(country_pct, self.top_countries[var])

            matches = country_pct >= min_country_percentage
            details["checks"].append({
                "type": "country",
                "target": target_country,
                "actual": country_pct,
                "threshold": min_country_percentage,
                "passed": matches,
            })
            if not matches:
                details["passed"] = False

        return details["passed"], details

    def _calculate_age_range_percentage(self, min_age: int, max_age: int) -> Optional[float]:
        """Calculate total percentage of followers in an age range."""
        total = 0.0
        has_data = False

        age_groups = [
            (13, 17, self.age_13_17),
            (18, 24, self.age_18_24),
            (25, 34, self.age_25_34),
            (35, 44, self.age_35_44),
            (45, 54, self.age_45_54),
            (55, 64, self.age_55_64),
            (65, 100, self.age_65_plus),
        ]

        for group_min, group_max, percentage in age_groups:
            if percentage is not None:
                has_data = True
                # Check if age group overlaps with target range
                if group_max >= min_age and group_min <= max_age:
                    total += percentage

        return total if has_data else None

    def _get_country_variations(self, country: str) -> list[str]:
        """Get variations of country names."""
        variations_map = {
            "United States": ["US", "USA", "United States of America"],
            "US": ["United States", "USA", "United States of America"],
            "United Kingdom": ["UK", "GB", "Great Britain", "England"],
            "UK": ["United Kingdom", "GB", "Great Britain", "England"],
        }
        return variations_map.get(country, [country])

    def summary(self) -> str:
        """Return a human-readable summary."""
        parts = []

        if self.male_percentage and self.female_percentage:
            parts.append(f"Gender: {self.male_percentage:.0f}% M / {self.female_percentage:.0f}% F")

        age_parts = []
        if self.age_18_24:
            age_parts.append(f"18-24: {self.age_18_24:.0f}%")
        if self.age_25_34:
            age_parts.append(f"25-34: {self.age_25_34:.0f}%")
        if self.age_35_44:
            age_parts.append(f"35-44: {self.age_35_44:.0f}%")
        if self.age_45_54:
            age_parts.append(f"45-54: {self.age_45_54:.0f}%")
        if self.age_55_64:
            age_parts.append(f"55-64: {self.age_55_64:.0f}%")
        if age_parts:
            parts.append(f"Age: {', '.join(age_parts)}")

        if self.top_countries:
            top_3 = list(self.top_countries.items())[:3]
            countries = ", ".join(f"{c}: {p:.0f}%" for c, p in top_3)
            parts.append(f"Location: {countries}")

        if self.fake_follower_percentage is not None:
            parts.append(f"Fake followers: {self.fake_follower_percentage:.0f}%")

        return " | ".join(parts) if parts else "No demographic data"


class AudienceAnalyzer:
    """
    Analyzes Instagram account audience demographics.

    Uses browser automation to fetch data from free tools:
    - Modash: 10 free searches/day
    - Manual input: For when you have the data from other sources
    """

    def __init__(self, playwright_browser=None):
        """
        Initialize the analyzer.

        Args:
            playwright_browser: Optional Playwright browser instance for automation
        """
        self.browser = playwright_browser
        self._modash_searches_today = 0
        logger.info("Initialized AudienceAnalyzer")

    async def analyze_with_modash(self, username: str) -> Optional[AudienceDemographics]:
        """
        Fetch demographics from Modash free tool.

        Note: Requires Playwright for browser automation.
        Limited to 10 searches per day on free tier.

        Args:
            username: Instagram username to analyze

        Returns:
            AudienceDemographics or None if failed
        """
        if self._modash_searches_today >= 10:
            logger.warning("Modash daily limit reached (10 searches)")
            return None

        try:
            # Import playwright dynamically
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                # Navigate to Modash free checker
                url = f"https://www.modash.io/fake-follower-check?username={username}"
                await page.goto(url)

                # Wait for results to load
                await page.wait_for_selector('[data-testid="results"]', timeout=30000)

                # Extract demographics data
                data = await self._extract_modash_data(page)

                await browser.close()

                if data:
                    self._modash_searches_today += 1
                    return self._parse_modash_data(username, data)

        except ImportError:
            logger.error("Playwright not installed. Run: pip install playwright && playwright install")
        except Exception as e:
            logger.error("Failed to fetch from Modash", error=str(e))

        return None

    async def _extract_modash_data(self, page) -> Optional[dict]:
        """Extract demographic data from Modash page."""
        try:
            # This is a simplified example - actual selectors may vary
            data = await page.evaluate("""
                () => {
                    const result = {};

                    // Try to find demographic sections
                    const genderSection = document.querySelector('[data-testid="gender"]');
                    if (genderSection) {
                        result.gender = genderSection.textContent;
                    }

                    const ageSection = document.querySelector('[data-testid="age"]');
                    if (ageSection) {
                        result.age = ageSection.textContent;
                    }

                    const locationSection = document.querySelector('[data-testid="location"]');
                    if (locationSection) {
                        result.location = locationSection.textContent;
                    }

                    return result;
                }
            """)
            return data
        except Exception as e:
            logger.warning("Failed to extract Modash data", error=str(e))
            return None

    def _parse_modash_data(self, username: str, data: dict) -> AudienceDemographics:
        """Parse raw Modash data into AudienceDemographics."""
        demographics = AudienceDemographics(
            username=username,
            source="modash",
            raw_data=data,
        )

        # Parse gender (example: "65% Male, 35% Female")
        if "gender" in data:
            gender_match = re.findall(r"(\d+)%\s*(Male|Female)", data["gender"], re.I)
            for pct, gender in gender_match:
                if gender.lower() == "male":
                    demographics.male_percentage = float(pct)
                else:
                    demographics.female_percentage = float(pct)

        # Parse age (example: "25-34: 35%, 35-44: 25%")
        if "age" in data:
            age_patterns = [
                (r"13-17[:\s]+(\d+)%", "age_13_17"),
                (r"18-24[:\s]+(\d+)%", "age_18_24"),
                (r"25-34[:\s]+(\d+)%", "age_25_34"),
                (r"35-44[:\s]+(\d+)%", "age_35_44"),
                (r"45-54[:\s]+(\d+)%", "age_45_54"),
                (r"55-64[:\s]+(\d+)%", "age_55_64"),
                (r"65\+[:\s]+(\d+)%", "age_65_plus"),
            ]
            for pattern, attr in age_patterns:
                match = re.search(pattern, data["age"], re.I)
                if match:
                    setattr(demographics, attr, float(match.group(1)))

        return demographics

    def from_manual_input(
        self,
        username: str,
        male_pct: Optional[float] = None,
        female_pct: Optional[float] = None,
        age_data: Optional[dict] = None,
        countries: Optional[dict] = None,
        cities: Optional[dict] = None,
        fake_follower_pct: Optional[float] = None,
    ) -> AudienceDemographics:
        """
        Create demographics from manual input.

        Useful when you have data from HypeAuditor, Favikon, etc.
        that was gathered manually.

        Args:
            username: Instagram username
            male_pct: Percentage of male followers
            female_pct: Percentage of female followers
            age_data: Dict with age ranges, e.g., {"25-34": 35, "35-44": 25}
            countries: Dict with countries, e.g., {"United States": 45}
            cities: Dict with cities
            fake_follower_pct: Fake follower percentage

        Returns:
            AudienceDemographics object
        """
        demographics = AudienceDemographics(
            username=username,
            male_percentage=male_pct,
            female_percentage=female_pct,
            top_countries=countries or {},
            top_cities=cities or {},
            fake_follower_percentage=fake_follower_pct,
            source="manual",
        )

        # Parse age data
        if age_data:
            age_mapping = {
                "13-17": "age_13_17",
                "18-24": "age_18_24",
                "25-34": "age_25_34",
                "35-44": "age_35_44",
                "45-54": "age_45_54",
                "55-64": "age_55_64",
                "65+": "age_65_plus",
            }
            for range_str, attr in age_mapping.items():
                if range_str in age_data:
                    setattr(demographics, attr, age_data[range_str])

        return demographics

    def from_json(self, json_path: str) -> list[AudienceDemographics]:
        """
        Load demographics from a JSON file.

        Expected format:
        [
            {
                "username": "example",
                "male_percentage": 65,
                "female_percentage": 35,
                "age_25_34": 40,
                "age_35_44": 30,
                "top_countries": {"United States": 50, "Canada": 10}
            }
        ]
        """
        with open(json_path) as f:
            data = json.load(f)

        results = []
        for item in data:
            demographics = AudienceDemographics(
                username=item.get("username", "unknown"),
                male_percentage=item.get("male_percentage"),
                female_percentage=item.get("female_percentage"),
                age_13_17=item.get("age_13_17"),
                age_18_24=item.get("age_18_24"),
                age_25_34=item.get("age_25_34"),
                age_35_44=item.get("age_35_44"),
                age_45_54=item.get("age_45_54"),
                age_55_64=item.get("age_55_64"),
                age_65_plus=item.get("age_65_plus"),
                top_countries=item.get("top_countries", {}),
                top_cities=item.get("top_cities", {}),
                fake_follower_percentage=item.get("fake_follower_percentage"),
                source="json_import",
            )
            results.append(demographics)

        return results


def filter_accounts_by_audience(
    accounts: list[str],
    audience_data: dict[str, AudienceDemographics],
    target_gender: Optional[str] = None,
    min_gender_pct: float = 40.0,
    target_age_min: Optional[int] = None,
    target_age_max: Optional[int] = None,
    min_age_pct: float = 30.0,
    target_country: Optional[str] = None,
    min_country_pct: float = 20.0,
) -> list[tuple[str, AudienceDemographics, dict]]:
    """
    Filter accounts based on their audience demographics.

    This is useful for finding accounts whose FOLLOWERS match your target.
    E.g., find accounts where 50%+ of followers are men aged 40-60 in California.

    Args:
        accounts: List of Instagram usernames
        audience_data: Dict mapping username -> AudienceDemographics
        target_gender: "male" or "female"
        min_gender_pct: Minimum % of followers matching gender
        target_age_min: Minimum age
        target_age_max: Maximum age
        min_age_pct: Minimum % in age range
        target_country: Target country
        min_country_pct: Minimum % from country

    Returns:
        List of (username, demographics, match_details) for matching accounts
    """
    results = []

    for username in accounts:
        if username not in audience_data:
            logger.warning("No audience data for account", username=username)
            continue

        demographics = audience_data[username]
        matches, details = demographics.matches_criteria(
            target_gender=target_gender,
            min_gender_percentage=min_gender_pct,
            target_age_min=target_age_min,
            target_age_max=target_age_max,
            min_age_percentage=min_age_pct,
            target_country=target_country,
            min_country_percentage=min_country_pct,
        )

        if matches:
            results.append((username, demographics, details))
            logger.info(
                "Account matches audience criteria",
                username=username,
                summary=demographics.summary(),
            )

    return results
