"""
NextJob endpoints — POST /nextjob-candidate-find

Converts a natural-language recruitment query into a ranked candidate list
using Gemini AI and the NextJobz dataset.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.prompts.candidate_ranking_prompt import Candidate_ranking_PROMPT
from app.services.nextjob_service import (
    GeminiCandidateSession,
    fetch_job_with_applicants,
    remove_id_fields,
)

router = APIRouter(tags=["NextJob"])


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class CandidateFindRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        example="Give me 5 candidates who has minimum 5 years of experience",
    )
    intJobMasterId: int = Field(..., example=390)
    pipelineRowId: int = Field(default=0, example=0)


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post(
    "/nextjob-candidate-find",
    summary="Rank candidates using Gemini AI",
    status_code=status.HTTP_200_OK,
)
async def candidate_find(body: CandidateFindRequest):
    """
    Convert a natural-language recruitment question into a ranked candidate
    list by:

    1. Fetching job + applicant data from NextJobz.
    2. Stripping noisy / internal ID fields.
    3. Sending a structured prompt to Gemini with key rotation.
    4. Returning the parsed JSON ranking result.
    """
    try:
        # 1. Fetch raw dataset
        raw_json = fetch_job_with_applicants(body.intJobMasterId)

        # 2. Clean dataset
        dataset = remove_id_fields(json.loads(raw_json))
        print(dataset)

        # 3. Build prompt (prompt is kept verbatim from original Flask code)
        formatted_prompt = Candidate_ranking_PROMPT.format(
            user_query=(
                body.question
                + "based on the job description and applicant data, "
                  "and respond in the required output format. "
                  "Make sure to return only the number of candidates requested."
            ),
            data=dataset,
        )

        # 4. Call Gemini
        session = GeminiCandidateSession()
        result = session.call_api(formatted_prompt)

        return result

    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {exc}",
        ) from exc
