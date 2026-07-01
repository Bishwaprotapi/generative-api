"""
NextJob service layer.

Provides:
  - fetch_job_with_applicants  – calls NextJobz REST API
  - remove_id_fields           – strips unwanted keys from the raw payload
  - GeminiCandidateSession     – google.genai Gemini wrapper with key rotation
"""

from __future__ import annotations

import json
import re

import requests
from google import genai
from google.genai.types import HttpOptions

from app.prompts.candidate_ranking_prompt import DELETED_KEYS


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def fetch_job_with_applicants(job_id: int) -> str:
    """
    Fetch job + applicant data from NextJobz and return a JSON string.
    Raises RuntimeError on network / HTTP failure.
    """
    url = f"https://nextjobz.com.bd/api/DataScraper/JobWithApplicants?jobId={job_id}"
    try:
        response = requests.get(url, headers={"accept": "*/*"}, timeout=30)
        response.raise_for_status()
        return json.dumps(response.json(), indent=2)
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(f"Failed to fetch job data: {exc}") from exc


def remove_id_fields(data: dict) -> dict:
    """
    Recursively remove DELETED_KEYS from a nested dict/list structure.
    Exception: 'photoId' is preserved when it appears inside a profile object.
    """
    delete_set = set(DELETED_KEYS)

    def clean(obj: object, inside_profile: bool = False) -> object:
        if isinstance(obj, list):
            return [clean(item, inside_profile) for item in obj]

        if isinstance(obj, dict):
            result: dict = {}
            for key, value in obj.items():
                # Recurse into profile list with the inside_profile flag enabled
                if key == "profiles" and isinstance(value, list):
                    result[key] = [clean(profile, inside_profile=True) for profile in value]
                    continue

                # Drop blacklisted keys — except photoId inside a profile
                if key in delete_set:
                    if inside_profile and key == "photoId":
                        result[key] = value
                    # else: skip
                else:
                    result[key] = clean(value, inside_profile)

            return result

        return obj

    return clean(data)  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Gemini session with key rotation
# ---------------------------------------------------------------------------

class GeminiCandidateSession:
    """
    google.genai-backed Gemini client that rotates through all available API
    keys when a request fails (mirrors the Flask GeminiSession behaviour).
    """

    _KEY_FILE = "credentials/gemini_keys.json"
    _MODEL = "gemini-2.5-flash"

    def __init__(self) -> None:
        self.keys = self._load_keys()
        if not self.keys:
            raise RuntimeError("No Gemini API keys found in credentials/gemini_keys.json")
        self._index = 0

    # -- private helpers -----------------------------------------------------

    def _load_keys(self) -> list[str]:
        try:
            with open(self._KEY_FILE, encoding="utf-8") as fh:
                return list(json.load(fh).values())
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _make_client(self, api_key: str) -> genai.Client:
        return genai.Client(
            api_key=api_key,
            http_options=HttpOptions(api_version="v1"),
        )

    # -- public API ----------------------------------------------------------

    def call_api(self, prompt: str) -> dict:
        """
        Send *prompt* to Gemini, rotating keys on failure.
        Returns parsed JSON dict.
        Raises RuntimeError when all keys are exhausted.
        """
        for _ in range(len(self.keys)):
            api_key = self.keys[self._index]
            try:
                print(f"🔄 Using Gemini key: ...{api_key[-6:]}")
                client = self._make_client(api_key)
                response = client.models.generate_content(
                    model=self._MODEL,
                    contents=prompt,
                )
                return self._parse_json(response.text)
            except Exception as exc:  # noqa: BLE001
                print(f"❌ Key failed ...{api_key[-6:]}: {exc}")
                self._index = (self._index + 1) % len(self.keys)

        raise RuntimeError("All Gemini API keys failed for candidate ranking")

    @staticmethod
    def _parse_json(output: str) -> dict:
        text = output.strip()
        # Strip markdown code fences
        text = re.sub(r"^```json\s*", "", text, flags=re.MULTILINE)
        text = re.sub(r"^```\s*", "", text, flags=re.MULTILINE)
        text = re.sub(r"```$", "", text.rstrip(), flags=re.MULTILINE)

        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            raise ValueError("No JSON object found in Gemini response")

        clean = match.group()
        # Remove trailing commas (common LLM artefact)
        clean = re.sub(r",\s*}", "}", clean)
        clean = re.sub(r",\s*]", "]", clean)

        return json.loads(clean)
