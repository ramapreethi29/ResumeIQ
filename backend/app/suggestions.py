from pydantic import BaseModel, Field
from langchain_ollama import ChatOllama


class SuggestionResult(BaseModel):
    presentation_score: int = Field(ge=0, le=100)
    summary: str
    suggestions: list[str] = Field(default_factory=list)
    improved_bullets: list[str] = Field(default_factory=list)
    recommendation: str


def build_suggestions(comparison: dict, comparison_score: float) -> dict:
    """Ask Qwen for wording suggestions. It must not invent missing experience."""
    llm = ChatOllama(
        model="qwen2.5:7b",
        temperature=0,
        num_predict=1200,
    )
    structured_llm = llm.with_structured_output(
        SuggestionResult,
        method="json_schema",
    )
    prompt = f"""
You review a resume comparison that was already calculated.

Comparison score: {comparison_score} out of 100.

Comparison JSON:
{comparison}

Rules:
- Do not claim a missing skill, certification, degree, or job exists.
- Suggestions may only tell the candidate how to surface evidence already marked match or partial.
- For unmatched items, say to add them only if the candidate truly has that evidence.
- presentation_score rates how clearly the matched evidence is written, from 0 to 100.
- Keep presentation_score within 15 points of the comparison score.
- improved_bullets must reuse facts from matched evidence only.
- Return at most 6 suggestions and 4 bullets.
"""
    result = structured_llm.invoke(prompt)
    data = result.model_dump() if hasattr(result, "model_dump") else result.dict()
    data["source"] = "qwen2.5"
    return data
