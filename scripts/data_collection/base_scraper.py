"""
Base scraper class providing common functionality for all source-specific scrapers.

Features:
- Rate limiting with configurable delays
- Retry with exponential backoff (via tenacity)
- robots.txt compliance
- Checksum-based change detection
- Incremental downloads (skip existing files)
- Progress logging
- Consistent file naming and metadata
"""

import hashlib
import json
import time
import abc
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from scripts.data_collection.config import (
    RAW_DIR,
    DEFAULT_DELAY,
    MAX_RETRIES,
    RETRY_BACKOFF_BASE,
    REQUEST_TIMEOUT,
)
from scripts.data_collection.logger import get_logger


class BaseScraper(abc.ABC):
    """
    Abstract base class for all data collection scrapers.

    Subclasses must implement:
        - source_name (property): unique identifier for this source
        - collect(self) -> dict: main collection logic returning stats
    """

    def __init__(self, delay: float = DEFAULT_DELAY):
        self.delay = delay
        self.logger = get_logger(f"scraper.{self.source_name}")
        self.output_dir = RAW_DIR / self.source_name
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._last_request_time: dict[str, float] = {}
        self._robot_parsers: dict[str, RobotFileParser] = {}
        self._session = self._build_session()
        self.stats = {
            "source": self.source_name,
            "started_at": None,
            "completed_at": None,
            "files_downloaded": 0,
            "files_skipped": 0,
            "errors": 0,
            "total_bytes": 0,
        }

    @property
    @abc.abstractmethod
    def source_name(self) -> str:
        """Unique identifier for this scraper's source category."""
        ...

    @abc.abstractmethod
    def collect(self) -> dict:
        """
        Execute the collection process.

        Returns:
            dict with collection statistics.
        """
        ...

    # ──────────────────────────────────────────
    # HTTP Session
    # ──────────────────────────────────────────

    def _build_session(self) -> requests.Session:
        """Create a requests session with retry logic and polite headers."""
        session = requests.Session()

        retry_strategy = Retry(
            total=MAX_RETRIES,
            backoff_factor=RETRY_BACKOFF_BASE,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "HEAD"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        session.headers.update({
            "User-Agent": (
                "ValorAssist-DataCollector/1.0 "
                "(Veterans Legal Knowledge Base; "
                "educational/non-commercial; "
                "https://github.com/genregod/Claude-vet-AI-)"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
        })

        return session

    # ──────────────────────────────────────────
    # Rate limiting
    # ──────────────────────────────────────────

    def _rate_limit(self, domain: str) -> None:
        """Enforce minimum delay between requests to the same domain."""
        now = time.monotonic()
        last = self._last_request_time.get(domain, 0)
        elapsed = now - last
        if elapsed < self.delay:
            sleep_time = self.delay - elapsed
            self.logger.debug(f"Rate limiting: sleeping {sleep_time:.1f}s for {domain}")
            time.sleep(sleep_time)
        self._last_request_time[domain] = time.monotonic()

    # ──────────────────────────────────────────
    # robots.txt compliance
    # ──────────────────────────────────────────

    def _check_robots(self, url: str) -> bool:
        """Check if the URL is allowed by robots.txt."""
        parsed = urlparse(url)
        domain = f"{parsed.scheme}://{parsed.netloc}"

        if domain not in self._robot_parsers:
            rp = RobotFileParser()
            robots_url = f"{domain}/robots.txt"
            try:
                rp.set_url(robots_url)
                rp.read()
            except Exception:
                # If we can't read robots.txt, assume allowed
                self.logger.debug(f"Could not read robots.txt for {domain}, proceeding")
                rp = None
            self._robot_parsers[domain] = rp

        rp = self._robot_parsers[domain]
        if rp is None:
            return True

        user_agent = "ValorAssist-DataCollector"
        allowed = rp.can_fetch(user_agent, url)
        if not allowed:
            self.logger.warning(f"Blocked by robots.txt: {url}")
        return allowed

    # ──────────────────────────────────────────
    # HTTP requests
    # ──────────────────────────────────────────

    def fetch(self, url: str, params: Optional[dict] = None,
              respect_robots: bool = True) -> Optional[requests.Response]:
        """
        Fetch a URL with rate limiting, robots.txt check, and retries.

        Args:
            url: The URL to fetch.
            params: Optional query parameters.
            respect_robots: Whether to check robots.txt.

        Returns:
            requests.Response or None if blocked/failed.
        """
        if respect_robots and not self._check_robots(url):
            return None

        domain = urlparse(url).netloc
        self._rate_limit(domain)

        try:
            response = self._session.get(url, params=params, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request failed for {url}: {e}")
            self.stats["errors"] += 1
            return None

    def fetch_with_retry(self, url: str, params: Optional[dict] = None,
                         max_attempts: int = MAX_RETRIES) -> Optional[requests.Response]:
        """Fetch with explicit tenacity retry wrapper for critical requests."""
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=RETRY_BACKOFF_BASE, min=2, max=60),
            retry=retry_if_exception_type(requests.exceptions.RequestException),
        )
        def _do_fetch():
            domain = urlparse(url).netloc
            self._rate_limit(domain)
            resp = self._session.get(url, params=params, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            return resp

        try:
            return _do_fetch()
        except Exception as e:
            self.logger.error(f"All retries exhausted for {url}: {e}")
            self.stats["errors"] += 1
            return None

    # ──────────────────────────────────────────
    # File management
    # ──────────────────────────────────────────

    @staticmethod
    def compute_hash(content: bytes) -> str:
        """Compute SHA-256 hash of content."""
        return hashlib.sha256(content).hexdigest()

    def file_exists(self, filename: str) -> bool:
        """Check if a file already exists in the output directory."""
        return (self.output_dir / filename).exists()

    def save_file(self, filename: str, content: bytes | str,
                  metadata: Optional[dict] = None, force: bool = False) -> Optional[Path]:
        """
        Save content to the output directory with optional metadata sidecar.

        Args:
            filename: Name for the output file.
            content: File content (bytes or str).
            metadata: Optional metadata dict to save as .meta.json sidecar.
            force: If True, overwrite existing files.

        Returns:
            Path to saved file, or None if skipped.
        """
        filepath = self.output_dir / filename

        if isinstance(content, str):
            content_bytes = content.encode("utf-8")
        else:
            content_bytes = content

        content_hash = self.compute_hash(content_bytes)

        # Check for existing file with same hash (no changes)
        meta_path = self.output_dir / f"{filename}.meta.json"
        if not force and filepath.exists() and meta_path.exists():
            try:
                existing_meta = json.loads(meta_path.read_text())
                if existing_meta.get("sha256") == content_hash:
                    self.logger.debug(f"Skipping unchanged file: {filename}")
                    self.stats["files_skipped"] += 1
                    return None
            except (json.JSONDecodeError, KeyError):
                pass

        # Write content
        if isinstance(content, str):
            filepath.write_text(content, encoding="utf-8")
        else:
            filepath.write_bytes(content)

        # Write metadata sidecar
        meta = {
            "filename": filename,
            "source": self.source_name,
            "sha256": content_hash,
            "size_bytes": len(content_bytes),
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "word_count": len(content_bytes.decode("utf-8", errors="ignore").split()),
        }
        if metadata:
            meta.update(metadata)
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

        self.stats["files_downloaded"] += 1
        self.stats["total_bytes"] += len(content_bytes)
        self.logger.info(f"Saved: {filename} ({len(content_bytes):,} bytes)")
        return filepath

    # ──────────────────────────────────────────
    # Lifecycle
    # ──────────────────────────────────────────

    def run(self) -> dict:
        """Execute the full collection process with timing and error handling."""
        self.stats["started_at"] = datetime.now(timezone.utc).isoformat()
        self.logger.info(f"={'=' * 60}")
        self.logger.info(f"Starting collection: {self.source_name}")
        self.logger.info(f"Output directory: {self.output_dir}")
        self.logger.info(f"={'=' * 60}")

        try:
            result = self.collect()
            if isinstance(result, dict):
                self.stats.update(result)
        except Exception as e:
            self.logger.exception(f"Collection failed for {self.source_name}: {e}")
            self.stats["errors"] += 1

        self.stats["completed_at"] = datetime.now(timezone.utc).isoformat()
        self.logger.info(
            f"Collection complete: {self.source_name} | "
            f"Downloaded: {self.stats['files_downloaded']} | "
            f"Skipped: {self.stats['files_skipped']} | "
            f"Errors: {self.stats['errors']} | "
            f"Total bytes: {self.stats['total_bytes']:,}"
        )
        return self.stats

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} source={self.source_name}>"
