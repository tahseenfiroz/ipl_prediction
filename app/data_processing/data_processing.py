from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


TEAM_COLUMNS = ("first_batting_team", "second_batting_team")


@dataclass(frozen=True)
class TeamSnapshot:
    team: str
    matches: int
    wins: int
    losses: int
    win_rate: float
    batting_first_matches: int
    batting_first_wins: int
    batting_first_win_rate: Optional[float]
    chasing_matches: int
    chasing_wins: int
    chasing_win_rate: Optional[float]
    recent_results: list[str]
    recent_wins: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "team": self.team,
            "matches": self.matches,
            "wins": self.wins,
            "losses": self.losses,
            "win_rate": self.win_rate,
            "batting_first_matches": self.batting_first_matches,
            "batting_first_wins": self.batting_first_wins,
            "batting_first_win_rate": self.batting_first_win_rate,
            "chasing_matches": self.chasing_matches,
            "chasing_wins": self.chasing_wins,
            "chasing_win_rate": self.chasing_win_rate,
            "recent_results": self.recent_results,
            "recent_wins_last_5": self.recent_wins,
        }


def load_match_data(csv_path: str | Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with open(csv_path, newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            cleaned = {key.strip(): _clean_value(value) for key, value in row.items()}
            cleaned["match_date"] = _parse_date(cleaned.get("match_date"))
            cleaned["season"] = _parse_int(cleaned.get("season"))
            records.append(cleaned)
    return sorted(records, key=lambda row: row["match_date"] or datetime.min)


def get_unique_values(matches: list[dict[str, Any]], field_name: str) -> list[str]:
    values = {match.get(field_name) for match in matches if match.get(field_name)}
    return sorted(values)


def build_match_context(
    matches: list[dict[str, Any]],
    team_a: str,
    team_b: str,
    city: Optional[str] = None,
    stadium: Optional[str] = None,
    match_type: Optional[str] = None,
    season: Optional[int] = None,
    match_date: Optional[str] = None,
    first_batting_team: Optional[str] = None,
) -> dict[str, Any]:
    filtered_matches = _filter_history(matches, season=season, match_date=match_date)
    latest_match_date = filtered_matches[-1]["match_date"] if filtered_matches else None
    venue_matches = [
        match
        for match in filtered_matches
        if (not city or match.get("host_city") == city)
        and (not stadium or match.get("stadium_name") == stadium)
    ]

    context = {
        "match_input": {
            "team_a": team_a,
            "team_b": team_b,
            "city": city,
            "stadium": stadium,
            "match_type": match_type,
            "season": season,
            "match_date": match_date,
            "first_batting_team": first_batting_team,
        },
        "history_scope": {
            "matches_used": len(filtered_matches),
            "latest_historical_match_date": latest_match_date.date().isoformat()
            if latest_match_date
            else None,
        },
        "team_a_stats": _team_snapshot(filtered_matches, team_a).as_dict(),
        "team_b_stats": _team_snapshot(filtered_matches, team_b).as_dict(),
        "head_to_head": _head_to_head(filtered_matches, team_a, team_b),
        "venue_stats": _venue_stats(venue_matches, team_a, team_b, city, stadium),
        "match_type_stats": _match_type_stats(filtered_matches, team_a, team_b, match_type),
    }
    if first_batting_team:
        context["innings_bias"] = _innings_bias(filtered_matches, first_batting_team, city, stadium)
    return context


def _clean_value(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if text == "" or text.lower() == "nan":
        return None
    return text


def _parse_date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    for fmt in ("%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _parse_int(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def _filter_history(
    matches: list[dict[str, Any]], season: Optional[int] = None, match_date: Optional[str] = None
) -> list[dict[str, Any]]:
    if match_date:
        cutoff = _parse_date(match_date)
        if cutoff:
            return [match for match in matches if match["match_date"] and match["match_date"] < cutoff]
    if season is not None:
        return [match for match in matches if match.get("season") is not None and match["season"] < season]
    return list(matches)


def _team_in_match(match: dict[str, Any], team: str) -> bool:
    return match.get("first_batting_team") == team or match.get("second_batting_team") == team


def _team_snapshot(matches: list[dict[str, Any]], team: str) -> TeamSnapshot:
    team_matches = [match for match in matches if _team_in_match(match, team)]
    wins = sum(1 for match in team_matches if match.get("winning_team") == team)
    matches_count = len(team_matches)
    losses = matches_count - wins

    batting_first_matches = [match for match in team_matches if match.get("first_batting_team") == team]
    chasing_matches = [match for match in team_matches if match.get("second_batting_team") == team]
    batting_first_wins = sum(1 for match in batting_first_matches if match.get("winning_team") == team)
    chasing_wins = sum(1 for match in chasing_matches if match.get("winning_team") == team)

    recent_matches = sorted(team_matches, key=lambda match: match["match_date"] or datetime.min)[-5:]
    recent_results = []
    for match in recent_matches:
        opponent = (
            match.get("second_batting_team")
            if match.get("first_batting_team") == team
            else match.get("first_batting_team")
        )
        result = "W" if match.get("winning_team") == team else "L"
        match_date = match["match_date"].date().isoformat() if match["match_date"] else "unknown"
        recent_results.append(f"{match_date}: {result} vs {opponent}")

    return TeamSnapshot(
        team=team,
        matches=matches_count,
        wins=wins,
        losses=losses,
        win_rate=round((wins / matches_count) * 100, 2) if matches_count else 0.0,
        batting_first_matches=len(batting_first_matches),
        batting_first_wins=batting_first_wins,
        batting_first_win_rate=round((batting_first_wins / len(batting_first_matches)) * 100, 2)
        if batting_first_matches
        else None,
        chasing_matches=len(chasing_matches),
        chasing_wins=chasing_wins,
        chasing_win_rate=round((chasing_wins / len(chasing_matches)) * 100, 2)
        if chasing_matches
        else None,
        recent_results=recent_results,
        recent_wins=sum(1 for match in recent_matches if match.get("winning_team") == team),
    )


def _head_to_head(matches: list[dict[str, Any]], team_a: str, team_b: str) -> dict[str, Any]:
    h2h_matches = [match for match in matches if _team_in_match(match, team_a) and _team_in_match(match, team_b)]
    team_a_wins = sum(1 for match in h2h_matches if match.get("winning_team") == team_a)
    team_b_wins = sum(1 for match in h2h_matches if match.get("winning_team") == team_b)
    latest_five = []
    for match in sorted(h2h_matches, key=lambda row: row["match_date"] or datetime.min)[-5:]:
        latest_five.append(
            {
                "date": match["match_date"].date().isoformat() if match["match_date"] else None,
                "winner": match.get("winning_team"),
                "city": match.get("host_city"),
                "stadium": match.get("stadium_name"),
                "match_type": match.get("match_type"),
            }
        )
    matches_count = len(h2h_matches)
    return {
        "matches": matches_count,
        "team_a_wins": team_a_wins,
        "team_b_wins": team_b_wins,
        "team_a_win_rate": round((team_a_wins / matches_count) * 100, 2) if matches_count else None,
        "team_b_win_rate": round((team_b_wins / matches_count) * 100, 2) if matches_count else None,
        "latest_five_meetings": latest_five,
    }


def _venue_stats(
    venue_matches: list[dict[str, Any]],
    team_a: str,
    team_b: str,
    city: Optional[str],
    stadium: Optional[str],
) -> dict[str, Any]:
    def team_record(team: str) -> dict[str, Any]:
        team_matches = [match for match in venue_matches if _team_in_match(match, team)]
        matches_count = len(team_matches)
        wins = sum(1 for match in team_matches if match.get("winning_team") == team)
        return {
            "matches": matches_count,
            "wins": wins,
            "win_rate": round((wins / matches_count) * 100, 2) if matches_count else None,
        }

    batting_first_wins = sum(
        1
        for match in venue_matches
        if match.get("winning_team") and match.get("winning_team") == match.get("first_batting_team")
    )
    return {
        "city": city,
        "stadium": stadium,
        "matches_in_scope": len(venue_matches),
        "batting_first_win_rate": round((batting_first_wins / len(venue_matches)) * 100, 2)
        if venue_matches
        else None,
        "team_a_record": team_record(team_a),
        "team_b_record": team_record(team_b),
    }


def _match_type_stats(
    matches: list[dict[str, Any]], team_a: str, team_b: str, match_type: Optional[str]
) -> Optional[dict[str, Any]]:
    if not match_type:
        return None
    requested_bucket = _match_type_bucket(match_type)
    filtered_matches = [
        match
        for match in matches
        if _match_type_bucket(match.get("match_type")) == requested_bucket
    ]

    def record(team: str) -> dict[str, Any]:
        team_matches = [match for match in filtered_matches if _team_in_match(match, team)]
        matches_count = len(team_matches)
        wins = sum(1 for match in team_matches if match.get("winning_team") == team)
        return {
            "matches": matches_count,
            "wins": wins,
            "win_rate": round((wins / matches_count) * 100, 2) if matches_count else None,
        }

    return {
        "match_type": match_type,
        "normalized_match_bucket": requested_bucket,
        "matches_in_scope": len(filtered_matches),
        "team_a_record": record(team_a),
        "team_b_record": record(team_b),
    }


def _innings_bias(
    matches: list[dict[str, Any]], first_batting_team: str, city: Optional[str], stadium: Optional[str]
) -> dict[str, Any]:
    batting_first_matches = [
        match for match in matches if match.get("first_batting_team") == first_batting_team
    ]
    venue_matches = [
        match
        for match in batting_first_matches
        if (not city or match.get("host_city") == city)
        and (not stadium or match.get("stadium_name") == stadium)
    ]

    def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
        matches_count = len(rows)
        wins = sum(1 for match in rows if match.get("winning_team") == first_batting_team)
        return {
            "matches": matches_count,
            "wins": wins,
            "win_rate": round((wins / matches_count) * 100, 2) if matches_count else None,
        }

    return {
        "first_batting_team": first_batting_team,
        "overall_record_batting_first": summarize(batting_first_matches),
        "venue_record_batting_first": summarize(venue_matches),
    }


def _match_type_bucket(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    normalized = value.strip().lower()
    playoff_types = {"final", "eliminator", "qualifier 1", "qualifier 2"}
    if normalized in playoff_types:
        return normalized.title()
    return "League"
