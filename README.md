# IPL Prediction with Gemini

This project builds an IPL match predictor from your historical match-results CSV and uses `gemini-2.5-flash` to make the final prediction.

It does not "train" Gemini on the CSV in the classical ML sense. Instead, it:

1. Loads and cleans the IPL historical data
2. Computes matchup features like recent form, head-to-head, and venue record
3. Sends those features to Gemini
4. Gets back a structured prediction JSON

## Setup

```bash
cd /Users/tahseenfiroz/Documents/tfiroz/Project/ipl/pythonProject3
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

The project now expects the IPL CSV in [data/ipl_matches.csv](/Users/tahseenfiroz/Documents/tfiroz/Project/ipl/pythonProject3/data/ipl_matches.csv).

Set your Gemini key in [.env](/Users/tahseenfiroz/Documents/tfiroz/Project/ipl/pythonProject3/.env):

```bash
GEMINI_API_KEY="YOUR_KEY_HERE"
```

The loader reads `.env` first and then falls back to the current shell environment.

## Run a prediction

```bash
python3 main.py \
  --team-a "Mumbai Indians" \
  --team-b "Chennai Super Kings" \
  --city "Mumbai" \
  --stadium "Wankhede Stadium, Mumbai" \
  --match-type "League" \
  --season 2026
```

## Run the Streamlit UI

```bash
cd /Users/tahseenfiroz/Documents/tfiroz/Project/ipl/pythonProject3
source .venv/bin/activate
python -m streamlit run streamlit_app.py
```

The Streamlit app uses the repo-local CSV at [data/ipl_matches.csv](/Users/tahseenfiroz/Documents/tfiroz/Project/ipl/pythonProject3/data/ipl_matches.csv).
It now has a top navigation header with:

1. `Prediction` as the landing view
2. `Live Match` for live scores and the next IPL fixture

If you already know who is batting first, include it:

```bash
python3 main.py \
  --team-a "Mumbai Indians" \
  --team-b "Chennai Super Kings" \
  --city "Mumbai" \
  --stadium "Wankhede Stadium, Mumbai" \
  --match-type "League" \
  --season 2026 \
  --first-batting-team "Mumbai Indians"
```

## Inspect the evidence without calling Gemini

```bash
python3 main.py \
  --team-a "Mumbai Indians" \
  --team-b "Chennai Super Kings" \
  --city "Mumbai" \
  --stadium "Wankhede Stadium, Mumbai" \
  --season 2026 \
  --dry-run
```

If you store the CSV somewhere else, you can still override it:

```bash
python3 main.py \
  --csv-path "/absolute/path/to/other_ipl_file.csv" \
  --team-a "Mumbai Indians" \
  --team-b "Chennai Super Kings" \
  --season 2026
```

## Output

The CLI returns JSON like:

```json
{
  "predicted_winner": "Mumbai Indians",
  "confidence": 68,
  "winner_probability_percent": {
    "team_a": 56,
    "team_b": 44
  },
  "key_factors": [
    "Stronger recent form",
    "Better venue record",
    "Favorable head-to-head"
  ],
  "risk_flags": [
    "Limited venue-specific sample size"
  ],
  "summary": "Mumbai Indians have the stronger venue history and slightly better recent form, so they enter as favorites."
}
```
