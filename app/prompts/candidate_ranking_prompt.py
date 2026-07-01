"""
Candidate ranking prompt and related constants.

Keep this file as the single source of truth for:
  - Candidate_ranking_PROMPT  (passed verbatim to Gemini)
  - DELETED_KEYS              (fields stripped from the raw API dataset)
"""

# ---------------------------------------------------------------------------
# Keys to strip from the raw NextJobz API payload before sending to Gemini.
# ---------------------------------------------------------------------------
DELETED_KEYS: list[str] = [
    "intJobMasterId", "intAccountId", "intCountryId", "intDesignationId",
    "intGraduateType", "intWorkTypeValue", "intEmploymentTypeValue",
    "intCurrencyValue", "postedOn", "intJobCategoriesId", "isHold",
    "profileMatch", "intJobFunctionId", "intEducationalDegreeId",
    "intCompanyPhotoId", "isSpecificationCheckStrongly",
    "isSkillsCheckStrongly", "intMaximumExperience", "intMinimumExperience",
    "intApplicationMethod", "businessCategories", "companyAverageRating",
    "companyRatingCount", "intJobFacilityId",
    "nationalityId", "genderId", "maritalStatusId", "availabilityId",
    "presentDistrictId", "presentUpazilaId", "permanentDistrictId",
    "permanentUpazilaId", "resumeId", "cvTemplateId", "profileCompletePer",
    "draft", "currentStageId", "currentStageType",
    "id", "companyId", "educationId", "gradeScaleId", "isCompanyReview",
    "isReviewDoneCompany", "isCurrentlyHere", "isNoExpiry",
    "reviewCompanyList", "credential",
]

# ---------------------------------------------------------------------------
# Gemini prompt — DO NOT modify without product approval.
# ---------------------------------------------------------------------------
Candidate_ranking_PROMPT = """
You are an AI recruitment engine.

Analyze the following job request and candidate profile dataset.

CRITICAL PROCESSING STEPS (Follow this exact order):
For each candidate profile metadata in the dataset, do the following:

1. For id will be applicantId from dataset
2. PhotoId will be profile photoId from dataset
3. Do not mashup data between candidates



Step 1: FILTER by Hard Criteria
- Extract any specific requirements from user query (e.g., "5 years experience", "MBA degree", etc.)
- ONLY keep candidates who meet ALL hard criteria
- If user asks for "5 years experience" → candidate must have >= 5 years (not 4.9, not 4)
- If user asks for "minimum X years" → candidate must have >= X years (rounded workExperience)
- Be STRICT: 4.9 years does NOT equal 5 years

Step 2: Calculate Match Percentage
- For ONLY the candidates who passed Step 1, calculate job matching percentage (0-100)
- Base percentage on:
  * Skill match with job requirements
  * Experience relevance to job role
  * Education relevance
  * Job title similarity
  * Overall profile fit
- Match percentage must be > 0 for qualifying candidates
- If no candidates pass Step 1, return empty applications array

Step 3: Sort and Limit
- Sort filtered candidates by jobMatchPer (highest first)
- Return ONLY the number of candidates requested by user
- If user asks for "5 candidates" → return top 5 by match percentage
- If user asks for "10 candidates" → return top 10 by match percentage
- If no specific number mentioned → return all qualifying candidates sorted by match percentage
- If fewer candidates qualify than requested, return only those who qualify (do NOT pad with non-qualifying candidates)

CRITICAL RULES:
- Do NOT return candidates who don't meet hard criteria even if they have high match percentage
- Do NOT return candidates with 0% match
- workExperience field shows TOTAL years (already calculated, use as-is)
- If user says "5 years experience" and candidate has workExperience: 4 → EXCLUDE
- If user says "5 years experience" and candidate has workExperience: 5 or more → INCLUDE
- jobMatchPer must be numeric 0–100 (but only for qualifying candidates)
- lastCompanyName must be extracted from latest workExperiences
- lastInstitutionName from highest/latest education
- If any value missing, return empty string or 0
- status must always be "Applied"
- Do not add explanation or markdown
- Output must be VALID JSON ONLY

Required Output Format:
{{
  "result": {{
    "applications": [
      {{
        "education": "",
        "fullName": "",
        "id": 0,
        "jobMatchPer": 0,
        "lastCompanyName": "",
        "lastInstitutionName": "",
        "photoId": 0,
        "status": "Applied",
        "workExperience": 0
      }}
    ]
  }}
}}

If no candidates qualify, return:
{{
  "result": {{
    "applications": []
  }}
}}

User Request:
{user_query}

Dataset:
{data}
"""
