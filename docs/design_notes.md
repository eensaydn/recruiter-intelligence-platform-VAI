## Part 2: Data Modeling & System Thinking

### Talent Schema

The talent schema stores candidate profiles uploaded by recruiters. The core idea is separating candidate identity from their preferences and skills so each piece can be updated independently.

Tables:

`candidates` stores the core identity record:
- candidate_id (PK, UUID)
- first_name, last_name
- email (unique)
- phone
- linkedin_url
- current_title
- current_company
- years_of_experience (int)
- seniority_level (enum: junior, mid, senior, lead, manager, director)
- work_authorization (enum: citizen, permanent_resident, visa_holder, requires_sponsorship)
- created_at, updated_at
- created_by (FK to recruiter)

`candidate_skills` is a many-to-many junction table:
- candidate_id (FK)
- skill_id (FK to shared skills lookup table)
- proficiency (enum: beginner, intermediate, advanced, expert)
- years_experience (int, nullable)

`skills` is a shared lookup table, same one used by job normalization:
- skill_id (PK)
- name (unique, lowercase)
- category (e.g. "programming_language", "framework", "cloud", "soft_skill")

`candidate_preferences` stores what the candidate is looking for:
- candidate_id (FK, one-to-one)
- preferred_roles (text array, e.g. ["data engineer", "backend engineer"])
- preferred_locations (text array)
- remote_preference (enum: remote_only, hybrid, onsite, flexible)
- salary_min, salary_max (numeric)
- salary_currency (e.g. USD, GBP, INR)
- notice_period_days (int, nullable)
- willing_to_relocate (boolean)

Why this structure? Keeping skills in a separate junction table lets us query across candidates ("find everyone who knows Python at expert level") without parsing strings. The shared skills table also means we can match candidates to jobs using the same vocabulary. Preferences live in their own table because they change more often than identity data and we might want to track preference history later.

---

### Company Enrichment Design

The idea is having a `companies_raw` table that stores whatever we extract from job posts (just company name, maybe a logo URL), and a separate `companies_enriched` table for data pulled from external APIs like Apollo, Crunchbase, or LinkedIn.

`companies_raw` (extracted from job posts):
- company_id (PK, UUID)
- name (as seen in job post)
- name_normalized (lowercased, stripped of suffixes like "Inc", "Ltd")
- logo_url
- first_seen_at
- source (which job board we first saw them on)

`companies_enriched` (from Apollo/Crunchbase):
- company_id (FK)
- domain (e.g. "stripe.com")
- industry
- employee_count_range (e.g. "51-200")
- founded_year
- hq_city, hq_country
- funding_stage (e.g. "Series B", "Public")
- total_funding_usd
- linkedin_url
- description
- enriched_at (timestamp)
- enrichment_source (e.g. "apollo", "crunchbase")

Identity resolution is the tricky part. Matching "Capgemini" from Naukri to "Capgemini Technology Services India Limited" from a different post requires a few steps:

1. Normalize names: lowercase, remove legal suffixes (Inc, Ltd, LLC, GmbH), strip punctuation
2. Fuzzy match with something like rapidfuzz, using a threshold around 85% similarity
3. If we have a domain from enrichment, use that as the authoritative key
4. Keep a company_aliases table to track name variants pointing to the same entity

This is a classic entity resolution problem. For an MVP, normalized name + fuzzy matching is enough. In production, I'd add a manual review queue for low-confidence matches.

---

### Job-to-Talent Matching Approach

For the MVP, I'd go rule-based and explainable. Score each candidate-job pair on a few structured dimensions:

1. Skill overlap (0-100): matched skills / total required skills * 100
2. Seniority fit (0 or 1): does the candidate's level match? Allow +/- 1 level tolerance
3. Location match (0 or 1): does the candidate's preferred location work, or is the job remote?
4. Salary fit (0 or 1): is there overlap between what the candidate expects and what the job offers?
5. Work type match (0 or 1): candidate wants remote, job is remote? etc.

Final score is a weighted sum: `0.4 * skill_overlap + 0.2 * seniority + 0.15 * location + 0.15 * salary + 0.1 * work_type`

Why rule-based first? It's explainable (recruiter sees exactly why someone scored high or low), debuggable (you can trace the logic when something looks off), and doesn't need training data we don't have yet.

