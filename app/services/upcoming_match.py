from __future__ import annotations

import re
from html import unescape
from typing import Any
from urllib.request import Request, urlopen


IPL_MATCHES_URL = "https://www.ipl.com/cricket-matches"


def fetch_upcoming_ipl_match() -> dict[str, Any] | None:
    request = Request(
        IPL_MATCHES_URL,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36"
            )
        },
    )
    with urlopen(request, timeout=15) as response:
        html = response.read().decode("utf-8", errors="ignore")

    cleaned = unescape(re.sub(r"\s+", " ", html))
    pattern = re.compile(
        r"Indian Premier League 20\d{2}.+?"
        r"([A-Za-z][A-Za-z .'-]+?)\s+\1.+?Upcoming.+?"
        r"(?:Match starts at [^<]+ )?(?P<date>[A-Za-z]+ \d{1,2}, 20\d{2} \d{1,2}:\d{2} [ap]m).+?"
        r"([A-Za-z][A-Za-z .'-]+?)\s+\2",
        re.IGNORECASE,
    )
    match = pattern.search(cleaned)
    if not match:
        return None

    teams = re.findall(
        r"Indian Premier League 20\d{2}.+?([A-Za-z][A-Za-z .'-]+?)\s+\1.+?Upcoming.+?"
        r"(?:Match starts at [^<]+ )?[A-Za-z]+ \d{1,2}, 20\d{2} \d{1,2}:\d{2} [ap]m.+?"
        r"([A-Za-z][A-Za-z .'-]+?)\s+\2",
        cleaned,
        re.IGNORECASE,
    )
    if not teams:
        return None

    team_a, team_b = teams[0]
    return {
        "team_a": team_a.strip(),
        "team_b": team_b.strip(),
        "start_time_local": match.group("date").strip(),
        "source_url": IPL_MATCHES_URL,
    }
