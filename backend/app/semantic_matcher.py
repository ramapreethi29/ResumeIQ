
import json
import hashlib
import requests

from pathlib import Path
from fastembed import TextEmbedding

from app.skill_normalizer import normalize_jd_skill


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

MODEL_NAME = "BAAI/bge-small-en-v1.5"

OLLAMA_URL = "http://localhost:11434/api/generate"
LLM_MODEL = "qwen2.5:7b"

SIMILARITY_THRESHOLD = 0.40
TOP_K = 3

CACHE_DIR = (
    Path(__file__).resolve().parent.parent
    / "cache"
)

VERIFICATION_CACHE_FILE = (
    CACHE_DIR / "semantic_verifications.json"
)
EMBEDDING_CACHE_FILE = (
    CACHE_DIR / "semantic_embeddings.json"
)

CACHE_VERSION = "v1"

_embedding_model = None

# In-memory embedding cache
_embedding_cache = {}
_embedding_cache_loaded = False

# In-memory verification cache
_verification_cache = None

# Reuse HTTP connections to Ollama
_http_session = requests.Session()


# --------------------------------------------------
# LOAD EMBEDDING MODEL
# --------------------------------------------------

def get_embedding_model():

    global _embedding_model

    if _embedding_model is None:

        _embedding_model = TextEmbedding(
            model_name=MODEL_NAME
        )

    return _embedding_model

