from __future__ import annotations

import json
from typing import Any
from urllib.request import Request, urlopen


def fetch_live_matches_with_scores(api_key: str, api_host: str) -> list[dict[str, Any]]:
    live_payload = _get_json(f"https://{api_host}/matches/v1/live", api_key, api_host)
    matches = _extract_live_matches(live_payload)

    enriched_matches: list[dict[str, Any]] = []
    for match in matches:
        match_id = match.get("match_id")
        if not match_id:
            continue
        try:
            scorecard_payload = _get_json(
                f"https://{api_host}/mcenter/v1/{match_id}/hscard",
                api_key,
                api_host,
            )
            match["score"] = _extract_score_from_hscard(scorecard_payload)
            match["status"] = _extract_status_from_hscard(scorecard_payload, fallback=match["status"])
        except Exception:
            match["score"] = match.get("score") or "Score unavailable"
        enriched_matches.append(match)
    return enriched_matches


def _get_json(url: str, api_key: str, api_host: str) -> Any:
    request = Request(
        url,
        headers={
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": api_host,
            "Content-Type": "application/json",
        },
    )
    with urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def _extract_live_matches(payload: Any) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for node in _walk_nodes(payload):
        match_info = node.get("matchInfo")
        if not isinstance(match_info, dict):
            continue
        normalized = _normalize_match(node)
        if normalized:
            matches.append(normalized)
    return matches


def _walk_nodes(node: Any):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _walk_nodes(value)
    elif isinstance(node, list):
        for item in node:
            yield from _walk_nodes(item)


def _normalize_match(node: dict[str, Any]) -> dict[str, Any] | None:
    match_info = node.get("matchInfo", {})
    team1 = _team_name(match_info.get("team1"))
    team2 = _team_name(match_info.get("team2"))
    if not team1 or not team2:
        return None

    return {
        "match_id": match_info.get("matchId"),
        "series_name": (match_info.get("seriesName") or "").strip(),
        "match_desc": match_info.get("matchDesc") or match_info.get("matchFormat") or "",
        "team_a": team1,
        "team_b": team2,
        "status": (
            match_info.get("status")
            or match_info.get("stateTitle")
            or match_info.get("state")
            or "Status unavailable"
        ),
        "venue": ((match_info.get("venueInfo") or {}).get("ground")) or "",
        "score": _format_score(node.get("matchScore") or {}),
    }


def _team_name(team: Any) -> str | None:
    if not isinstance(team, dict):
        return None
    return team.get("teamName") or team.get("teamSName")


def _format_score(match_score: dict[str, Any]) -> str:
    innings_lines: list[str] = []
    for team_key in ("team1Score", "team2Score"):
        team_score = match_score.get(team_key)
        if not isinstance(team_score, dict):
            continue
        team_innings: list[str] = []
        for innings in team_score.values():
            if not isinstance(innings, dict):
                continue
            runs = innings.get("runs")
            if runs is None:
                continue
            wickets = innings.get("wickets")
            overs = innings.get("overs")
            line = str(runs)
            if wickets is not None:
                line += f"/{wickets}"
            if overs is not None:
                line += f" ({overs} ov)"
            team_innings.append(line)
        if team_innings:
            innings_lines.append(" | ".join(team_innings))
    return " vs ".join(innings_lines) if innings_lines else "Score unavailable"


def _extract_score_from_hscard(payload: Any) -> str:
    score_lines: list[str] = []
    if isinstance(payload, dict):
        for key in ("scoreCard", "scorecard", "scoreCardList"):
            score_cards = payload.get(key)
            if isinstance(score_cards, list):
                for innings in score_cards:
                    if not isinstance(innings, dict):
                        continue
                    title = innings.get("batTeamDetails", {}).get("batTeamName") or innings.get("inningsId")
                    score = innings.get("scoreDetails") or innings
                    runs = score.get("runs")
                    wickets = score.get("wickets")
                    overs = score.get("overs")
                    if runs is None:
                        continue
                    line = f"{title}: {runs}"
                    if wickets is not None:
                        line += f"/{wickets}"
                    if overs is not None:
                        line += f" ({overs} ov)"
                    score_lines.append(line)
    return " | ".join(score_lines) if score_lines else "Score unavailable"


def _extract_status_from_hscard(payload: Any, fallback: str) -> str:
    if isinstance(payload, dict):
        for key in ("status", "statusText", "matchStatus"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        match_header = payload.get("matchHeader")
        if isinstance(match_header, dict):
            for key in ("status", "stateTitle", "state"):
                value = match_header.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
    return fallback
