"""Polite HTTP fetching: identifies itself, obeys robots.txt, and waits between requests."""

import time
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx

# MusicBrainz asks for "App/version ( contact-url )", Wikimedia for a contact and the word "bot".
USER_AGENT = "kfed-cal-bot/0.1 (+https://github.com/xaviervalarino/kfed-cal)"
# Documented APIs used under their published rules for apps. Their robots.txt files disallow these paths for
# crawlers, so they skip the robots check (README, "Scraping politely"). List API prefixes only, never a site's pages.
ROBOTS_EXCEPTIONS = (
    "https://musicbrainz.org/ws/2/",
    "https://en.wikipedia.org/api/rest_v1/",
    # Wikidata's robots.txt allows this path, but Python 3.13's parser reads its earlier "Disallow: /wiki/Special:".
    "https://www.wikidata.org/wiki/Special:EntityData/",
)


class Fetcher:
    def __init__(self, delay=2.0):
        self.client = httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=30, follow_redirects=True)
        self.delay = delay
        self.last = 0.0
        self.robots = {}

    def get(self, url, params=None, headers=None):
        """GET url. Pass query values (and API keys) in params: error messages leave them out."""
        return self.request("GET", url, params, headers)

    def post(self, url, headers=None):
        """POST to url with no body (how Tessera's ticket API starts a visitor session)."""
        return self.request("POST", url, None, headers)

    def request(self, method, url, params, headers):
        if not self.allowed(url):
            raise PermissionError(f"robots.txt does not allow fetching {url}")
        wait = self.last + self.delay - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        try:
            response = self.client.request(method, url, params=params, headers=headers)
        finally:
            self.last = time.monotonic()
        if is_challenge(response):
            # Never try to get past it (fake User-Agent, browser): use another source for this venue.
            raise PermissionError(f"{urlsplit(url).netloc} sent a bot challenge instead of the page. Use another source.")
        if response.is_error:
            raise httpx.HTTPStatusError(f"{url} answered {response.status_code} {response.reason_phrase}.",
                                        request=response.request, response=response)
        return response

    def allowed(self, url):
        if url.startswith(ROBOTS_EXCEPTIONS):
            return True
        parts = urlsplit(url)
        base = f"{parts.scheme}://{parts.netloc}"
        if base not in self.robots:
            parser = RobotFileParser()
            try:
                r = self.client.get(base + "/robots.txt")
                parser.parse(r.text.splitlines() if r.status_code == 200 else [])
            except httpx.HTTPError:
                parser.parse([])
            self.robots[base] = parser
        return self.robots[base].can_fetch(USER_AGENT, url)


def is_challenge(response):
    """True for a Cloudflare-style bot challenge page."""
    if response.headers.get("cf-mitigated") == "challenge":
        return True
    # Normal Cloudflare pages also load challenge-platform scripts, so only trust the markup on an error status.
    return response.status_code in (403, 429, 503) and any(
        m in response.text for m in ("<title>Just a moment...</title>", "challenge-platform", "cf-chl"))