def load_embedding_cache():

    global _embedding_cache_loaded

    if _embedding_cache_loaded:
        return

    try:
        with open(
            EMBEDDING_CACHE_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            _embedding_cache.update(json.load(file))

    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass

    _embedding_cache_loaded = True
# --------------------------------------------------
# EMBEDDING CACHE
# --------------------------------------------------
def get_embeddings(texts):

    load_embedding_cache()

    model = get_embedding_model()

    unique_texts = list(dict.fromkeys(texts))

    missing_texts = [
        text for text in unique_texts
        if text not in _embedding_cache
    ]

    if missing_texts:

        generated_embeddings = model.embed(
            missing_texts
        )

        
        for text, embedding in zip(
            missing_texts,
            generated_embeddings
        ):

            _embedding_cache[text] = [
                float(value) for value in embedding
            ]
        CACHE_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        temp_file = EMBEDDING_CACHE_FILE.with_suffix(".tmp")

        with open(
            temp_file,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(_embedding_cache, file)

        temp_file.replace(EMBEDDING_CACHE_FILE)

    return {
        text: _embedding_cache[text]
        for text in unique_texts
    }

# --------------------------------------------------
# COSINE SIMILARITY
# --------------------------------------------------

def cosine_similarity(vector_a, vector_b):

    dot_product = sum(
        a * b for a, b in zip(vector_a, vector_b)
    )

    magnitude_a = sum(a * a for a in vector_a) ** 0.5
    magnitude_b = sum(b * b for b in vector_b) ** 0.5

    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0

    return dot_product / (magnitude_a * magnitude_b)


# --------------------------------------------------
# FLATTEN RESUME EVIDENCE
# --------------------------------------------------

def flatten_evidence(evidence_sections):

    evidence_list = []

    for section in evidence_sections:

        if isinstance(section, str):

            if section.strip():
                evidence_list.append(section.strip())

        elif isinstance(section, list):

            evidence_list.extend(
                item.strip()
                for item in section
                if isinstance(item, str) and item.strip()
            )

    return list(dict.fromkeys(evidence_list))


# --------------------------------------------------
# FIND RELEVANT EVIDENCE
# --------------------------------------------------

def find_relevant_evidence(requirement, evidence_sections):

    if not requirement or not evidence_sections:
        return []

    requirement = normalize_jd_skill(requirement)

    evidence_list = flatten_evidence(
        evidence_sections
    )

    if not evidence_list:
        return []

    # Embed requirement and evidence together.
    all_texts = [requirement] + evidence_list

    embeddings = get_embeddings(all_texts)

    requirement_embedding = embeddings[requirement]

    results = []

    for evidence in evidence_list:

        score = cosine_similarity(
            requirement_embedding,
            embeddings[evidence]
        )

        if score >= SIMILARITY_THRESHOLD:

            results.append({
                "evidence": evidence,
                "similarity": score
            })

    results.sort(
        key=lambda item: item["similarity"],
        reverse=True
    )

    return results[:TOP_K]


# --------------------------------------------------
# LOAD VERIFICATION CACHE
# --------------------------------------------------

def get_verification_cache():

    global _verification_cache

    if _verification_cache is None:

        try:

            with open(
                VERIFICATION_CACHE_FILE,
                "r",
                encoding="utf-8"
            ) as file:

                _verification_cache = json.load(file)

        except (FileNotFoundError, json.JSONDecodeError, OSError):

            _verification_cache = {}

    return _verification_cache


# --------------------------------------------------
# SAVE VERIFICATION CACHE
# --------------------------------------------------

def save_verification_cache():

    CACHE_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    temp_file = VERIFICATION_CACHE_FILE.with_suffix(".tmp")

    with open(
        temp_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            _verification_cache,
            file,
            indent=2
        )

    temp_file.replace(VERIFICATION_CACHE_FILE)


# --------------------------------------------------
# VERIFICATION CACHE KEY
# --------------------------------------------------

def get_verification_cache_key(requirement, evidence):

    cache_input = (
        CACHE_VERSION
        + LLM_MODEL
        + requirement.casefold().strip()
        + evidence.casefold().strip()
    )

    return hashlib.sha256(
        cache_input.encode("utf-8")
    ).hexdigest()


# --------------------------------------------------
# VERIFY EVIDENCE USING LLM
# --------------------------------------------------

def verify_evidence_with_llm(requirement, evidence):

    cache = get_verification_cache()

    cache_key = get_verification_cache_key(
        requirement,
        evidence
    )

    # Check cache before calling Ollama
    if cache_key in cache:
        return cache[cache_key]

    prompt = f"""
You are a strict resume skill verification system.

Determine whether the exact resume evidence directly proves
the job requirement.

JOB REQUIREMENT:
{requirement}

RESUME EVIDENCE:
{evidence}

STRICT RULES:

1. Use ONLY the supplied resume evidence.
2. Do not assume the candidate has an unstated skill.
3. Related technologies do not automatically prove another skill.
4. SQL does not automatically prove database design or query optimization.
5. Docker does not prove Kubernetes.
6. REST API development does not automatically prove microservices.
7. Accept clearly equivalent wording when evidence establishes
   the same capability.
8. When uncertain, return false.

Return JSON:
{{
    "supported": false
}}
"""

    try:

        response = _http_session.post(
            OLLAMA_URL,
            json={
                "model": LLM_MODEL,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "keep_alive": "30m",
                "options": {
                    "temperature": 0,
                    "num_predict": 100
                }
            },
            timeout=120
        )

        response.raise_for_status()

        response_data = response.json()

        raw_response = response_data.get(
            "response", ""
        )

        result = json.loads(raw_response)

        supported = (
            result.get("supported") is True
        )

        # Save decision for future reuse
        cache[cache_key] = supported

        save_verification_cache()

        return supported

    except (
        requests.RequestException,
        json.JSONDecodeError,
        ValueError
    ):

        return False


# --------------------------------------------------
# MAIN SEMANTIC MATCH FUNCTION
# --------------------------------------------------

def semantic_match(requirement, evidence_sections):

    candidates = find_relevant_evidence(
        requirement,
        evidence_sections
    )

    if not candidates:
        return False

    for candidate in candidates:

        supported = verify_evidence_with_llm(
            requirement,
            candidate["evidence"]
        )

        if supported:
            return True

    return False
