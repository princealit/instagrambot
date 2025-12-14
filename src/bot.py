"""Main bot orchestration - ties together scraping, filtering, and actions."""

import os
from dataclasses import dataclass
from typing import Optional
import structlog

from .scrapers import ApifyScraper
from .filters import DemographicFilter
from .actions import InstagramClient
from .models import DemographicCriteria, Gender, InstagramProfile, OutreachResult

logger = structlog.get_logger()


@dataclass
class BotConfig:
    """Configuration for the Instagram bot."""

    # Apify
    apify_token: Optional[str] = None

    # Instagram credentials
    instagram_username: Optional[str] = None
    instagram_password: Optional[str] = None

    # OpenAI (for demographic inference)
    openai_api_key: Optional[str] = None

    # Safety limits
    max_profiles_per_run: int = 50
    max_likes_per_profile: int = 3
    min_delay: int = 30
    max_delay: int = 90

    # Features
    use_ai_inference: bool = True
    dry_run: bool = False  # If True, don't actually perform Instagram actions

    @classmethod
    def from_env(cls) -> "BotConfig":
        """Load configuration from environment variables."""
        return cls(
            apify_token=os.getenv("APIFY_API_TOKEN"),
            instagram_username=os.getenv("INSTAGRAM_USERNAME"),
            instagram_password=os.getenv("INSTAGRAM_PASSWORD"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            max_profiles_per_run=int(os.getenv("MAX_PROFILES_PER_RUN", "50")),
            max_likes_per_profile=3,
            min_delay=int(os.getenv("MIN_DELAY_BETWEEN_ACTIONS", "30")),
            max_delay=int(os.getenv("MAX_DELAY_BETWEEN_ACTIONS", "90")),
            use_ai_inference=os.getenv("USE_AI_INFERENCE", "true").lower() == "true",
            dry_run=os.getenv("DRY_RUN", "false").lower() == "true",
        )


class InstagramBot:
    """
    Main bot that orchestrates the full workflow:
    1. Scrape profiles (via Apify)
    2. Filter by demographics
    3. Perform outreach (like + DM)
    """

    def __init__(self, config: Optional[BotConfig] = None):
        """Initialize the bot with configuration."""
        self.config = config or BotConfig.from_env()

        # Initialize components
        self.scraper = ApifyScraper(self.config.apify_token)
        self.filter = DemographicFilter(
            openai_api_key=self.config.openai_api_key,
            use_ai=self.config.use_ai_inference,
        )

        self.instagram: Optional[InstagramClient] = None
        if not self.config.dry_run:
            self.instagram = InstagramClient(
                username=self.config.instagram_username,
                password=self.config.instagram_password,
                min_delay=self.config.min_delay,
                max_delay=self.config.max_delay,
            )

        logger.info(
            "Bot initialized",
            dry_run=self.config.dry_run,
            ai_inference=self.config.use_ai_inference,
        )

    def run_hashtag_campaign(
        self,
        hashtags: list[str],
        criteria: DemographicCriteria,
        message_template: str,
        max_outreach: int = 10,
    ) -> list[OutreachResult]:
        """
        Run a campaign targeting users from hashtags.

        Args:
            hashtags: Hashtags to scrape (without #)
            criteria: Demographic criteria to filter by
            message_template: DM message template (use {name} for personalization)
            max_outreach: Maximum number of users to reach out to

        Returns:
            List of outreach results
        """
        logger.info(
            "Starting hashtag campaign",
            hashtags=hashtags,
            criteria=str(criteria),
            max_outreach=max_outreach,
        )

        # Step 1: Scrape profiles
        profiles = self.scraper.scrape_profiles_by_hashtag(
            hashtags,
            results_limit=self.config.max_profiles_per_run,
        )
        logger.info("Scraped profiles from hashtags", count=len(profiles))

        # Step 2: Filter by demographics
        matched = self.filter.filter_profiles(profiles, criteria)
        logger.info("Profiles matching criteria", count=len(matched))

        # Step 3: Perform outreach
        return self._perform_outreach(matched[:max_outreach], message_template)

    def run_follower_campaign(
        self,
        source_accounts: list[str],
        criteria: DemographicCriteria,
        message_template: str,
        max_outreach: int = 10,
    ) -> list[OutreachResult]:
        """
        Run a campaign targeting followers of specific accounts.

        Args:
            source_accounts: Accounts to scrape followers from
            criteria: Demographic criteria to filter by
            message_template: DM message template
            max_outreach: Maximum users to reach out to

        Returns:
            List of outreach results
        """
        logger.info(
            "Starting follower campaign",
            sources=source_accounts,
            criteria=str(criteria),
        )

        all_profiles = []
        for account in source_accounts:
            profiles = self.scraper.scrape_followers(
                account,
                results_limit=self.config.max_profiles_per_run // len(source_accounts),
            )
            all_profiles.extend(profiles)

        logger.info("Scraped follower profiles", count=len(all_profiles))

        # Filter by demographics
        matched = self.filter.filter_profiles(all_profiles, criteria)
        logger.info("Profiles matching criteria", count=len(matched))

        return self._perform_outreach(matched[:max_outreach], message_template)

    def run_search_campaign(
        self,
        search_query: str,
        criteria: DemographicCriteria,
        message_template: str,
        max_outreach: int = 10,
    ) -> list[OutreachResult]:
        """
        Run a campaign targeting users from a search query.

        Args:
            search_query: Search query (e.g., "fitness coach NYC")
            criteria: Demographic criteria to filter by
            message_template: DM message template
            max_outreach: Maximum users to reach out to

        Returns:
            List of outreach results
        """
        logger.info(
            "Starting search campaign",
            query=search_query,
            criteria=str(criteria),
        )

        profiles = self.scraper.search_profiles(
            search_query,
            results_limit=self.config.max_profiles_per_run,
        )
        logger.info("Found profiles from search", count=len(profiles))

        matched = self.filter.filter_profiles(profiles, criteria)
        logger.info("Profiles matching criteria", count=len(matched))

        return self._perform_outreach(matched[:max_outreach], message_template)

    def analyze_profiles_only(
        self,
        usernames: list[str],
        criteria: Optional[DemographicCriteria] = None,
    ) -> list[InstagramProfile]:
        """
        Scrape and analyze profiles without performing outreach.

        Useful for testing demographic inference.

        Args:
            usernames: List of usernames to analyze
            criteria: Optional criteria to filter by

        Returns:
            List of analyzed profiles
        """
        profiles = self.scraper.scrape_profiles_by_username(usernames)

        analyzed = [self.filter.analyze_profile(p) for p in profiles]

        if criteria:
            analyzed = [p for p in analyzed if p.matches_criteria(criteria)]

        return analyzed

    def _perform_outreach(
        self,
        profiles: list[InstagramProfile],
        message_template: str,
    ) -> list[OutreachResult]:
        """Perform outreach to a list of profiles."""
        results = []

        if self.config.dry_run:
            logger.info("DRY RUN - Not performing actual outreach")
            for profile in profiles:
                results.append(OutreachResult(
                    profile=profile,
                    success=True,
                    dm_message=message_template,
                ))
            return results

        if not self.instagram:
            raise RuntimeError("Instagram client not initialized")

        # Login
        self.instagram.login()

        for profile in profiles:
            result = self.instagram.outreach_to_profile(
                profile=profile,
                message_template=message_template,
                likes_count=self.config.max_likes_per_profile,
            )
            results.append(result)

            # Log progress
            success_count = sum(1 for r in results if r.success)
            logger.info(
                "Outreach progress",
                completed=len(results),
                total=len(profiles),
                successful=success_count,
            )

        # Cleanup
        self.instagram.logout()

        return results
