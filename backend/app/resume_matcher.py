
import re
import unicodedata
import math

from langchain_ollama import OllamaEmbeddings


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

EMBEDDING_MODEL = "nomic-embed-text"

SIMILARITY_THRESHOLD = 0.35
STRONG_SIMILARITY_THRESHOLD = 0.60

TOP_K = 3
BATCH_SIZE = 64


IMPLEMENTATION_WORDS = {
    "built",
    "developed",
    "implemented",
    "created",
    "designed",
    "integrated",
    "deployed",
    "configured",
    "maintained",
    "automated",
    "programmed",
    "utilized",
    "tested",
    "engineered",
    "managed"
}


embeddings = OllamaEmbeddings(
    model=EMBEDDING_MODEL
)


# --------------------------------------------------
# 1. TEXT NORMALIZATION
# --------------------------------------------------

def normalize_text(text: str) -> str:

    text = unicodedata.normalize("NFKC", text)
    text = text.lower().strip()

    text = re.sub(r"[^a-z0-9+#.]+", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()



GENERIC_SKILL_WORDS = {
    "programming",
    "development",
    "developing",
    "developer",
    "experience",
    "knowledge",
    "proficiency",
    "familiarity",
    "working",
    "with",
    "using",
    "of",
    "in"
}


def normalize_skill_tokens(text: str) -> set:

    normalized = normalize_text(text)
    tokens = normalized.split()

    result = set()

    for token in tokens:

        if token in GENERIC_SKILL_WORDS:
            continue

        # Handle common plural forms
        if token.endswith("ies") and len(token) > 4:
            token = token[:-3] + "y"

        elif token.endswith("s") and not token.endswith("ss") and len(token) > 3:
            token = token[:-1]

        result.add(token)

    return result


GENERIC_SKILL_WORDS = {
    "programming",
    "development",
    "developing",
    "developer",
    "experience",
    "knowledge",
    "proficiency",
    "familiarity",
    "working",
    "with",
    "using",
    "of",
    "in"
}


def normalize_skill_tokens(text: str) -> set:
    normalized = normalize_text(text)

    # Remove punctuation while preserving letters and numbers
    tokens = re.findall(r"[a-z0-9]+", normalized)

    result = set()

    for token in tokens:
        if token in GENERIC_SKILL_WORDS:
            continue

        if token.endswith("ies") and len(token) > 4:
            token = token[:-3] + "y"

        elif token.endswith("s") and not token.endswith("ss") and len(token) > 3:
            token = token[:-1]

        result.add(token)

    return result

def contains_skill(skill: str, evidence_text: str) -> bool:
    skill_tokens = normalize_skill_tokens(skill)
    evidence_tokens = normalize_skill_tokens(evidence_text)

    if not skill_tokens:
        return False

    return skill_tokens.issubset(evidence_tokens)


# --------------------------------------------------
# 2. EVIDENCE MAP AND IDS
# --------------------------------------------------

def build_evidence_map(resume_evidence: list) -> dict:

    evidence_map = {}

    for index, item in enumerate(resume_evidence, start=1):

        evidence_id = f"E{index}"

        evidence_map[evidence_id] = {
            "evidence_id": evidence_id,
            "source_evidence_id": item.get("evidence_id"),
            "section": item.get("section", "other"),
            "text": item.get("text", "")
        }

    return evidence_map


# --------------------------------------------------
# 3. OLLAMA EMBEDDINGS
# --------------------------------------------------

def generate_embeddings(
    texts: list,
    is_query: bool = False
) -> list:

    if not texts:
        return []

    results = []

    for start in range(0, len(texts), BATCH_SIZE):

        batch = texts[start:start + BATCH_SIZE]

        try:

            if is_query:

                batch_embeddings = [
                    embeddings.embed_query(text)
                    for text in batch
                ]

            else:

                batch_embeddings = embeddings.embed_documents(
                    batch
                )

            results.extend(batch_embeddings)

        except Exception as error:

            raise RuntimeError(
                "Ollama embedding generation failed. "
                "Check that Ollama is running and "
                "nomic-embed-text is installed. "
                f"Details: {error}"
            )

    return results


# --------------------------------------------------
# 4. COSINE SIMILARITY
# --------------------------------------------------

def cosine_similarity(
    vector_a: list,
    vector_b: list
) -> float:

    if len(vector_a) != len(vector_b):
        raise ValueError(
            "Embedding dimensions do not match."
        )

    dot_product = sum(
        a * b
        for a, b in zip(vector_a, vector_b)
    )

    magnitude_a = math.sqrt(
        sum(a * a for a in vector_a)
    )

    magnitude_b = math.sqrt(
        sum(b * b for b in vector_b)
    )

    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0

    return dot_product / (
        magnitude_a * magnitude_b
    )


# --------------------------------------------------
# 5. IMPLEMENTATION CHECK
# --------------------------------------------------

def has_implementation_details(text: str) -> bool:

    words = set(
        normalize_text(text).split()
    )

    return bool(
        words.intersection(IMPLEMENTATION_WORDS)
    )


# --------------------------------------------------
# 6. EXACT SKILL MATCHING
# --------------------------------------------------

def find_exact_matches(
    skill: str,
    evidence_map: dict
) -> list:

    matches = []

    for evidence in evidence_map.values():

        if contains_skill(skill, evidence["text"]):
            matches.append(evidence)

    return matches


# --------------------------------------------------
# 7. PYTHON CLASSIFICATION
# --------------------------------------------------

def classify_exact_match(skill: str, matches: list) -> dict:

    if not matches:
        return {
            "skill": skill,
            "status": "Missing",
            "evidence": []
        }

    # Demonstrated: listed in technical skills
    technical_matches = [
        item for item in matches
        if item["section"] == "technical_skills"
    ]

    # Demonstrated: actually used in projects or work
    implementation_matches = [
        item for item in matches
        if item["section"] in {"projects", "work_experience"}
        and has_implementation_details(item["text"])
    ]

    if technical_matches or implementation_matches:
        return {
            "skill": skill,
            "status": "Demonstrated",
            "evidence": (technical_matches + implementation_matches)[:TOP_K]
        }

    # Potential: found in project content without implementation evidence
    project_matches = [
        item for item in matches
        if item["section"] == "projects"
    ]

    if project_matches:
        return {
            "skill": skill,
            "status": "Potential",
            "evidence": project_matches[:TOP_K]
        }

    # Mentioned: found, but no proof of usage
    return {
        "skill": skill,
        "status": "Mentioned",
        "evidence": matches[:TOP_K]
    }
# --------------------------------------------------
# 8. SEMANTIC EVIDENCE RETRIEVAL
# --------------------------------------------------

def find_semantic_matches(
    skill: str,
    skill_embedding: list,
    evidence_items: list,
    evidence_embeddings: list
) -> list:

    results = []

    for evidence, evidence_embedding in zip(
        evidence_items,
        evidence_embeddings
    ):

        score = cosine_similarity(
            skill_embedding,
            evidence_embedding
        )

        if score >= SIMILARITY_THRESHOLD:

            results.append({
                **evidence,
                "similarity": round(score, 4)
            })

    results.sort(
        key=lambda item: item["similarity"],
        reverse=True
    )

    return results[:TOP_K]


# --------------------------------------------------
# 9. MATCH SKILL GROUP
# --------------------------------------------------

def match_skill_group(skills: list, evidence_map: dict) -> list:

    results = []

    for skill in skills:

        exact_matches = find_exact_matches(
            skill,
            evidence_map
        )

        result = classify_exact_match(
            skill,
            exact_matches
        )

        results.append(result)

    return results

# --------------------------------------------------
# 10. CLEAN FINAL OUTPUT
# --------------------------------------------------

def format_skill_results(results: list) -> list:

    formatted_results = []

    for item in results:

        result = {
            "skill": item["skill"],
            "status": item["status"]
        }

        # Missing skills need only their status
        if item["status"] != "Missing":

            result["evidence"] = [
                {
                    "evidence_id": evidence["evidence_id"],
                    "text": evidence["text"]
                }
                for evidence in item.get("evidence", [])
            ]

        formatted_results.append(result)

    return formatted_results


# --------------------------------------------------
# 11. MAIN MATCHING FUNCTION
# --------------------------------------------------

def match_jd_skills(
    jd_requirements: dict,
    resume_evidence: list
) -> dict:

    # Build evidence map
    evidence_map = build_evidence_map(
        resume_evidence
    )

    # Extract required and preferred skills
    required_skills = jd_requirements.get(
        "required", {}
    ).get("skills", [])

    preferred_skills = jd_requirements.get(
        "preferred", {}
    ).get("skills", [])

    # Match required skills
    required_results = match_skill_group(
        required_skills,
        evidence_map
    )

    # Match preferred skills
    preferred_results = match_skill_group(
        preferred_skills,
        evidence_map
    )

    # Return clean output
    return {
        "required_skills": format_skill_results(
            required_results
        ),
        "preferred_skills": format_skill_results(
            preferred_results
        )
    }
