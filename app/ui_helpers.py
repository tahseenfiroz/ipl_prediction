from __future__ import annotations

from pathlib import Path

import streamlit as st

from app.config import load_rapidapi_config
from app.data_processing.data_processing import load_match_data
from app.services.live_scores import fetch_live_matches_with_scores
from app.services.upcoming_match import fetch_upcoming_ipl_match


DEFAULT_CSV_PATH = Path(__file__).resolve().parents[1] / "data" / "ipl_matches.csv"


@st.cache_data(show_spinner=False)
def load_matches(csv_path: str) -> list[dict]:
    return load_match_data(csv_path)


@st.cache_data(ttl=1800, show_spinner=False)
def load_upcoming_match() -> dict | None:
    try:
        return fetch_upcoming_ipl_match()
    except Exception:
        return None


@st.cache_data(ttl=120, show_spinner=False)
def load_live_matches() -> list[dict]:
    api_key, api_host = load_rapidapi_config()
    if not api_key or not api_host:
        return []
    try:
        return fetch_live_matches_with_scores(api_key, api_host)
    except Exception:
        return []
