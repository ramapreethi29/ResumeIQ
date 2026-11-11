
import json
import requests


OLLAMA_URL = "http://localhost:11434/api/generate"
LLM_MODEL = "qwen2.5:7b"


def generate_suggestions(
    matching_requirements,
    missing_requirements,
    experience_context=None
):

    # Only use skills, certifications and experience
    
    relevant_data = {
        "matched_skills": matching_requirements.get("skills", []),
        "missing_skills": missing_requirements.get("skills", []),

        "matched_certifications": matching_requirements.get(
            "certifications", []
        ),
        "missing_certifications": missing_requirements.get(
            "certifications", []
        ),

        "matched_experience": matching_requirements.get(
            "experience", []
        ),
        "missing_experience": missing_requirements.get(
            "experience", []
        ),

        "experience_context": experience_context or {}
    }

    

    prompt = f"""
You are a resume improvement advisor.

Analyze the following resume-job matching results:

{json.dumps(relevant_data, indent=2)}

Generate 3 to 4 concise, useful and generic improvement suggestions.

STRICT RULES:

1. Consider the overall matched and missing requirements.
2. Identify the most important improvement areas.
3. Do not generate one suggestion for every missing requirement.
4. Do not invent candidate skills, certifications or experience.
5. Never suggest adding skills, experience or certifications to the resume.
6. You may recommend learning relevant missing skills.
7. You may recommend pursuing a missing certification.
8. You may recommend gaining more relevant professional experience.
9. If experience is below the preferred requirement, state the gap accurately.
10. Do not recommend certifications that are already matched.
11. Do not use education or unknown requirements.
12. Avoid repetitive, exaggerated or overly specific advice.
13. Suggestions must be based only on the supplied data.
14. If a preferred experience requirement is missing,
    explain the gap without assuming the candidate's
    exact current experience from a requirement label.

15. If missing certifications are provided, consider
    including one relevant certification suggestion.

16. Prioritize the most significant improvement areas
    across skills, certifications and experience.

17. Do not force all categories into separate suggestions
    if they are not relevant.

For experience suggestions:
- Clearly distinguish required experience from preferred experience.
- Never describe a required experience requirement as preferred.
- Use experience_context when available.
- Compare date-based professional experience against the required minimum.
- Do not count internships as professional experience.
- If professional experience is unavailable, do not assume it is zero.
- Explain when the resume does not provide enough evidence to verify the required experience.
- Calculate remaining months only when the candidate's professional experience duration is known.

{{
    "suggestions": [
        "Suggestion 1",
        "Suggestion 2",
        "Suggestion 3"
    ]
}}

Return only 3 to 4 suggestions.
"""

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": LLM_MODEL,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.2,
                "num_predict": 450
            },
            "keep_alive": "30m"
        },
        timeout=180
    )

    response.raise_for_status()

    result = response.json()

    try:
        parsed = json.loads(result["response"])
        suggestions = parsed.get("suggestions", [])

        if not isinstance(suggestions, list):
            return []

        return [
            item.strip()
            for item in suggestions
            if isinstance(item, str) and item.strip()
        ][:4]

    except (json.JSONDecodeError, TypeError, KeyError):
        return []
