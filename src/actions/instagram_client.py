"""Instagram client for automated actions using instagrapi."""

import os
import random
import time
from pathlib import Path
from typing import Optional
import structlog
from instagrapi import Client
from instagrapi.exceptions import (
    LoginRequired,
    ChallengeRequired,
    FeedbackRequired,
    PleaseWaitFewMinutes,
)

from ..models import InstagramProfile, OutreachResult

logger = structlog.get_logger()


class InstagramClient:
    """
    Instagram client for automated actions.

    Handles:
    - Login with session persistence
    - Liking posts
    - Sending direct messages
    - Rate limiting and safety delays
    """

    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        session_path: str = "session",
        min_delay: int = 30,
        max_delay: int = 90,
    ):
        """
        Initialize Instagram client.

        Args:
            username: Instagram username (or INSTAGRAM_USERNAME env var)
            password: Instagram password (or INSTAGRAM_PASSWORD env var)
            session_path: Path to store session files
            min_delay: Minimum delay between actions (seconds)
            max_delay: Maximum delay between actions (seconds)
        """
        self.username = username or os.getenv("INSTAGRAM_USERNAME")
        self.password = password or os.getenv("INSTAGRAM_PASSWORD")

        if not self.username or not self.password:
            raise ValueError("Instagram credentials required. Set INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD.")

        self.session_path = Path(session_path)
        self.session_path.mkdir(exist_ok=True)
        self.session_file = self.session_path / f"{self.username}.json"

        self.min_delay = min_delay
        self.max_delay = max_delay

        self.client = Client()
        self._configure_client()

        logger.info("Initialized Instagram client", username=self.username)

    def _configure_client(self) -> None:
        """Configure client settings for safety."""
        # Set realistic device settings
        self.client.set_device({
            "app_version": "269.0.0.18.75",
            "android_version": 26,
            "android_release": "8.0.0",
            "dpi": "480dpi",
            "resolution": "1080x1920",
            "manufacturer": "OnePlus",
            "device": "devitron",
            "model": "6T Dev",
            "cpu": "qcom",
            "version_code": "314665256",
        })

        # Set delays
        self.client.delay_range = [self.min_delay, self.max_delay]

    def login(self) -> bool:
        """
        Login to Instagram, using cached session if available.

        Returns:
            True if login successful
        """
        # Try to load existing session
        if self.session_file.exists():
            try:
                logger.info("Loading existing session")
                self.client.load_settings(self.session_file)
                self.client.login(self.username, self.password)

                # Verify session is valid
                self.client.get_timeline_feed()
                logger.info("Session loaded successfully")
                return True

            except LoginRequired:
                logger.warning("Session expired, performing fresh login")
            except Exception as e:
                logger.warning("Failed to load session", error=str(e))

        # Fresh login
        try:
            logger.info("Performing fresh login")
            self.client.login(self.username, self.password)
            self.client.dump_settings(self.session_file)
            logger.info("Login successful, session saved")
            return True

        except ChallengeRequired as e:
            logger.error("Challenge required - manual verification needed", error=str(e))
            raise
        except Exception as e:
            logger.error("Login failed", error=str(e))
            raise

    def like_recent_posts(
        self,
        username: str,
        count: int = 3,
    ) -> int:
        """
        Like recent posts from a user.

        Args:
            username: Target username
            count: Number of posts to like

        Returns:
            Number of posts successfully liked
        """
        logger.info("Liking recent posts", target=username, count=count)

        try:
            # Get user ID
            user_id = self.client.user_id_from_username(username)
            self._random_delay()

            # Get recent posts
            medias = self.client.user_medias(user_id, amount=count)

            liked = 0
            for media in medias[:count]:
                try:
                    self.client.media_like(media.pk)
                    liked += 1
                    logger.debug("Liked post", username=username, media_id=media.pk)
                    self._random_delay()

                except FeedbackRequired as e:
                    logger.warning("Rate limited while liking", error=str(e))
                    break
                except Exception as e:
                    logger.warning("Failed to like post", error=str(e))

            logger.info("Liked posts", target=username, count=liked)
            return liked

        except PleaseWaitFewMinutes:
            logger.warning("Instagram requesting wait - rate limited")
            time.sleep(300)  # Wait 5 minutes
            return 0
        except Exception as e:
            logger.error("Failed to like posts", target=username, error=str(e))
            return 0

    def send_direct_message(
        self,
        username: str,
        message: str,
    ) -> bool:
        """
        Send a direct message to a user.

        Args:
            username: Target username
            message: Message to send

        Returns:
            True if message sent successfully
        """
        logger.info("Sending direct message", target=username)

        try:
            # Get user ID
            user_id = self.client.user_id_from_username(username)
            self._random_delay()

            # Send message
            self.client.direct_send(message, [user_id])

            logger.info("Direct message sent", target=username)
            return True

        except FeedbackRequired as e:
            logger.warning("Rate limited while sending DM", error=str(e))
            return False
        except PleaseWaitFewMinutes:
            logger.warning("Instagram requesting wait - rate limited")
            time.sleep(300)
            return False
        except Exception as e:
            logger.error("Failed to send DM", target=username, error=str(e))
            return False

    def outreach_to_profile(
        self,
        profile: InstagramProfile,
        message_template: str,
        likes_count: int = 3,
    ) -> OutreachResult:
        """
        Perform full outreach to a profile: like posts + send DM.

        Args:
            profile: Target profile
            message_template: DM message (can use {name} placeholder)
            likes_count: Number of posts to like

        Returns:
            OutreachResult with action details
        """
        result = OutreachResult(profile=profile)

        try:
            # First, like their recent posts
            result.photos_liked = self.like_recent_posts(
                profile.username,
                count=likes_count,
            )

            # Wait before sending DM
            self._random_delay(multiplier=2)

            # Personalize message
            name = profile.full_name.split()[0] if profile.full_name else profile.username
            message = message_template.replace("{name}", name)
            message = message.replace("{username}", profile.username)

            # Send DM
            result.dm_sent = self.send_direct_message(profile.username, message)
            result.dm_message = message
            result.success = result.photos_liked > 0 or result.dm_sent

            logger.info(
                "Outreach completed",
                target=profile.username,
                likes=result.photos_liked,
                dm_sent=result.dm_sent,
            )

        except Exception as e:
            result.error = str(e)
            logger.error("Outreach failed", target=profile.username, error=str(e))

        return result

    def _random_delay(self, multiplier: float = 1.0) -> None:
        """Add a random delay between actions."""
        delay = random.uniform(self.min_delay * multiplier, self.max_delay * multiplier)
        logger.debug("Waiting", seconds=round(delay, 1))
        time.sleep(delay)

    def logout(self) -> None:
        """Logout and save session."""
        try:
            self.client.dump_settings(self.session_file)
            logger.info("Session saved")
        except Exception as e:
            logger.warning("Failed to save session", error=str(e))
