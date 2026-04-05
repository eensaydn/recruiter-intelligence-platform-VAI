"""
Source-specific transformer functions.
Each function reads a raw CSV and returns a DataFrame with the unified schema.
"""

import pandas as pd
from utils import (
    extract_seniority,
    parse_dice_salary,
    parse_dice_skills,
    parse_dice_location,
    map_dice_work_type,
    parse_naukri_salary,
    map_naukri_work_type,
    map_reed_salary_period,
    map_reed_work_type,
    map_employment_type,
)


UNIFIED_COLUMNS = [
    "job_id",
    "source",
    "title",
    "company_name",
    "location_raw",
    "city",
    "state_region",
    "country",
    "work_type",
    "employment_type",
    "seniority",
    "industry",
    "skills",
    "salary_min",
    "salary_max",
    "salary_currency",
    "salary_period",
    "date_posted",
    "url",
    "description",
]


def transform_dice(filepath: str) -> pd.DataFrame:
    """Transform Dice job data into unified schema."""
    df = pd.read_csv(filepath)
    rows = []

    for _, r in df.iterrows():
        # location
        loc = parse_dice_location(
            str(r.get("locationDetail", "")),
            str(r.get("location", ""))
        )

        # salary
        sal = parse_dice_salary(str(r.get("salaryRaw", "")))

        # work type from boolean flags
        work_type = map_dice_work_type(
            bool(r.get("remote", False)),
            bool(r.get("onsite", False)),
            bool(r.get("hybrid", False)),
        )

        # employment type: combine contractType and positionSchedule
        emp_type = map_employment_type(str(r.get("contractType", "")), "dice")

        rows.append({
            "job_id": f"dice_{r.get('id', '')}",
            "source": "dice",
            "title": r.get("title"),
            "company_name": r.get("companyName"),
            "location_raw": r.get("location"),
            "city": loc["city"],
            "state_region": loc["state_region"],
            "country": loc["country"],
            "work_type": work_type,
            "employment_type": emp_type,
            "seniority": extract_seniority(str(r.get("title", ""))),
            "industry": None,  # Dice doesn't have industry
            "skills": parse_dice_skills(str(r.get("skills", ""))),
            "salary_min": sal["salary_min"],
            "salary_max": sal["salary_max"],
            "salary_currency": sal["salary_currency"],
            "salary_period": sal["salary_period"],
            "date_posted": r.get("datePosted"),
            "url": r.get("url"),
            "description": r.get("description"),
        })

    return pd.DataFrame(rows, columns=UNIFIED_COLUMNS)


def transform_naukri(filepath: str) -> pd.DataFrame:
    """Transform Naukri job data into unified schema."""
    df = pd.read_csv(filepath)
    rows = []

    for _, r in df.iterrows():
        location_str = str(r.get("location", ""))

        # Naukri location can be multi-city: "Kolkata, Mumbai, New Delhi"
        # Take the first city as primary
        cities = [c.strip() for c in location_str.split(",")]
        primary_city = cities[0] if cities and cities[0].lower() != "remote" else None

        # salary
        sal = parse_naukri_salary(str(r.get("salary", "")))

        # work type
        work_type = map_naukri_work_type(location_str)

        # skills: already comma-separated
        skills_raw = r.get("tagsAndSkills")
        skills = str(skills_raw).strip() if pd.notna(skills_raw) and str(skills_raw).strip() else None

        # employment type: Naukri's jobType is mostly empty
        job_type = r.get("jobType")
        emp_type = None
        if pd.notna(job_type) and str(job_type).strip():
            if "intern" in str(job_type).lower():
                emp_type = "internship"
            else:
                emp_type = str(job_type).lower()
        else:
            emp_type = "full_time"  # default assumption for Naukri

        rows.append({
            "job_id": f"naukri_{r.get('jobId', '')}",
            "source": "naukri",
            "title": r.get("title"),
            "company_name": r.get("companyName"),
            "location_raw": location_str,
            "city": primary_city,
            "state_region": None,  # Naukri doesn't provide state
            "country": "IN",
            "work_type": work_type,
            "employment_type": emp_type,
            "seniority": extract_seniority(str(r.get("title", ""))),
            "industry": None,  # Naukri doesn't have industry
            "skills": skills,
            "salary_min": sal["salary_min"],
            "salary_max": sal["salary_max"],
            "salary_currency": sal["salary_currency"],
            "salary_period": sal["salary_period"],
            "date_posted": r.get("createdDate"),
            "url": r.get("jdURL"),
            "description": r.get("jobDescription"),
        })

    return pd.DataFrame(rows, columns=UNIFIED_COLUMNS)


def transform_reed(filepath: str) -> pd.DataFrame:
    """Transform Reed job data into unified schema."""
    df = pd.read_csv(filepath)
    rows = []

    for _, r in df.iterrows():
        # salary
        sal_min = r.get("salaryMin")
        sal_max = r.get("salaryMax")
        sal_exact = r.get("salaryExact")

        salary_min = float(sal_min) if pd.notna(sal_min) else None
        salary_max = float(sal_max) if pd.notna(sal_max) else None

        # if exact salary is given but no min/max
        if salary_min is None and salary_max is None and pd.notna(sal_exact):
            salary_min = float(sal_exact)
            salary_max = float(sal_exact)

        rows.append({
            "job_id": f"reed_{r.get('id', '')}",
            "source": "reed",
            "title": r.get("title"),
            "company_name": r.get("companyName"),
            "location_raw": r.get("jobLocation"),
            "city": r.get("jobLocation"),
            "state_region": r.get("jobLocationRegion"),
            "country": r.get("jobLocationCountry"),
            "work_type": map_reed_work_type(str(r.get("jobLocationType", ""))),
            "employment_type": map_employment_type(str(r.get("employmentType", "")), "reed"),
            "seniority": extract_seniority(str(r.get("title", ""))),
            "industry": r.get("industry"),
            "skills": None,  # Reed doesn't have a skills field
            "salary_min": salary_min,
            "salary_max": salary_max,
            "salary_currency": r.get("currency") if pd.notna(r.get("currency")) else None,
            "salary_period": map_reed_salary_period(str(r.get("salaryTimeUnit", ""))),
            "date_posted": r.get("datePosted"),
            "url": r.get("url"),
            "description": r.get("descriptionText"),
        })

    return pd.DataFrame(rows, columns=UNIFIED_COLUMNS)
