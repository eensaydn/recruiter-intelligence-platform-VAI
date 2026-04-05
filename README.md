# Recruiter Intelligence Platform

A data pipeline that takes job postings from three different job boards (Dice, Naukri, Reed) and normalizes them into a single clean schema. The output is ready for analytics or downstream AI workflows.

## How to Run

```bash
cd recruiter-intelligence-platform
pip install -r requirements.txt

# put the 3 raw CSVs in data/raw/
cd src
python pipeline.py
```

Output goes to `data/output/normalized_jobs.csv`.

## Dependencies

- Python 3.10+
- pandas >= 2.0.0

Everything else is standard library (`re`, `ast`). No heavy dependencies.

## Project Structure

```
├── data/
│   ├── raw/                    # original CSVs from 3 job boards
│   └── output/                 # normalized_jobs.csv
├── src/
│   ├── pipeline.py             # main entry point
│   ├── transformers.py         # per-source transformation logic
│   └── utils.py                # shared helpers (parsing, normalization)
├── docs/
│   └── design_notes.md         # Part 2 & 3 design writeup
├── README.md
└── requirements.txt
```

## Unified Schema

| Column | Type | Description |
|--------|------|-------------|
| job_id | string | unique, prefixed by source (e.g. dice_abc123) |
| source | string | dice, naukri, or reed |
| title | string | job title as posted |
| company_name | string | hiring company |
| location_raw | string | original location string, kept for reference |
| city | string | parsed city |
| state_region | string | state or region, nullable |
| country | string | country code or name |
| work_type | string | remote, onsite, or hybrid |
| employment_type | string | full_time, contract, permanent, internship |
| seniority | string | junior, mid, senior, lead, manager, director |
| industry | string | only available from Reed, null for others |
| skills | string | comma-separated skill list |
| salary_min | float | nullable |
| salary_max | float | nullable |
| salary_currency | string | USD, GBP, or INR |
| salary_period | string | yearly, monthly, hourly, daily |
| date_posted | string | ISO format |
| url | string | link to original posting |
| description | string | plain text job description |

## Assumptions

Seniority is inferred from job titles via keyword matching. "Senior Data Engineer" becomes "senior", "Manager, Medical Economics" becomes "manager". Anything without a clear keyword defaults to "mid". This is simple and has edge cases, but it works for the majority of titles.

Most Naukri postings hide salary ("Not disclosed"). When salary is present in the format "4-8 Lacs PA", it gets converted to INR using 1 Lac = 100,000.

Reed has no structured skills field, so the skills column is null for all Reed records. Extracting skills from description text would be a natural next step but felt like scope creep for this exercise.

Dice has three separate boolean columns for remote/onsite/hybrid. When both remote and onsite are true, I treat it as hybrid since the role apparently supports both.

Naukri has no explicit work type field. If the location string is literally "Remote", I flag it as remote. Otherwise it defaults to onsite.

Naukri postings without an explicit job type are assumed full_time. That's the dominant pattern on the platform.

## Limitations

No skill extraction from descriptions. Reed records have null skills because of this. Adding keyword extraction or NER would help but goes beyond MVP scope.

Salaries are stored in their original currencies (USD, GBP, INR) without conversion. Cross-currency comparison would need FX rates and ideally cost-of-living normalization.

Company identity resolution isn't implemented. "Capgemini" and "Capgemini Technology Services India Limited" show up as separate entities. The design notes cover how I'd approach this with fuzzy matching and alias tracking.

The seniority extraction is keyword-based and has known edge cases. "Customer Success Manager" maps to "manager" which might not reflect actual seniority level.

The pipeline runs from scratch every time. For production use, you'd want incremental processing with change detection.

## Future Improvements

- Extract skills from job descriptions using keyword matching or a lightweight NER model
- Company entity resolution with fuzzy matching and an alias table
- Incremental pipeline that only processes new/changed records
- Salary normalization with currency conversion
- Data validation layer (great_expectations or pydantic)
- Database output (SQLite or PostgreSQL) instead of flat CSV
