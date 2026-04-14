"""
Merge image analysis results with the original Excel data.

Usage:
    python merge_excel_with_analysis.py --excel Health_and_Influencers_Jan_24-June_25.xlsx --analysis image_analysis_results.csv --output enriched_data.xlsx
"""

import argparse
import re
from pathlib import Path

import pandas as pd


def extract_shortcode(url: str) -> str:
    """Extract Instagram shortcode from URL."""
    if pd.isna(url):
        return ""
    match = re.search(r'/(?:p|reel|tv)/([A-Za-z0-9_-]+)', str(url))
    return match.group(1) if match else ""


def main():
    parser = argparse.ArgumentParser(description="Merge Excel data with image analysis results")
    parser.add_argument("--excel", type=Path, required=True, help="Original Excel file")
    parser.add_argument("--analysis", type=Path, required=True, help="Image analysis CSV from pipeline")
    parser.add_argument("--output", type=Path, default=Path("enriched_data.xlsx"), help="Output Excel file")
    parser.add_argument("--header-row", type=int, default=9, help="Header row in Excel (0-indexed)")
    
    args = parser.parse_args()
    
    print(f"Loading Excel: {args.excel}")
    excel_df = pd.read_excel(args.excel, header=args.header_row)
    print(f"  Rows: {len(excel_df)}, Columns: {list(excel_df.columns)}")
    
    print(f"\nLoading analysis: {args.analysis}")
    analysis_df = pd.read_csv(args.analysis)
    print(f"  Rows: {len(analysis_df)}, Columns: {list(analysis_df.columns)}")
    
    print(f"\nExtracting shortcodes from Excel...")
    excel_df['shortcode'] = excel_df['Url'].apply(extract_shortcode)
    matched_count = excel_df['shortcode'].isin(analysis_df['shortcode']).sum()
    print(f"  Shortcodes in Excel: {len(excel_df)}")
    print(f"  Shortcodes that will match analysis: {matched_count}")
    
    merge_columns = ['shortcode', 'image_path', 'instagram_url', 'in_excel']
    analysis_subset = analysis_df[[c for c in merge_columns if c in analysis_df.columns]].copy()
    
    if 'theme' in analysis_df.columns:
        for col in ['theme', 'theme_confidence', 'content_type', 'visual_appeal_score', 'engagement_potential']:
            if col in analysis_df.columns:
                analysis_subset[col] = analysis_df[col]
    
    if 'main_subject' in analysis_df.columns:
        for col in ['image_type', 'main_subject', 'setting', 'visual_theme', 'mood', 'has_text_overlay', 'brand_visibility', 'quality_score']:
            if col in analysis_df.columns:
                analysis_subset[col] = analysis_df[col]
    
    print(f"\nMerging datasets...")
    enriched_df = excel_df.merge(analysis_subset, on='shortcode', how='left')
    
    matched = enriched_df['image_path'].notna().sum()
    print(f"  Successfully matched: {matched} rows")
    
    output_path = args.output
    enriched_df.to_excel(output_path, index=False)
    print(f"\nSaved enriched data to: {output_path}")
    
    print(f"\n=== Summary ===")
    print(f"Total rows: {len(enriched_df)}")
    print(f"With image analysis: {enriched_df['image_path'].notna().sum()}")
    print(f"Without image analysis: {enriched_df['image_path'].isna().sum()}")
    
    if 'theme' in enriched_df.columns:
        print(f"\nTheme distribution (analyzed images only):")
        theme_counts = enriched_df[enriched_df['image_path'].notna()]['theme'].value_counts()
        print(theme_counts.to_string())


if __name__ == "__main__":
    main()