Future improvements with AI:
- Use sentence transformer embeddings to compute semantic similarity between descriptions and resumes, catching matches that keyword overlap misses
- Train a ranking model on recruiter feedback (which candidates they actually contacted)
- Use LLMs to extract structured requirements from free-text descriptions

Challenges worth noting:
- Skill vocabulary mismatch ("React.js" vs "React" vs "ReactJS") needs a synonym table
- Seniority is contextual: "Senior" at a 10-person startup vs a Fortune 500 bank are different things
- Cross-currency salary comparison needs FX conversion and cost-of-living adjustment
- Cold start problem: no feedback data initially to tune the weights

---

### Hiring Intent Design

The goal is estimating how likely a company is to be actively hiring, and at what intensity.

Signals from our own data:
- Job posting velocity: how many new posts in the last 7/30 days? An increasing trend means high intent
- Role diversity: posting for 1 role vs 10 different roles signals different hiring stages
- Posting freshness: are posts recent or stale?
- Reposting patterns: same role posted multiple times usually means it's urgent or hard to fill

External signals (future, via enrichment):
- Funding events: company just raised a round? Hiring spree is likely
- Headcount growth: LinkedIn employee count trending up
- Multi-board presence: posting on Dice, Naukri, and Reed simultaneously signals serious intent

MVP scoring approach (rule-based):

```
intent_score = 0
if posts_last_7_days > 5:     intent_score += 30
if posts_last_30_days > 15:   intent_score += 20
if unique_roles > 3:          intent_score += 20
if avg_post_age_days < 7:     intent_score += 15
if has_reposted_roles:        intent_score += 15
```

Bucket into High (70+), Medium (40-69), Low (<40).

Confidence depends on data completeness. Seeing a company on 1 board with 1 post means low confidence regardless of the intent score. More data points = higher confidence.

Limitations:
- We only see what's on the boards we scrape. A company could be hiring heavily through referrals or agencies
- Posting doesn't guarantee the role is actually open (ghost postings are common)
- Small companies might have high intent but low posting volume, so they'd score low
- Can't distinguish "backfill" from "growth" hiring without enrichment data

---

## Part 3: Future AI / RAG Extension

### Recruiter-Facing AI Assistant

What data goes into the RAG system:
- Normalized job postings (the pipeline output)
- Candidate profiles (from the talent schema)
- Company enrichment data
- Historical match outcomes (which candidates got placed where)
- Recruiter notes and interaction logs

How to structure and index it:

Each document type gets its own collection in a vector store (Qdrant, Pinecone, or pgvector if we want to keep things simple).

Job postings are short enough to embed whole, no chunking needed. Use a sentence transformer for embeddings and store structured fields (seniority, location, salary range) as metadata for filtered search. A query like "show me remote senior Python roles" would use metadata filters for the hard constraints and vector similarity for the soft matching.

Candidate profiles get embedded as a concatenation of title + skills + summary. Metadata: seniority, location, salary range.

Company data gets embedded by description + industry. Metadata: size, funding stage, location.

Why hybrid search matters: pure vector search misses exact requirements like "must have AWS certification". Pure keyword search misses semantic matches like "cloud infrastructure" matching "AWS". Combining metadata filters for hard requirements with vector similarity for soft matching gives the best results.

Metadata and access control:
- Every document gets a recruiter_id or team_id tag
- Query-time filtering ensures recruiters only see candidates in their own pool
- Company data and job postings are shared across all recruiters
- PII (candidate email, phone) stays in the structured DB, not in the vector store

Update strategy:
- Job postings: re-index daily, remove expired ones (past validThrough date)
- Candidate profiles: re-index on update, track updated_at and only re-embed changed records
- Company data: re-index weekly after enrichment runs
- Each record gets a last_indexed_at timestamp to track what needs re-embedding

Failure modes to watch for:

Stale data: RAG returns a job that was filled 2 weeks ago. Fix with TTL on job documents and aggressive expiry.

Hallucinated matches: LLM claims a candidate has a skill they don't, based on loose semantic similarity. Fix by always grounding responses in structured data and showing source records.

Embedding drift: swapping embedding models means all vectors need re-indexing. Plan for this upfront.

Context window limits: recruiter asks "show me all candidates for this role" and there are 500 matches. Need a retrieval + ranking step before stuffing context. Top-K retrieval with reranking (Cohere rerank or a cross-encoder) handles this.

Access control leaks: if metadata filtering is implemented wrong, one recruiter might see another's candidates. This needs thorough testing.
