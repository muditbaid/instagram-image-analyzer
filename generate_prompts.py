"""
Generate Gemini App Prompts for Image Analysis

This creates ready-to-use prompts for students to copy-paste into Gemini app.

Usage:
    python generate_prompts.py --images images --output prompts.md
"""

import argparse
from pathlib import Path


GEMINI_ANALYSIS_PROMPT = """You are analyzing Instagram images for a social media research project.

## Your Task
Analyze ALL images in this folder and classify each one.

## Image Naming
Images are named with their Instagram shortcode (e.g., DAgykYOyWJ_.jpg)
This shortcode links to the original post at: https://www.instagram.com/p/[SHORTCODE]/

## Output Format
Create a CSV with these columns:
- shortcode: The image filename (without .jpg)
- url: https://www.instagram.com/p/[SHORTCODE]/
- theme: One theme from this list (choose exactly one):
  [Health/Nutrition; Fitness/Exercise; Mental Health; Beauty/Self-care; Lifestyle; Medical/Healthcare; Family/Parenting; Weight Loss; Other]
- theme_confidence: How confident you are (high/medium/low)
- image_type: photo / reel_thumbnail / carousel / other
- main_subject: What/who is the focus (person/product/text/scene)
- has_text_overlay: yes/no
- visual_quality: good/medium/poor
- mood: positive/negative/neutral/aspirational/informational
- engagement_potential: high/medium/low (how likely to get likes/comments)

## Important Rules
1. Analyze EVERY image in the folder
2. Use EXACT theme names from the list above
3. Be consistent in your classifications
4. Link analysis to the Instagram post using the shortcode

## Your Response
Output a COMPLETE CSV with all analyzed images. Include ALL images, not just samples.
"""


def main():
    parser = argparse.ArgumentParser(description="Generate Gemini app prompts for image analysis")
    parser.add_argument("--images", type=Path, default=Path("images"), help="Folder with downloaded images")
    parser.add_argument("--output", type=Path, default=Path("gemini_prompts.md"), help="Output file for prompts")
    parser.add_argument("--themes", type=str, default=None, help="Custom theme list (comma-separated)")
    
    args = parser.parse_args()
    
    if args.themes:
        theme_list = [t.strip() for t in args.themes.split(",")]
        theme_str = "; ".join(theme_list)
    else:
        theme_str = "Health/Nutrition; Fitness/Exercise; Mental Health; Beauty/Self-care; Lifestyle; Medical/Healthcare; Family/Parenting; Weight Loss; Other"
    
    prompt = GEMINI_ANALYSIS_PROMPT.replace(
        "[Health/Nutrition; Fitness/Exercise; Mental Health; Beauty/Self-care; Lifestyle; Medical/Healthcare; Family/Parenting; Weight Loss; Other]",
        theme_str
    )
    
    with args.output.open("w", encoding="utf-8") as f:
        f.write("# Gemini App Image Analysis Prompts\n\n")
        f.write("## Instructions for Students\n\n")
        f.write("1. Run the download script: `python download_images.py`\n")
        f.write("2. Open this file to get your Gemini prompt\n")
        f.write("3. Go to Gemini (gemini.google.com) and log in with your UGA email\n")
        f.write("4. Create a NEW chat for this analysis\n")
        f.write("5. Copy the prompt below and paste it into Gemini\n")
        f.write("6. Upload the images folder to Gemini\n")
        f.write("7. Copy the CSV output from Gemini\n")
        f.write("8. Save as `image_analysis.csv`\n\n")
        f.write("## Gemini Prompt (copy everything below this line)\n")
        f.write("---\n")
        f.write(prompt)
        f.write("\n---\n\n")
        f.write("## After Gemini Analysis\n\n")
        f.write("Run this to merge with your Excel data:\n")
        f.write("```\npython merge_results.py --analysis image_analysis.csv\n```\n")
    
    print(f"Created: {args.output}")
    print(f"\nNext steps:")
    print(f"1. python download_images.py --max 50  (download test batch)")
    print(f"2. Open {args.output}")
    print(f"3. Copy prompt to Gemini app")
    print(f"4. Upload images folder")


if __name__ == "__main__":
    main()
