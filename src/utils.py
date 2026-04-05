"""
Utility functions for job data normalization.
Handles seniority extraction, salary parsing, skills parsing, and work type mapping.
"""

import re
import ast


def extract_seniority(title: str) -> str | None:
    """
    Infer seniority level from job title using keyword matching.
    Returns one of: junior, mid, senior, lead, manager, director, or None.
    
    Priority: director > manager > lead > senior > junior > mid
    We check from highest to lowest so "Senior Director" maps to "director".
    """
    if not title or not isinstance(title, str):
        return None

    t = title.lower()

    if any(k in t for k in ["director", "vp ", "vice president", "head of", "chief ", "cto", "cfo", "ceo"]):
        return "director"
    if any(k in t for k in ["manager", "management"]):
        return "manager"
    if any(k in t for k in ["lead", "principal", "staff"]):
        return "lead"
    if any(k in t for k in ["senior", "sr.", "sr "]):
        return "senior"
    if any(k in t for k in ["junior", "jr.", "jr ", "trainee", "intern ", "entry", "graduate"]):
        return "junior"
    return "mid"


def parse_dice_salary(raw: str) -> dict:
    """
    Parse Dice salary strings like:
      - "USD 88,453.00 - 165,000.00 per year"
      - "USD 82,000.00 per year"
      - "Depends on Experience"
      - "Compensation information provided in the description"
    
    Returns dict with keys: salary_min, salary_max, salary_currency, salary_period
    """
    result = {"salary_min": None, "salary_max": None, "salary_currency": None, "salary_period": None}

    if not raw or not isinstance(raw, str):
        return result

    # skip non-numeric salary entries
    if any(skip in raw.lower() for skip in ["depends on", "provided in", "not specified"]):
        return result

    # extract currency (first 3 uppercase letters)
    currency_match = re.match(r"([A-Z]{3})", raw)
    if currency_match:
        result["salary_currency"] = currency_match.group(1)

    # extract numbers: handles "88,453.00" format
    numbers = re.findall(r"[\d,]+\.?\d*", raw)
    numbers = [float(n.replace(",", "")) for n in numbers if float(n.replace(",", "")) > 100]

    if len(numbers) >= 2:
        result["salary_min"] = numbers[0]
        result["salary_max"] = numbers[1]
    elif len(numbers) == 1:
        result["salary_min"] = numbers[0]
        result["salary_max"] = numbers[0]

    # period
    if "year" in raw.lower() or "annual" in raw.lower():
        result["salary_period"] = "yearly"
    elif "hour" in raw.lower():
        result["salary_period"] = "hourly"
    elif "month" in raw.lower():
        result["salary_period"] = "monthly"

    return result


def parse_naukri_salary(raw: str) -> dict:
    """
    Parse Naukri salary strings like:
      - "4-8 Lacs PA"
      - "20-25 Lacs PA"
      - "Not disclosed"
    
    1 Lac = 100,000 INR. PA = Per Annum.
    """
    result = {"salary_min": None, "salary_max": None, "salary_currency": "INR", "salary_period": "yearly"}

    if not raw or not isinstance(raw, str) or raw.lower() in ["not disclosed", "unpaid"]:
        result["salary_currency"] = None
        result["salary_period"] = None
        return result

    numbers = re.findall(r"[\d.]+", raw)
    if not numbers:
        result["salary_currency"] = None
        result["salary_period"] = None
        return result

    multiplier = 100_000 if "lac" in raw.lower() else 1

    if len(numbers) >= 2:
        result["salary_min"] = float(numbers[0]) * multiplier
        result["salary_max"] = float(numbers[1]) * multiplier
    elif len(numbers) == 1:
        result["salary_min"] = float(numbers[0]) * multiplier
        result["salary_max"] = float(numbers[0]) * multiplier

    return result


def parse_dice_skills(raw: str) -> str | None:
    """
    Parse Dice skills from string representation of list of dicts.
    Input: "[{'name': 'Python'}, {'name': 'SQL'}]"
    Output: "Python, SQL"
    """
    if not raw or not isinstance(raw, str):
        return None

    try:
        skills_list = ast.literal_eval(raw)
        names = [s["name"] for s in skills_list if isinstance(s, dict) and "name" in s]
        return ", ".join(names) if names else None
    except (ValueError, SyntaxError):
        return None


def parse_dice_location(location_detail: str, location_raw: str) -> dict:
    """
    Extract city, state/region, country from Dice locationDetail dict string.
    Falls back to location_raw if parsing fails.
    """
    result = {"city": None, "state_region": None, "country": None}

    if location_detail and isinstance(location_detail, str):
        try:
            loc = ast.literal_eval(location_detail)
            result["city"] = loc.get("city")
            result["state_region"] = loc.get("state")
            result["country"] = loc.get("country")
            return result
        except (ValueError, SyntaxError):
            pass

    # fallback: use raw location string
    if location_raw and isinstance(location_raw, str):
        result["city"] = location_raw

    return result


def map_dice_work_type(remote: bool, onsite: bool, hybrid: bool) -> str | None:
    """Map Dice boolean flags to a single work_type string."""
    if hybrid:
        return "hybrid"
    if remote and onsite:
        return "hybrid"
    if remote:
        return "remote"
    if onsite:
        return "onsite"
    return None


def map_reed_salary_period(unit: str) -> str | None:
    """Map Reed salary time unit to normalized period."""
    if not unit or not isinstance(unit, str):
        return None
    mapping = {
        "per annum": "yearly",
        "per hour": "hourly",
        "per day": "daily",
        "per month": "monthly",
    }
    return mapping.get(unit.lower())


def map_employment_type(raw: str, source: str) -> str | None:
    """
    Normalize employment type across sources.
    Returns: full_time, part_time, contract, permanent, internship, or None.
    """
    if not raw or not isinstance(raw, str):
        return None

    r = raw.lower().replace("_", " ").strip()

    if source == "dice":
        if "direct hire" in r or "direct_hire" in r.replace(" ", "_"):
            return "full_time"
        if "contract" in r:
            return "contract"

    if source == "reed":
        if r == "permanent":
            return "permanent"
        if r == "contract":
            return "contract"

    if "full" in r:
        return "full_time"
    if "part" in r:
        return "part_time"
    if "intern" in r:
        return "internship"
    if "contract" in r:
        return "contract"

    return raw.lower()


def map_reed_work_type(loc_type: str) -> str | None:
    """Map Reed jobLocationType to normalized work_type."""
    if not loc_type or not isinstance(loc_type, str):
        return None
    mapping = {
        "on-site": "onsite",
        "remote": "remote",
        "hybrid": "hybrid",
    }
    return mapping.get(loc_type.lower())


def map_naukri_work_type(location: str) -> str | None:
    """
    Naukri doesn't have an explicit work_type field.
    If location is "Remote", we flag it. Otherwise None (assume onsite).
    """
    if not location or not isinstance(location, str):
        return None
    if location.strip().lower() == "remote":
        return "remote"
    return "onsite"
