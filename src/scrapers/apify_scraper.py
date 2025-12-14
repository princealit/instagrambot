"""Apify integration for scraping Instagram profiles."""

import os
from typing import Optional
from datetime import datetime
import structlog
from apify_client import ApifyClient

from ..models import InstagramProfile, Gender

logger = structlog.get_logger()


class ApifyScraper:
    """Scrapes Instagram profiles using Apify actors."""

    # Apify actor IDs for different scrapers
    PROFILE_SCRAPER = "apify/instagram-profile-scraper"
    HASHTAG_SCRAPER = "apify/instagram-hashtag-scraper"
    SEARCH_SCRAPER = "apify/instagram-search-scraper"

    def __init__(self, api_token: Optional[str] = None):
        """
        Initialize the Apify scraper.

        Args:
            api_token: Apify API token. If not provided, reads from APIFY_API_TOKEN env var.
        """
        self.api_token = api_token or os.getenv("APIFY_API_TOKEN")
        if not self.api_token:
            raise ValueError("Apify API token is required. Set APIFY_API_TOKEN env var.")

        self.client = ApifyClient(self.api_token)
        logger.info("Initialized Apify scraper")

    def scrape_profiles_by_hashtag(
        self,
        hashtags: list[str],
        results_limit: int = 100,
    ) -> list[InstagramProfile]:
        """
        Scrape profiles from posts with specific hashtags.

        Args:
            hashtags: List of hashtags to search (without #)
            results_limit: Maximum number of profiles to return

        Returns:
            List of Instagram profiles
        """
        logger.info("Scraping profiles by hashtag", hashtags=hashtags, limit=results_limit)

        # First get posts from hashtags
        run_input = {
            "hashtags": hashtags,
            "resultsLimit": results_limit,
            "resultsType": "posts",
        }

        run = self.client.actor(self.HASHTAG_SCRAPER).call(run_input=run_input)
        items = list(self.client.dataset(run["defaultDatasetId"]).iterate_items())

        # Extract unique usernames from posts
        usernames = list(set(item.get("ownerUsername") for item in items if item.get("ownerUsername")))
        logger.info("Found unique usernames from hashtag posts", count=len(usernames))

        # Now scrape those profiles
        return self.scrape_profiles_by_username(usernames[:results_limit])

    def scrape_profiles_by_username(
        self,
        usernames: list[str],
    ) -> list[InstagramProfile]:
        """
        Scrape profiles by username.

        Args:
            usernames: List of Instagram usernames

        Returns:
            List of Instagram profiles
        """
        logger.info("Scraping profiles by username", count=len(usernames))

        run_input = {
            "usernames": usernames,
        }

        run = self.client.actor(self.PROFILE_SCRAPER).call(run_input=run_input)
        items = list(self.client.dataset(run["defaultDatasetId"]).iterate_items())

        profiles = []
        for item in items:
            try:
                profile = self._parse_profile(item)
                profiles.append(profile)
            except Exception as e:
                logger.warning("Failed to parse profile", username=item.get("username"), error=str(e))

        logger.info("Successfully scraped profiles", count=len(profiles))
        return profiles

    def scrape_profiles_by_location(
        self,
        location_ids: list[str],
        results_limit: int = 100,
    ) -> list[InstagramProfile]:
        """
        Scrape profiles from posts at specific locations.

        Args:
            location_ids: List of Instagram location IDs
            results_limit: Maximum number of profiles to return

        Returns:
            List of Instagram profiles
        """
        logger.info("Scraping profiles by location", locations=location_ids, limit=results_limit)

        run_input = {
            "locationIds": location_ids,
            "resultsLimit": results_limit,
            "resultsType": "posts",
        }

        run = self.client.actor("apify/instagram-scraper").call(run_input=run_input)
        items = list(self.client.dataset(run["defaultDatasetId"]).iterate_items())

        # Extract unique usernames
        usernames = list(set(item.get("ownerUsername") for item in items if item.get("ownerUsername")))

        return self.scrape_profiles_by_username(usernames[:results_limit])

    def search_profiles(
        self,
        query: str,
        results_limit: int = 50,
    ) -> list[InstagramProfile]:
        """
        Search for profiles matching a query.

        Args:
            query: Search query (e.g., "fitness coach")
            results_limit: Maximum number of profiles to return

        Returns:
            List of Instagram profiles
        """
        logger.info("Searching profiles", query=query, limit=results_limit)

        run_input = {
            "search": query,
            "resultsType": "user",
            "resultsLimit": results_limit,
        }

        run = self.client.actor(self.SEARCH_SCRAPER).call(run_input=run_input)
        items = list(self.client.dataset(run["defaultDatasetId"]).iterate_items())

        # Search results have less data, need to fetch full profiles
        usernames = [item.get("username") for item in items if item.get("username")]

        return self.scrape_profiles_by_username(usernames)

    def scrape_followers(
        self,
        username: str,
        results_limit: int = 100,
    ) -> list[InstagramProfile]:
        """
        Scrape followers of a specific account.

        Args:
            username: Instagram username to get followers from
            results_limit: Maximum number of followers to return

        Returns:
            List of Instagram profiles
        """
        logger.info("Scraping followers", username=username, limit=results_limit)

        run_input = {
            "usernames": [username],
            "resultsType": "followers",
            "resultsLimit": results_limit,
        }

        run = self.client.actor("apify/instagram-scraper").call(run_input=run_input)
        items = list(self.client.dataset(run["defaultDatasetId"]).iterate_items())

        # Follower results are partial, fetch full profiles
        usernames = [item.get("username") for item in items if item.get("username")]

        return self.scrape_profiles_by_username(usernames[:results_limit])

    def _parse_profile(self, data: dict) -> InstagramProfile:
        """Parse Apify response into InstagramProfile model."""
        return InstagramProfile(
            username=data.get("username", ""),
            user_id=str(data.get("id", data.get("pk", ""))),
            full_name=data.get("fullName", data.get("full_name", "")),
            biography=data.get("biography", data.get("bio", "")),
            follower_count=data.get("followersCount", data.get("follower_count", 0)),
            following_count=data.get("followsCount", data.get("following_count", 0)),
            post_count=data.get("postsCount", data.get("media_count", 0)),
            is_verified=data.get("verified", data.get("is_verified", False)),
            is_business=data.get("isBusinessAccount", data.get("is_business", False)),
            profile_pic_url=data.get("profilePicUrl", data.get("profile_pic_url", "")),
            external_url=data.get("externalUrl", data.get("external_url")),
            scraped_at=datetime.now(),
        )
