import re

def extract_experience_duration(text: str) -> dict:
    """Convert an experience duration phrase into months."""

    if not text:
        return {"minimum_months": None, "maximum_months": None}

    value = text.casefold()
    value = re.sub(r"[–—−]", "-", value)
    value = re.sub(r"\s+", " ", value)

    # 3-5 years, 3 to 5 years, 6-12 months
    match = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:-|to)\s*"
        r"(\d+(?:\.\d+)?)\s*(years?|yrs?|months?|mos?)\b",
        value
    )

    if match:
        multiplier = (
            12 if match.group(3).startswith(("year", "yr")) else 1
        )

        return {
            "minimum_months": int(float(match.group(1)) * multiplier),
            "maximum_months": int(float(match.group(2)) * multiplier)
        }

    # 3+ years, 6+ months, 3 or more years
    match = re.search(
        r"(\d+(?:\.\d+)?)\s*\+\s*(years?|yrs?|months?|mos?)\b",
        value
    )

    if not match:
        match = re.search(
            r"(\d+(?:\.\d+)?)\s+or\s+more\s+(years?|yrs?|months?|mos?)\b",
            value
        )

    if match:
        multiplier = (
            12 if match.group(2).startswith(("year", "yr")) else 1
        )

        return {
            "minimum_months": int(float(match.group(1)) * multiplier),
            "maximum_months": None
        }

    # 1 year and 6 months
    match = re.search(
        r"(\d+(?:\.\d+)?)\s*(years?|yrs?)"
        r"(?:\s*(?:and)?\s*(\d+(?:\.\d+)?)\s*(months?|mos?))?",
        value
    )

    if match:
        total = int(
            float(match.group(1)) * 12 +
            float(match.group(3) or 0)
        )

        return {
            "minimum_months": total,
            "maximum_months": None
        }

    # Standalone months
    match = re.search(
        r"(\d+(?:\.\d+)?)\s*(months?|mos?)\b",
        value
    )

    if match:
        return {
            "minimum_months": int(float(match.group(1))),
            "maximum_months": None
        }

    # Standalone years
    match = re.search(
        r"(\d+(?:\.\d+)?)\s*(years?|yrs?)\b",
        value
    )

    if match:
        return {
            "minimum_months": int(float(match.group(1)) * 12),
            "maximum_months": None
        }

    return {"minimum_months": None, "maximum_months": None}

def _heading_category(line: str, current: str) -> str:

    heading = line.casefold().strip(" #:-*•\t")

    # Handle inline headings such as:
    # Preferred experience: 3+ years
    # Required qualifications: Python, SQL
    heading = re.split(r"[:：]", heading, maxsplit=1)[0].strip()

    heading = re.sub(r"\s+", " ", heading)

    preferred = (
        "preferred qualifications",
        "preferred qualification",
        "preferred skills",
        "preferred experience",
        "nice to have",
        "good to have",
        "desirable qualifications",
        "desired qualifications",
        "bonus qualifications",
    )

    required = (
        "required qualifications",
        "required qualification",
        "required skills",
        "required experience",
        "minimum qualifications",
        "basic qualifications",
        "mandatory requirements",
        "must have",
        "additional requirements",
        "qualifications",
        "requirements",
    )

    if any(
        heading == item or heading.startswith(item + " ")
        for item in preferred
    ):
        return "preferred"

    if any(
        heading == item or heading.startswith(item + " ")
        for item in required
    ):
        return "required"

    return current


def extract_jd_experience(job_description: str) -> dict:
    """Extract required and preferred experience, including inline JDs."""

    result = {
        "required": {
            "professional": None,
            "internship": None,
            "alternative_paths": [],
        },
        "preferred": {
            "professional": None,
            "internship": None,
            "alternative_paths": [],
        },
    }

    # Detect experience headings anywhere in the JD,
    # including when multiple headings appear on one line.
    headings = list(re.finditer(
        r"\b(required|preferred)\s+experience\s*[:：]",
        job_description,
        flags=re.IGNORECASE
    ))

    # Handle inline / continuous paragraph format.
    if headings:
        for index, heading in enumerate(headings):

            category = heading.group(1).casefold()

            start = heading.end()
            end = (
                headings[index + 1].start()
                if index + 1 < len(headings)
                else len(job_description)
            )

            segment = job_description[start:end].strip()
            lower = segment.casefold()

            duration = extract_experience_duration(segment)

            if duration["minimum_months"] is None:
                continue

            experience_type = (
                "internship"
                if re.search(r"\bintern(ship)?s?\b", lower)
                else "professional"
            )

            existing = result[category][experience_type]

            if existing is None:
                result[category][experience_type] = duration
            else:
                mins = [
                    v for v in (
                        existing.get("minimum_months"),
                        duration.get("minimum_months")
                    ) if v is not None
                ]

                maxes = [
                    v for v in (
                        existing.get("maximum_months"),
                        duration.get("maximum_months")
                    ) if v is not None
                ]

                result[category][experience_type] = {
                    "minimum_months": max(mins) if mins else None,
                    "maximum_months": max(maxes) if maxes else None,
                }

            if experience_type == "internship" and any(
                phrase in lower for phrase in (
                    "encouraged to apply",
                    "also encouraged",
                    "alternative",
                    "instead of",
                    "in lieu of",
                    "may also apply",
                    "will also be considered",
                )
            ):
                note = segment.rstrip(".")
                if note not in result[category]["alternative_paths"]:
                    result[category]["alternative_paths"].append(note)

        return result

    # Original multiline extraction logic.
    current_category = "required"

    for raw_line in job_description.splitlines():
        line = raw_line.strip(" \t-*\u2022")

        if not line:
            continue

        current_category = _heading_category(
            line, current_category
        )

        lower = line.casefold()
        duration = extract_experience_duration(line)

        if duration["minimum_months"] is None:
            continue

        experience_type = (
            "internship"
            if re.search(r"\bintern(ship)?s?\b", lower)
            else "professional"
        )

        existing = result[current_category][experience_type]

        if existing is None:
            result[current_category][experience_type] = duration
        else:
            mins = [
                v for v in (
                    existing.get("minimum_months"),
                    duration.get("minimum_months")
                ) if v is not None
            ]

            maxes = [
                v for v in (
                    existing.get("maximum_months"),
                    duration.get("maximum_months")
                ) if v is not None
            ]

            result[current_category][experience_type] = {
                "minimum_months": max(mins) if mins else None,
                "maximum_months": max(maxes) if maxes else None,
            }

        if experience_type == "internship" and any(
            phrase in lower for phrase in (
                "encouraged to apply",
                "also encouraged",
                "alternative",
                "instead of",
                "in lieu of",
                "may also apply",
                "will also be considered",
            )
        ):
            note = line.rstrip(".")
            if note not in result[current_category]["alternative_paths"]:
                result[current_category]["alternative_paths"].append(note)

    return result
