from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from app.config import load_gemini_api_key
from app.data_processing.data_processing import (
    build_match_context,
    get_unique_values,
    load_match_data,
)
from app.predictor.gemini_predictor import GeminiIPLPredictor


DEFAULT_CSV_PATH = Path(__file__).resolve().parent / "data" / "ipl_matches.csv"


@st.cache_data(show_spinner=False)
def load_matches(csv_path: str) -> list[dict]:
    return load_match_data(csv_path)


def _stadiums_for_city(matches: list[dict], city: str | None) -> list[str]:
    if not city:
        return get_unique_values(matches, "stadium_name")
    stadiums = {
        match.get("stadium_name")
        for match in matches
        if match.get("host_city") == city and match.get("stadium_name")
    }
    return sorted(stadiums)


def main() -> None:
    st.set_page_config(page_title="IPL Predictor", page_icon="🏏", layout="wide")
    st.title("IPL Match Predictor")

    csv_path = DEFAULT_CSV_PATH
    if not csv_path.exists():
        st.error(f"CSV file not found: {csv_path}")
        st.stop()

    matches = load_matches(str(csv_path))
    teams = sorted(
        set(get_unique_values(matches, "first_batting_team"))
        | set(get_unique_values(matches, "second_batting_team"))
    )
    cities = get_unique_values(matches, "host_city")

    col1, col2 = st.columns(2)
    with col1:
        team_a = st.selectbox("Team A", teams, index=teams.index("Mumbai Indians") if "Mumbai Indians" in teams else 0)
        city = st.selectbox("City", [""] + cities)
        match_type = st.selectbox(
            "Match type",
            ["League", "Qualifier 1", "Eliminator", "Qualifier 2", "Final"],
        )
    with col2:
        team_b_options = [team for team in teams if team != team_a]
        team_b = st.selectbox(
            "Team B",
            team_b_options,
            index=team_b_options.index("Chennai Super Kings")
            if "Chennai Super Kings" in team_b_options
            else 0,
        )
        stadium_options = _stadiums_for_city(matches, city or None)
        stadium = st.selectbox("Stadium", [""] + stadium_options)
        season = st.number_input("Season", min_value=2008, max_value=2100, value=2026, step=1)

    first_batting_team = st.selectbox(
        "Batting first",
        ["Unknown", team_a, team_b],
    )

    if not st.button("Predict", type="primary", use_container_width=True):
        return

    api_key = load_gemini_api_key()
    if not api_key:
        st.error("Gemini API key not found. Set GEMINI_API_KEY or update .env.")
        st.stop()

    match_context = build_match_context(
        matches,
        team_a=team_a,
        team_b=team_b,
        city=city or None,
        stadium=stadium or None,
        match_type=match_type,
        season=int(season),
        first_batting_team=None if first_batting_team == "Unknown" else first_batting_team,
    )

    with st.spinner("Generating prediction..."):
        predictor = GeminiIPLPredictor(api_key=api_key, model_name="gemini-2.5-flash")
        prediction = predictor.predict(match_context)

    probabilities = prediction.get("winner_probability_percent", {})
    metric1, metric2, metric3 = st.columns(3)
    metric1.metric("Predicted winner", prediction.get("predicted_winner", "Unknown"))
    metric2.metric("Confidence", f"{prediction.get('confidence', 0)}%")
    metric3.metric(
        "Win split",
        f"{probabilities.get('team_a', 0)}% / {probabilities.get('team_b', 0)}%",
    )

    st.subheader("Summary")
    st.write(prediction.get("summary", ""))

    st.subheader("Key factors")
    for factor in prediction.get("key_factors", []):
        st.write(f"- {factor}")

    risk_flags = prediction.get("risk_flags", [])
    if risk_flags:
        st.subheader("Risk flags")
        for item in risk_flags:
            st.write(f"- {item}")

    with st.expander("Prediction JSON"):
        st.code(json.dumps(prediction, indent=2), language="json")

    with st.expander("Evidence sent to Gemini"):
        st.code(json.dumps(match_context, indent=2), language="json")


if __name__ == "__main__":
    main()
