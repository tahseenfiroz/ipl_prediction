from __future__ import annotations

import json
from typing import Optional

import streamlit as st

from app.config import load_gemini_api_key
from app.data_processing.data_processing import build_match_context, get_unique_values
from app.predictor.gemini_predictor import GeminiIPLPredictor
from app.ui_helpers import DEFAULT_CSV_PATH, load_live_matches, load_matches, load_upcoming_match


def render_header(selected_page: str) -> None:
    prediction_class = "nav-link active" if selected_page == "prediction" else "nav-link"
    live_class = "nav-link active" if selected_page == "live-match" else "nav-link"

    st.markdown(
        """
        <style>
        .app-shell {
            background: linear-gradient(135deg, #fff7ed 0%, #ecfeff 45%, #eff6ff 100%);
            border: 1px solid rgba(251, 146, 60, 0.18);
            border-radius: 24px;
            padding: 1.5rem 1.5rem 1rem 1.5rem;
            margin-bottom: 1.25rem;
            box-shadow: 0 18px 40px rgba(15, 23, 42, 0.08);
        }
        .app-title {
            text-align: center;
            font-size: 2.35rem;
            font-weight: 800;
            letter-spacing: -0.03em;
            margin: 0;
            background: linear-gradient(90deg, #b45309 0%, #0f766e 45%, #2563eb 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .app-subtitle {
            text-align: center;
            color: #475569;
            font-size: 0.98rem;
            margin: 0.35rem 0 1.15rem 0;
        }
        .top-nav {
            display: flex;
            justify-content: center;
            gap: 0.85rem;
            flex-wrap: wrap;
        }
        .nav-link {
            display: inline-block;
            padding: 0.7rem 1.15rem;
            border-radius: 999px;
            text-decoration: none;
            color: #0f172a;
            background: rgba(255, 255, 255, 0.88);
            border: 1px solid rgba(148, 163, 184, 0.24);
            font-weight: 700;
            transition: all 0.2s ease;
            box-shadow: 0 6px 16px rgba(15, 23, 42, 0.06);
        }
        .nav-link.active {
            color: #ffffff;
            background: linear-gradient(90deg, #ea580c 0%, #0891b2 55%, #2563eb 100%);
            border-color: transparent;
            box-shadow: 0 10px 24px rgba(37, 99, 235, 0.22);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="app-shell">
          <h1 class="app-title">IPL Match Predictor</h1>
          <div class="app-subtitle">Prediction and live score tracking in one place</div>
          <div class="top-nav">
            <a class="{prediction_class}" href="?page=prediction" target="_self">Prediction</a>
            <a class="{live_class}" href="?page=live-match" target="_self">Live Score</a>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _stadiums_for_city(matches: list[dict], city: Optional[str]) -> list[str]:
    if not city:
        return get_unique_values(matches, "stadium_name")
    stadiums = {
        match.get("stadium_name")
        for match in matches
        if match.get("host_city") == city and match.get("stadium_name")
    }
    return sorted(stadiums)


def render_live_match_page() -> None:
    st.caption("Live data is loaded on demand to keep the app responsive.")
    should_load_live_data = st.button("Load Live Match Data", type="primary", use_container_width=True)
    if not should_load_live_data:
        st.info("Click `Load Live Match Data` to fetch the upcoming fixture and current live scores.")
        return

    st.subheader("Upcoming Match")
    upcoming_match = load_upcoming_match()
    if upcoming_match:
        st.info(
            "Upcoming IPL match: "
            f"{upcoming_match['team_a']} vs {upcoming_match['team_b']} "
            f"at {upcoming_match['start_time_local']} "
            f"([source]({upcoming_match['source_url']}))"
        )
    else:
        st.info("Upcoming IPL match data is not available right now.")

    st.subheader("Live Scores")
    live_matches = load_live_matches()
    if live_matches:
        for live_match in live_matches[:3]:
            title = f"{live_match['team_a']} vs {live_match['team_b']}"
            subtitle_parts = [live_match["series_name"], live_match["match_desc"], live_match["venue"]]
            subtitle = " | ".join(part for part in subtitle_parts if part)
            st.markdown(f"**{title}**")
            if subtitle:
                st.caption(subtitle)
            st.write(live_match["status"])
            st.write(live_match["score"])
    else:
        st.info("No live matches found right now, or the live-score API did not return usable data.")


def render_prediction_page() -> None:
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

    first_batting_team = st.selectbox("Batting first", ["Unknown", team_a, team_b])

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
    metric3.metric("Win split", f"{probabilities.get('team_a', 0)}% / {probabilities.get('team_b', 0)}%")

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


def main() -> None:
    st.set_page_config(page_title="IPL Predictor", page_icon="🏏", layout="wide")
    selected_page = st.query_params.get("page", "prediction")
    if selected_page not in {"prediction", "live-match"}:
        selected_page = "prediction"

    render_header(selected_page)

    if selected_page == "prediction":
        render_prediction_page()
    else:
        render_live_match_page()


if __name__ == "__main__":
    main()
