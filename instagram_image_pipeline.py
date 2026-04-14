"""
Integrated Instagram Image Downloader & Analyzer with Gemini

Workflow:
1. Extract image URLs from Instagram post URLs
2. Download images organized by shortcode
3. Analyze images using Google Gemini API
4. Output CSV with analysis linked by shortcode for merging with Excel

Usage:
    python instagram_image_pipeline.py --urls urls.txt --output-dir data --excel your_data.xlsx --api-key YOUR_GEMINI_KEY
    
Environment variables:
    GEMINI_API_KEY - Your Google AI API key
"""

import argparse
import base64
import json
import os
import random
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()


INSTAGRAM_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def extract_shortcode(url: str) -> str:
    match = re.search(r'/(?:p|reel|tv)/([A-Za-z0-9_-]+)', url)
    if not match:
        raise ValueError(f"Could not extract shortcode from URL: {url}")
    return match.group(1)


def fetch_image_url(post_url: str, session: requests.Session) -> str | None:
    """Fetch the main image URL from an Instagram post page."""
    try:
        response = session.get(post_url, headers=INSTAGRAM_HEADERS, timeout=15)
        response.raise_for_status()
        content = response.text
        
        og_image_match = re.search(r'<meta property="og:image" content="([^"]+)"', content)
        if og_image_match:
            return og_image_match.group(1)
        
        sidecar_match = re.search(r'"items":\s*\[(.*?)\]', content, re.DOTALL)
        if sidecar_match:
            items_text = sidecar_match.group(1)
            image_match = re.search(r'"display_url":\s*"([^"]+)"', items_text)
            if image_match:
                return image_match.group(1)
        
        return None
    except Exception as e:
        print(f"Error fetching {post_url}: {e}")
        return None


def download_image(image_url: str, output_path: Path, session: requests.Session) -> bool:
    """Download an image from URL to the specified path."""
    try:
        response = session.get(image_url, headers=INSTAGRAM_HEADERS, timeout=30, stream=True)
        response.raise_for_status()
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with output_path.open('wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"Error downloading {image_url}: {e}")
        return False


def load_excel_with_lock(excel_path: Path) -> pd.DataFrame:
    """Load Excel file, handling lock issues."""
    try:
        return pd.read_excel(excel_path, header=9)
    except PermissionError:
        print("File is locked. Copying to temporary file...")
        import shutil
        temp_path = Path("temp_pipeline.xlsx")
        shutil.copyfile(excel_path, temp_path)
        df = pd.read_excel(temp_path, header=9)
        temp_path.unlink(missing_ok=True)
        return df


def extract_shortcodes_from_excel(df: pd.DataFrame) -> set:
    """Extract shortcodes from URL column in Excel."""
    if 'Url' not in df.columns:
        raise ValueError("Excel must have 'Url' column")
    
    shortcodes = set()
    for url in df['Url'].dropna():
        try:
            shortcodes.add(extract_shortcode(str(url)))
        except ValueError:
            continue
    return shortcodes


def analyze_image_with_gemini(image_path: Path, api_key: str, model: str = "gemini-1.5-flash") -> dict:
    """Analyze a single image using Gemini API."""
    import mimetypes
    
    mime, _ = mimetypes.guess_type(image_path.name)
    if mime is None:
        mime = "image/jpeg"
    
    with image_path.open("rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    
    prompt = """Analyze this Instagram image and provide a structured analysis.
    
Return a JSON object with these fields ONLY (no markdown, no explanation, just the JSON):
{
    "image_type": "photo" or "reel_thumbnail" or "carousel" or "video_frame",
    "main_subject": "what/who is the primary subject (person, product, text, etc.)",
    "setting": "where is this taking place (indoor, outdoor, studio, etc.)",
    "visual_theme": "overall aesthetic (minimal, vibrant, professional, lifestyle, etc.)",
    "has_text_overlay": true or false,
    "text_content": "any text visible in the image, or empty string",
    "brand_visibility": "none" or "low" or "medium" or "high",
    "brands_mentioned": ["list of brand names if visible, else empty array"],
    "colors": ["dominant colors in the image"],
    "mood": "emotional tone (positive, negative, neutral, aspirational, informational, etc.)",
    "contains_human": true or false,
    "human_activity": "what activity are humans doing, or empty string",
    "contains_product": true or false,
    "product_category": "general product category if visible, or empty string",
    "quality_score": 1-5 rating of image quality/production value,
    "notes": "any other notable observations"
}

Be concise and accurate. Only return valid JSON."""

    payload = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": mime, "data": image_data}}
            ]
        }],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 800
        }
    }
    
    for attempt in range(3):
        try:
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
            
            if 'candidates' in result and len(result['candidates']) > 0:
                text = result['candidates'][0]['content']['parts'][0]['text']
                text = text.strip()
                if text.startswith('```json'):
                    text = text[7:]
                if text.startswith('```'):
                    text = text[3:]
                if text.endswith('```'):
                    text = text[:-3]
                return json.loads(text.strip())
            return {"error": "No response from Gemini"}
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            return {"error": f"Failed to parse response: {text[:100] if 'text' in dir() else 'N/A'}"}
        except Exception as e:
            if attempt == 2:
                return {"error": str(e)}
            time.sleep(2 ** attempt)


def create_analysis_prompt(theme_categories: list[str] = None) -> str:
    """Create a custom analysis prompt for specific themes."""
    base_prompt = """Analyze this Instagram image for social media content classification.

Return ONLY valid JSON with these fields:
{
    "theme": "one of the categories that best matches this image",
    "theme_confidence": 0.0-1.0,
    "content_type": "promotional" or "informational" or "personal" or "news" or "entertainment",
    "target_audience": "who this content seems to appeal to",
    "persuasion_techniques": ["list of techniques used if any, else empty"],
    "visual_appeal_score": 1-5,
    "engagement_potential": "high" or "medium" or "low" estimate
}"""

    if theme_categories:
        base_prompt = base_prompt.replace(
            '"one of the categories that best matches this image"',
            f'"one of these EXACT categories: {theme_categories}"'
        )
    
    return base_prompt


