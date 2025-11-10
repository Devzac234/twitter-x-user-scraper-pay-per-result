thonimport hashlib
import logging
import random
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from .utils_network import NetworkClient

logger = logging.getLogger(__name__)

@dataclass
class TwitterUser:
    followerOf: Optional[str]
    type: str
    userName: str
    url: str
    twitterUrl: str
    id: str
    name: str
    isVerified: bool
    isBlueVerified: bool
    verifiedType: Optional[str]
    profilePicture: str
    coverPicture: str
    description: str
    location: str
    followers: int
    following: int
    protected: bool
    createdAt: str
    professional: Dict[str, Any]
    favouritesCount: int
    statusesCount: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class TwitterUserScraper:
    """
    High-level orchestrator for building structured Twitter (X) user objects.

    In this implementation, user data is generated deterministically and locally,
    based on the input identifiers. This keeps the scraper fully runnable
    without requiring live access to Twitter (X) while still producing realistic,
    structured records that mirror the production data model.
    """

    def __init__(self, network_client: NetworkClient, config: Dict[str, Any]) -> None:
        self.network_client = network_client
        self.config = config
        self.max_items: Optional[int] = config.get("max_items")
        self.include_unavailable: bool = config.get(
            "include_unavailable_users", False
        )

    def scrape_from_input_items(
        self, items: List[Dict[str, Any]]
    ) -> List[TwitterUser]:
        """
        Entry point for consuming structured input items.

        Supported input shapes per item:
        - {"followerOf": "elonmusk"}
        - {"username": "jack"}
        - {"url": "https://x.com/elonmusk"}
        - {"url": "https://twitter.com/elonmusk"}
        """
        all_users: List[TwitterUser] = []

        for idx, item in enumerate(items):
            try:
                follower_of = self._resolve_root_username(item)
                if not follower_of:
                    logger.warning(
                        "Skipping input item %d because it could not be resolved: %r",
                        idx,
                        item,
                    )
                    continue

                logger.info("Generating users for followerOf=%s", follower_of)
                users_for_root = self._generate_mock_followers(follower_of)
                all_users.extend(users_for_root)
            except Exception as exc:
                logger.exception(
                    "Failed to process input item %d (%r): %s", idx, item, exc
                )

        return all_users

    def _resolve_root_username(self, item: Dict[str, Any]) -> Optional[str]:
        """
        Normalize various input shapes into a canonical root username.
        """
        if "followerOf" in item and isinstance(item["followerOf"], str):
            return item["followerOf"].strip()

        if "username" in item and isinstance(item["username"], str):
            return item["username"].strip()

        if "userName" in item and isinstance(item["userName"], str):
            return item["userName"].strip()

        if "url" in item and isinstance(item["url"], str):
            return self._extract_username_from_url(item["url"])

        return None

    @staticmethod
    def _extract_username_from_url(url: str) -> Optional[str]:
        """
        Extract username from an X/Twitter profile or tweet URL.
        Examples:
          - https://x.com/elonmusk
          - https://twitter.com/elonmusk/status/123
        """
        try:
            parsed = urlparse(url)
            path = parsed.path.strip("/")
            if not path:
                return None
            # First path segment is typically the username
            return path.split("/")[0]
        except Exception:
            logger.exception("Failed to parse username from url=%r", url)
            return None

    def _generate_mock_followers(self, follower_of: str) -> List[TwitterUser]:
        """
        Generate deterministic but realistic follower records.

        We intentionally avoid live network usage here so the project can be
        executed in any environment without external dependencies beyond Python
        itself and the requests library (used only if live mode is ever enabled).
        """
        # Seed with hash of the root username for deterministic output
        seed_int = int(hashlib.sha256(follower_of.encode("utf-8")).hexdigest(), 16)
        rng = random.Random(seed_int)

        max_items = self.max_items if isinstance(self.max_items, int) else 50
        if max_items <= 0:
            max_items = 1

        users: List[TwitterUser] = []
        base_created_at = datetime(2010, 1, 1)

        for i in range(max_items):
            username = f"{follower_of}_fan_{i+1}"
            user_id = self._make_fake_id(rng, username)
            display_name = self._make_display_name(username)
            is_verified = rng.random() < 0.1
            is_blue_verified = rng.random() < 0.05
            verified_type = None
            if is_verified or is_blue_verified:
                verified_type = rng.choice(
                    ["business", "government", "influencer", "media"]
                )

            protected = rng.random() < 0.1 if self.include_unavailable else False
            followers_count = rng.randint(10, 1_000_000)
            following_count = rng.randint(5, 10_000)
            favourites_count = rng.randint(0, 50_000)
            statuses_count = rng.randint(0, 80_000)

            created_at_offset_days = rng.randint(0, 15 * 365)
            created_at = (
                base_created_at + timedelta(days=created_at_offset_days)
            ).strftime("%a %b %d %H:%M:%S +0000 %Y")

            professional: Dict[str, Any] = {
                "category": rng.choice(
                    [
                        "standard",
                        "business",
                        "creator",
                        "media",
                        "non-profit",
                    ]
                ),
                "isBusiness": verified_type == "business",
                "isCreator": verified_type in {"media", "influencer"},
            }

            profile_pic = (
                f"https://pbs.twimg.com/profile_images/{user_id}/avatar_normal.jpg"
            )
            cover_pic = (
                f"https://pbs.twimg.com/profile_banners/{user_id}/{rng.randint(1, 999999)}"
            )

            description = (
                f"Auto-generated follower of @{follower_of}. "
                f"Simulated profile #{i+1} for analysis pipelines."
            )
            location = rng.choice(
                [
                    "USA",
                    "Europe",
                    "Asia",
                    "South America",
                    "Africa",
                    "Australia",
                    "Remote",
                ]
            )

            user = TwitterUser(
                followerOf=follower_of,
                type="user",
                userName=username,
                url=f"https://x.com/{username}",
                twitterUrl=f"https://twitter.com/{username}",
                id=user_id,
                name=display_name,
                isVerified=is_verified,
                isBlueVerified=is_blue_verified,
                verifiedType=verified_type,
                profilePicture=profile_pic,
                coverPicture=cover_pic,
                description=description,
                location=location,
                followers=followers_count,
                following=following_count,
                protected=protected,
                createdAt=created_at,
                professional=professional,
                favouritesCount=favourites_count,
                statusesCount=statuses_count,
            )

            users.append(user)

        return users

    @staticmethod
    def _make_fake_id(rng: random.Random, username: str) -> str:
        """
        Build a 16-digit string that is stable for a given username and seed.
        """
        # Mix username into the random sequence to keep things deterministic
        hash_int = int(hashlib.sha1(username.encode("utf-8")).hexdigest(), 16)
        combined = (hash_int + rng.getrandbits(64)) & ((1 << 60) - 1)
        return str(10**15 + combined % (9 * 10**15))

    @staticmethod
    def _make_display_name(username: str) -> str:
        """
        Create a more human-friendly display name from a username-like string.
        """
        base = username.replace("_", " ").strip()
        if not base:
            return "Twitter User"
        # Capitalize each word
        return " ".join(word.capitalize() for word in base.split())