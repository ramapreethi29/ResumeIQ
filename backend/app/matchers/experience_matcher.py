
def match_experience_category(
    requirement: dict | None,
    resume_months: int | None
) -> dict:

    result = {
        "match": [],
        "unmatch": [],
        "unknown": []
    }

    if requirement is None:
        return result

    minimum = requirement.get("minimum_months")
    maximum = requirement.get("maximum_months")

    item = {
        "required_experience": requirement,
        "resume_experience_months": resume_months
    }

    if resume_months is None:
        item["reason"] = "Resume experience information is unavailable."
        result["unknown"].append(item)
        return result

    if minimum is not None and resume_months < minimum:
        item["reason"] = "Resume experience is below the minimum required."
        result["unmatch"].append(item)

    elif maximum is not None and resume_months > maximum:
        item["reason"] = "Resume experience exceeds the specified maximum."
        result["unmatch"].append(item)

    else:
        item["reason"] = "Resume experience satisfies the requirement."
        result["match"].append(item)

    return result


def match_experience(jd_data: dict, resume_data: dict) -> dict:

    jd_experience = {
        "required": jd_data["required"]["experience"],
        "preferred": jd_data["preferred"]["experience"]
    }

    resume_experience = resume_data.get("experience", {})

    return {
        category: {
            "professional": match_experience_category(
                jd_experience[category].get("professional"),
                resume_experience.get("professional_months")
            ),

            "internship": match_experience_category(
                jd_experience[category].get("internship"),
                resume_experience.get("internship_months")
            )
        }
        for category in ["required", "preferred"]
    }
