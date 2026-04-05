"""
Recruiter Intelligence Platform - Data Pipeline
Reads raw job data from 3 sources, normalizes into unified schema, outputs clean CSV.

Usage:
    python pipeline.py
"""

import os
import pandas as pd
from transformers import transform_dice, transform_naukri, transform_reed


# paths
RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "output")


def run_pipeline():
    """Main pipeline: read -> transform -> merge -> validate -> write."""

    print("=" * 60)
    print("Recruiter Intelligence Platform - Data Pipeline")
    print("=" * 60)

    # --- Transform each source ---
    print("\n[1/4] Transforming Dice data...")
    dice_df = transform_dice(os.path.join(RAW_DIR, "dataset_dice_jobs.csv"))
    print(f"  -> {len(dice_df)} records")

    print("[2/4] Transforming Naukri data...")
    naukri_df = transform_naukri(os.path.join(RAW_DIR, "dataset_naukri_jobs.csv"))
    print(f"  -> {len(naukri_df)} records")

    print("[3/4] Transforming Reed data...")
    reed_df = transform_reed(os.path.join(RAW_DIR, "dataset_reed_jobs.csv"))
    print(f"  -> {len(reed_df)} records")

    # --- Merge ---
    merged = pd.concat([dice_df, naukri_df, reed_df], ignore_index=True)
    print(f"\n[4/4] Merged total: {len(merged)} records")

    # --- Deduplicate ---
    before_dedup = len(merged)
    merged = merged.drop_duplicates(subset=["job_id"], keep="first")
    after_dedup = len(merged)
    if before_dedup != after_dedup:
        print(f"  -> Removed {before_dedup - after_dedup} duplicate job_ids")

    # --- Write output ---
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, "normalized_jobs.csv")
    merged.to_csv(output_path, index=False)
    print(f"\nOutput written to: {output_path}")

    # --- Data Quality Report ---
    print_quality_report(merged)

    return merged


def print_quality_report(df: pd.DataFrame):
    """Print a simple data quality summary."""
    print("\n" + "=" * 60)
    print("DATA QUALITY REPORT")
    print("=" * 60)

    # records per source
    print("\nRecords per source:")
    for source, count in df["source"].value_counts().items():
        print(f"  {source}: {count}")

    # null percentages
    print("\nNull percentage per column:")
    null_pct = (df.isnull().sum() / len(df) * 100).round(1)
    for col, pct in null_pct.items():
        indicator = "!!" if pct > 50 else ""
        print(f"  {col:20s} {pct:6.1f}% {indicator}")

    # seniority distribution
    print("\nSeniority distribution:")
    for level, count in df["seniority"].value_counts().items():
        print(f"  {level}: {count}")

    # work_type distribution
    print("\nWork type distribution:")
    for wt, count in df["work_type"].value_counts(dropna=False).items():
        label = wt if wt else "(null)"
        print(f"  {label}: {count}")

    # salary coverage
    has_salary = df["salary_min"].notna().sum()
    print(f"\nSalary data available: {has_salary}/{len(df)} ({has_salary/len(df)*100:.1f}%)")

    # skills coverage
    has_skills = df["skills"].notna().sum()
    print(f"Skills data available: {has_skills}/{len(df)} ({has_skills/len(df)*100:.1f}%)")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    run_pipeline()
