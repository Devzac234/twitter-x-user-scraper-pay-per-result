thonimport logging
import time
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)

class NetworkError(RuntimeError):
    """Raised when the network client encounters an unrecoverable error."""

class NetworkClient:
    """
    Thin wrapper around HTTP access with retries and logging.

    By default, this client runs in "offline" mode (enable_live=False) and
    will refuse to make outbound HTTP calls. This keeps the scraper runnable
    in restricted environments and avoids unintentional traffic.

    If you explicitly turn on live mode via config, the same client can be used
    to pull JSON or text responses from public HTTP endpoints.
    """

    def __init__(
        self,
        timeout: int = 10,
        max_retries: int = 3,
        user_agent: str = "TwitterUserScraper/1.0",
        enable_live: bool = False,
    ) -> None:
        self.timeout = timeout
        self.max_retries = max_retries
        self.user_agent = user_agent
        self.enable_live = enable_live

        self._session = requests.Session()
        self._session.headers.update({"User-Agent": self.user_agent})

    def _check_live(self) -> None:
        if not self.enable_live:
            raise NetworkError(
                "Live HTTP access is disabled. Set enable_live=True in the config "
                "if you intend to fetch real data from the network."
            )

    def _request_with_retries(
        self, method: str, url: str, **kwargs: Any
    ) -> requests.Response:
        self._check_live()
        last_exc: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.debug(
                    "HTTP %s %s (attempt %d/%d)",
                    method,
                    url,
                    attempt,
                    self.max_retries,
                )
                response = self._session.request(
                    method=method, url=url, timeout=self.timeout, **kwargs
                )
                if response.status_code >= 500:
                    raise NetworkError(
                        f"Server error {response.status_code} for URL {url}"
                    )
                return response
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "HTTP %s %s failed on attempt %d/%d: %s",
                    method,
                    url,
                    attempt,
                    self.max_retries,
                    exc,
                )
                if attempt < self.max_retries:
                    sleep_for = 2**attempt * 0.25
                    time.sleep(sleep_for)

        raise NetworkError(
            f"Failed to perform HTTP {method} {url} after {self.max_retries} retries"
        ) from last_exc

    def get_json(self, url: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Retrieve JSON from an HTTP endpoint with retries.
        """
        response = self._request_with_retries("GET", url, params=params)
        try:
            return response.json()
        except Exception as exc:
            raise NetworkError(
                f"Failed to decode JSON response from {url}: {exc}"
            ) from exc

    def get_text(self, url: str, params: Optional[Dict[str, Any]] = None) -> str:
        """
        Retrieve text from an HTTP endpoint with retries.
        """
        response = self._request_with_retries("GET", url, params=params)
        return response.text