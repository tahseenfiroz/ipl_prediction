import argparse
import json
from pathlib import Path

from app.config import load_gemini_api_key
from app.data_processing.data_processing import build_match_context, load_match_data
from app.predictor.gemini_predictor import GeminiIPLPredictor


DEFAULT_CSV_PATH = Path(__file__).resolve().parent / "data" / "ipl_matches.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Predict IPL match results using historical CSV features + Gemini."
    )
    parser.add_argument(
        "--csv-path",
        default=str(DEFAULT_CSV_PATH),
        help="Path to the IPL CSV file. Defaults to data/ipl_matches.csv inside the project.",
    )
    parser.add_argument("--team-a", required=True, help="First team in the matchup.")
    parser.add_argument("--team-b", required=True, help="Second team in the matchup.")
    parser.add_argument("--city", help="Host city for the match.")
    parser.add_argument("--stadium", help="Stadium name for the match.")
    parser.add_argument("--match-type", default="League", help="Match type or stage.")
    parser.add_argument("--season", type=int, help="Season year of the match to predict.")
    parser.add_argument(
        "--match-date",
        help="Match date in YYYY-MM-DD format. Used to avoid leaking future matches into the summary.",
    )
    parser.add_argument(
        "--first-batting-team",
        help="Team batting first, if known. This can improve the prompt evidence.",
    )
    parser.add_argument(
        "--model-name",
        default="gemini-2.5-flash",
        help="Gemini model name. Default matches your requested model.",
    )
    parser.add_argument(
        "--api-key",
        help="Gemini API key. If omitted, the app checks .env and then the current environment.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the prepared evidence bundle without calling Gemini.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    csv_path = Path(args.csv_path).expanduser().resolve()
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    matches_df = load_match_data(csv_path)
    match_context = build_match_context(
        matches_df,
        team_a=args.team_a,
        team_b=args.team_b,
        city=args.city,
        stadium=args.stadium,
        match_type=args.match_type,
        season=args.season,
        match_date=args.match_date,
        first_batting_team=args.first_batting_team,
    )

    if args.dry_run:
        print(json.dumps(match_context, indent=2, default=str))
        return

    api_key = load_gemini_api_key(args.api_key)
    predictor = GeminiIPLPredictor(api_key=api_key, model_name=args.model_name)
    prediction = predictor.predict(match_context)
    print(json.dumps(prediction, indent=2))


if __name__ == "__main__":
    main()
