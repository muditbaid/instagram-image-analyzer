"""
Merge Image Analysis Results with Excel Data

Students run this after getting CSV from Gemini.

Usage:
    python merge_results.py --analysis image_analysis.csv

Requirements:
- image_analysis.csv with 'shortcode' column from Gemini
- Original Excel file in the same folder
"""

import argparse
import re
from pathlib import Path

import pandas as pd


def extract_shortcode(url: str) -> str:
    if pd.isna(url):
        return ""
    match = re.search(r'/(?:p|reel|tv)/([A-Za-z0-9_-]+)', str(url))
    return match.group(1) if match else ""


def main():
    parser = argparse.ArgumentParser(description="Merge Gemini image analysis with Excel data")
    parser.add_argument("--analysis", type=Path, default=Path("image_analysis.csv"), help="CSV from Gemini")
    parser.add_argument("--excel", type=Path, default=Path("Health_and_Influencers_Jan_24-June_25.xlsx"), help="Original Excel")
    parser.add_argument("--output", type=Path, default=Path("enriched_data.xlsx"), help="Output file")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("IMAGE ANALYSIS MERGE TOOL")
    print("=" * 60)
    
    if not args.excel.exists():
        print(f"ERROR: Excel file not found: {args.excel}")
        print("Make sure your Excel file is in the same folder")
        return
    
    if not args.analysis.exists():
        print(f"ERROR: Analysis file not found: {args.analysis}")
        print("This should be the CSV you got from Gemini")
        return
    
    print(f"\n1. Loading Excel: {args.excel.name}")
    excel_df = pd.read_excel(args.excel, header=9)
    print(f"   Rows: {len(excel_df)}")
    
    print(f"\n2. Loading Analysis: {args.analysis.name}")
    analysis_df = pd.read_csv(args.analysis)
    print(f"   Rows: {len(analysis_df)}")
    
    print(f"\n3. Extracting shortcodes from Excel...")
    excel_df['shortcode'] = excel_df['Url'].apply(extract_shortcode)
    
    excel_shortcodes = set(excel_df['shortcode'])
    analysis_shortcodes = set(analysis_df['shortcode'])
    match_count = len(excel_shortcodes & analysis_shortcodes)
    
    print(f"   Shortcodes in Excel: {len(excel_shortcodes)}")
    print(f"   Shortcodes in Analysis: {len(analysis_shortcodes)}")
    print(f"   Matched: {match_count}")
    
    if match_count == 0:
        print("\nWARNING: No matches found!")
        print("Check that your shortcode column names match")
        print(f"Excel columns: {list(excel_df.columns[:5])}...")
        print(f"Analysis columns: {list(analysis_df.columns)}")
        return
    
    merge_cols = ['shortcode']
    for col in analysis_df.columns:
        if col != 'shortcode':
            new_name = f"image_{col}"
            merge_cols.append(col)
    
    analysis_subset = analysis_df[merge_cols].copy()
    analysis_subset.columns = ['shortcode'] + [f"image_{c}" for c in analysis_df.columns if c != 'shortcode']
    
    print(f"\n4. Merging data...")
    merged = excel_df.merge(analysis_subset, on='shortcode', how='left')
    
    matched = merged['image_shortcode'].notna().sum() if 'image_shortcode' in merged.columns else merged['image_shortcode' in merged.columns].sum()
    
    print(f"   Total rows: {len(merged)}")
    print(f"   With image analysis: {matched}")
    
    merged.to_excel(args.output, index=False)
    print(f"\n5. SAVED: {args.output}")
    
    print("\n" + "=" * 60)
    print("DONE!")
    print("=" * 60)
    
    if 'image_theme' in merged.columns:
        print("\nTheme breakdown (analyzed images only):")
        themes = merged[merged['image_shortcode'].notna()]['image_theme'].value_counts()
        for theme, count in themes.items():
            print(f"  {theme}: {count}")


if __name__ == "__main__":
    main()
