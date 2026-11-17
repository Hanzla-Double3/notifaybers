"""The only HTTP client an adapter gets.

It refuses hosts the adapter did not declare, follows no redirect off those hosts,
caps the response size and time, and lets cookies travel from the first `fetch()`
call to the second through the Challenge state.
"""

from __future__ import annotations

from urllib.parse import urlparse

import httpx

from app.bills.base import Adapter, BillError

MAX_BYTES = 2_000_000
TIMEOUT_SECONDS = 20
USER_AGENT = "Mozilla/5.0 (compatible; Notifaybers bill check; +https://github.com/)"


class PolicyClient:
    def __init__(self, adapter: type[Adapter] | Adapter, cookies: dict | None = None, transport=None):
        self._allowed = {h.lower() for h in adapter.allowed_hosts}
        if not self._allowed:
            raise ValueError(f"adapter {adapter.id!r} declares no allowed_hosts")
        self._client = httpx.Client(
            timeout=TIMEOUT_SECONDS,
            follow_redirects=False,
            headers={"User-Agent": USER_AGENT},
            cookies=cookies or {},
            transport=transport,  # tests pass a fake one; leave None in the app
        )

    # -- cookies travel between the two steps through the Challenge state ------
    def export_cookies(self) -> dict:
        return dict(self._client.cookies.items())

    def _check(self, url: str) -> None:
        parts = urlparse(url)
        if parts.scheme != "https" or (parts.hostname or "").lower() not in self._allowed:
            raise BillError(f"This adapter may not contact {parts.hostname or url!r}")

    def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        for _ in range(5):  # follow redirects by hand so each hop is checked
            self._check(url)
            try:
                response = self._client.request(method, url, **kwargs)
            except httpx.HTTPError as exc:
                raise BillError(f"Could not reach the portal ({exc.__class__.__name__})") from exc
            if len(response.content) > MAX_BYTES:
                raise BillError("The portal's answer was unexpectedly large")
            if response.is_redirect and response.headers.get("location"):
                url = str(response.url.join(response.headers["location"]))
                method, kwargs = "GET", {}
                continue
            return response
        raise BillError("The portal redirected too many times")

    def get(self, url: str, **kwargs) -> httpx.Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs) -> httpx.Response:
        return self.request("POST", url, **kwargs)

    def close(self) -> None:
        self._client.close()
