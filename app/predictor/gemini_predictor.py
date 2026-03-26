from __future__ import annotations

import json
from typing import Any


class GeminiIPLPredictor:
    def __init__(self, api_key: str | None, model_name: str = "gemini-2.5-flash") -> None:
        if not api_key:
            raise ValueError(
                "Gemini API key missing. Pass --api-key, set GEMINI_API_KEY, or add it to .env."
            )

        try:
            import google.generativeai as genai
        except ImportError as exc:
            raise ImportError(
                "google-generativeai is not installed. Run: pip install google-generativeai"
            ) from exc

        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(model_name)

    def predict(self, match_context: dict[str, Any]) -> dict[str, Any]:
        prompt = self._build_prompt(match_context)
        response = self._model.generate_content(
            prompt,
            generation_config={"temperature": 0},
        )
        return self._parse_json_response(response.text)

    @staticmethod
    def _build_prompt(match_context: dict[str, Any]) -> str:
        return f"""
You are an IPL match prediction analyst.
Use ONLY the structured evidence below. Do not invent statistics.
Balance team strength, recent form, head-to-head, venue history, and batting-first bias if available.

Return valid JSON with this exact schema:
{{
  "predicted_winner": "team name",
  "confidence": 0,
  "winner_probability_percent": {{
    "team_a": 0,
    "team_b": 0
  }},
  "key_factors": ["factor 1", "factor 2", "factor 3"],
  "risk_flags": ["risk 1", "risk 2"],
  "summary": "2-4 sentence explanation"
}}

Rules:
- confidence must be an integer from 0 to 100.
- winner_probability_percent values must add up to 100.
- predicted_winner must be either team_a or team_b from match_input.
- If evidence is thin, lower confidence and say so.

Evidence:
{json.dumps(match_context, indent=2, default=str)}
""".strip()

    @staticmethod
    def _parse_json_response(text: str) -> dict[str, Any]:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
            cleaned = cleaned.rsplit("```", 1)[0].strip()
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1:
            raise ValueError(f"Gemini response did not contain JSON: {text}")
        return json.loads(cleaned[start : end + 1])