def load_urls(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.lstrip().startswith("#")]


def main():
    parser = argparse.ArgumentParser(description="Instagram image download and analysis pipeline with Gemini")
    
    parser.add_argument("--urls", type=Path, default=Path("urls.txt"), help="Path to URLs file")
    parser.add_argument("--output-dir", type=Path, default=Path("instagram_images"), help="Output directory for images")
    parser.add_argument("--excel", type=Path, default=Path("Health_and_Influencers_Jan_24-June_25.xlsx"), help="Excel file to match against")
    parser.add_argument("--api-key", type=str, default=os.getenv("GEMINI_API_KEY"), help="Gemini API key")
    parser.add_argument("--model", type=str, default="gemini-1.5-flash", help="Gemini model")
    parser.add_argument("--max-download", type=int, default=None, help="Max posts to download")
    parser.add_argument("--max-analyze", type=int, default=None, help="Max images to analyze")
    parser.add_argument("--analyze-only", action="store_true", help="Skip download, only analyze existing images")
    parser.add_argument("--output-csv", type=Path, default=Path("image_analysis_results.csv"), help="Output CSV path")
    parser.add_argument("--delay", type=float, default=2.0, help="Delay between requests (seconds)")
    
    args = parser.parse_args()
    
    if not args.analyze_only and not args.urls.exists():
        print(f"URLs file not found: {args.urls}")
        sys.exit(1)
    
    api_key = args.api_key
    if not api_key:
        print("Error: GEMINI_API_KEY is required. Set environment variable or use --api-key")
        sys.exit(1)
    
    excel_shortcodes = set()
    if args.excel.exists():
        print(f"Loading Excel file: {args.excel}")
        df = load_excel_with_lock(args.excel)
        excel_shortcodes = extract_shortcodes_from_excel(df)
        print(f"Found {len(excel_shortcodes)} shortcodes in Excel")
    
    session = requests.Session()
    
    if not args.analyze_only:
        urls = load_urls(args.urls)
        if args.max_download:
            urls = urls[:args.max_download]
        
        print(f"\n=== PHASE 1: Downloading {len(urls)} images ===")
        
        download_results = []
        
        for idx, url in enumerate(urls, 1):
            shortcode = extract_shortcode(url)
            image_path = args.output_dir / f"{shortcode}.jpg"
            
            if image_path.exists():
                print(f"[{idx}/{len(urls)}] SKIP (exists): {shortcode}")
                download_results.append({"shortcode": shortcode, "url": url, "status": "skipped", "image_path": str(image_path)})
                continue
            
            print(f"[{idx}/{len(urls)}] Fetching: {shortcode}")
            image_url = fetch_image_url(url, session)
            
            if image_url:
                if download_image(image_url, image_path, session):
                    print(f"  -> Downloaded: {image_path.name}")
                    download_results.append({"shortcode": shortcode, "url": url, "status": "success", "image_path": str(image_path)})
                else:
                    download_results.append({"shortcode": shortcode, "url": url, "status": "failed", "image_path": ""})
            else:
                print(f"  -> Failed to get image URL")
                download_results.append({"shortcode": shortcode, "url": url, "status": "failed", "image_path": ""})
            
            time.sleep(random.uniform(args.delay * 0.5, args.delay * 1.5))
        
        download_df = pd.DataFrame(download_results)
        download_csv = args.output_dir / "download_log.csv"
        download_df.to_csv(download_csv, index=False)
        print(f"\nDownload log saved to: {download_csv}")
    
    print(f"\n=== PHASE 2: Analyzing images with Gemini ===")
    
    image_files = list(args.output_dir.glob("*.jpg")) + list(args.output_dir.glob("*.png")) + list(args.output_dir.glob("*.webp"))
    image_files = [f for f in image_files if not f.name.endswith("_thumb.jpg")]
    
    if args.max_analyze:
        image_files = image_files[:args.max_analyze]
    
    print(f"Found {len(image_files)} images to analyze")
    
    analysis_results = []
    
    for idx, image_path in enumerate(image_files, 1):
        shortcode = image_path.stem
        
        print(f"[{idx}/{len(image_files)}] Analyzing: {shortcode}")
        
        result = analyze_image_with_gemini(image_path, api_key, args.model)
        result["shortcode"] = shortcode
        result["image_path"] = str(image_path)
        result["instagram_url"] = f"https://www.instagram.com/p/{shortcode}/"
        
        if excel_shortcodes and shortcode in excel_shortcodes:
            result["in_excel"] = True
        else:
            result["in_excel"] = False
        
        analysis_results.append(result)
        
        print(f"  -> Theme: {result.get('theme', result.get('main_subject', 'N/A'))}")
        
        time.sleep(random.uniform(0.5, 1.5))
    
    analysis_df = pd.DataFrame(analysis_results)
    analysis_df.to_csv(args.output_csv, index=False)
    print(f"\n=== COMPLETE ===")
    print(f"Analysis results saved to: {args.output_csv}")
    print(f"Total images analyzed: {len(analysis_results)}")
    
    print(f"\nTo merge with your Excel data:")
    print(f"1. Load your Excel file and the analysis CSV")
    print(f"2. Add a column 'shortcode' by extracting from 'Url' column")
    print(f"3. VLOOKUP or merge on 'shortcode' column")


if __name__ == "__main__":
    main()
