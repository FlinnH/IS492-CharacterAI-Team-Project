"""Checks the public demo after a deploy, from this computer.

Run it from the repo root with the demo's address:

    app/.venv/bin/python app/scripts/check_link.py https://your-demo.onrender.com

It asks the demo what a visitor's browser would ask, with no demo code: the
health address, the page, the two sample chats and their flags, and a few
requests the demo must refuse. It makes no model call, types nothing, and
prints one line per check. A free Render service that was asleep takes about
a minute to answer the first request, so the first check waits up to 90 seconds.
docs/deployment.md says what to do when a check fails.
"""

import json
import sys
import urllib.error
import urllib.request
from collections.abc import Callable

# (status, headers with lowercase names, body text) for one request.
Answer = tuple[int, dict[str, str], str]
Fetch = Callable[..., Answer]

COOKIE = "workbench_visitor"
OTHER_SITE = "https://another-site.example"


def data(text: str):
    """The body as JSON, or None when it isn't."""
    try:
        return json.loads(text)
    except ValueError:
        return None


def check(fetch: Fetch, site: str) -> list[tuple[bool, str]]:
    """Runs every check and returns (passed, line) for each.

    fetch(method, path, headers) sends one request to the demo. site is the
    demo's own address, like https://your-demo.onrender.com, which a browser
    sends as Origin.
    """
    results: list[tuple[bool, str]] = []

    def record(passed: bool, line: str) -> bool:
        results.append((bool(passed), line))
        return bool(passed)

    status, _, body = fetch("GET", "/api/health", {})
    health = data(body) or {}
    if not record(status == 200 and health.get("status") == "ok", f"The health address answers ok (HTTP {status})."):
        return results
    record(health.get("mode") == "demo", "The service runs in demo mode (WORKBENCH_MODE=demo).")
    record(health.get("key_set") is True, "A Gemini key is set (GEMINI_API_KEY on Render).")

    status, headers, body = fetch("GET", "/", {})
    record(status == 200 and "demo.js" in body, f"The page loads with the demo banner's script (HTTP {status}).")
    cookie = headers.get("set-cookie", "")
    flags = cookie.lower()
    record(
        cookie.startswith(f"{COOKIE}=") and "httponly" in flags and "secure" in flags and "samesite=lax" in flags,
        "The visitor cookie is HttpOnly, Secure, and SameSite=Lax.",
    )
    visitor = {"Cookie": cookie.split(";", 1)[0]} if cookie else {}

    status, _, body = fetch("GET", "/api/chats", visitor)
    chats = data(body) if status == 200 else None
    titles = sorted(chat["title"] for chat in chats) if isinstance(chats, list) else []
    record(len(titles) == 2, f"A new visitor starts with the two sample chats: {', '.join(titles) or 'none found'}.")

    status, _, body = fetch("GET", "/api/review", visitor)
    review = data(body) if status == 200 else None
    counts = {item["chat"]["title"]: len(item["flags"]) for item in review["chats"]} if isinstance(review, dict) else {}
    shown = ", ".join(f"{title} has {count}" for title, count in sorted(counts.items())) or "none found"
    record(len(counts) == 2 and all(counts.values()), f"Both samples show their saved flags with no model call: {shown}.")

    flag_id = next((flag["id"] for item in (review or {}).get("chats", []) for flag in item["flags"]), None)
    if flag_id is not None:
        path = f"/api/flags/{flag_id}/evidence"
        status, _, _ = fetch("POST", path, {**visitor, "Origin": site})
        record(status == 200, f"Show in context works with no code, from the demo's own page (HTTP {status}).")
        status, _, _ = fetch("POST", path, {**visitor, "Origin": OTHER_SITE})
        record(status == 403, f"The same request from another site's page is refused (HTTP {status}).")

    start = json.dumps({"character": "harry", "scenario": "F2", "model": "none"})
    status, _, body = fetch("POST", "/api/chats", {**visitor, "Origin": site, "Content-Type": "application/json"}, start)
    record(status == 403 and "demo code" in body, f"Starting a test case with no demo code is refused (HTTP {status}).")

    status, _, _ = fetch("GET", "/api/settings", visitor)
    record(status == 403, f"Settings is off (HTTP {status}).")
    return results


def http_fetch(base: str, timeout: float = 90.0) -> Fetch:
    """A fetch that sends real requests to the demo at base."""

    def fetch(method: str, path: str, headers: dict[str, str], body: str | None = None) -> Answer:
        request = urllib.request.Request(
            f"{base}{path}",
            data=body.encode("utf-8") if body is not None else (b"" if method == "POST" else None),
            headers={"User-Agent": "workbench-check-link", **headers},
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.status, {name.lower(): value for name, value in response.headers.items()}, response.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as error:
            return error.code, {name.lower(): value for name, value in error.headers.items()}, error.read().decode("utf-8", "replace")

    return fetch


def main(argv: list[str]) -> int:
    if len(argv) != 2 or not argv[1].startswith(("https://", "http://")):
        print("Give the demo's address, like: app/.venv/bin/python app/scripts/check_link.py https://your-demo.onrender.com")
        return 2
    base = argv[1].rstrip("/")
    print(f"Checking {base}. A sleeping demo takes about a minute to wake.")
    try:
        results = check(http_fetch(base), base)
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        print(f"FAIL  The demo didn't answer: {error}. Wait a minute and run this again.")
        return 1
    for passed, line in results:
        print(f"{'ok  ' if passed else 'FAIL'}  {line}")
    failed = sum(not passed for passed, _ in results)
    print("Every check passed." if not failed else f"{failed} of {len(results)} checks failed. See docs/deployment.md.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
