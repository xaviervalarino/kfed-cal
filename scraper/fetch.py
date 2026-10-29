"""Polite HTTP fetching: identifies itself, obeys robots.txt, and waits between requests."""

import time
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx

USER_AGENT = "kfed-cal/0.1 (+https://github.com/xaviervalarino/kfed-cal)"


class Fetcher:
    def __init__(self, delay=2.0):
        self.client = httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=30, follow_redirects=True)
        self.delay = delay
        self.last = 0.0
        self.robots = {}

    def get(self, url):
        if not self.allowed(url):
            raise PermissionError(f"robots.txt does not allow fetching {url}")
        wait = self.last + self.delay - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        try:
            response = self.client.get(url)
        finally:
            self.last = time.monotonic()
        response.raise_for_status()
        return response

    def allowed(self, url):
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
