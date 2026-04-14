"""
Instagram Image Downloader - Simple version for non-technical students.

Downloads images from Instagram URLs using requests with browser headers.
No login or API key needed!

Usage:
    python download_images.py --urls urls.txt --output images

Requirements:
    pip install requests
"""

import argparse
import random
import re
import sys
import time
from pathlib import Path

import requests


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
}


def extract_shortcode(url: str) -> str:
    match = re.search(r'/(?:p|reel|tv)/([A-Za-z0-9_-]+)', url)
    if not match:
        raise ValueError(f"Could not extract shortcode from: {url}")
    return match.group(1)


def load_urls(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.lstrip().startswith("#")]


def download_image(shortcode: str, output_dir: Path) -> tuple[bool, str]:
    output_path = output_dir / f"{shortcode}.jpg"
    
    if output_path.exists():
        return True, "Already downloaded"
    
    post_url = f"https://www.instagram.com/p/{shortcode}/"
    
    try:
        response = requests.get(post_url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        content = response.text
        
        og_match = re.search(r'<meta property="og:image" content="([^"]+)"', content)
        
        if og_match:
            img_url = og_match.group(1)
        else:
            json_match = re.search(r'"display_url"\s*:\s*"([^"]+)"', content)
            if json_match:
                img_url = json_match.group(1)
            else:
                return False, "Could not find image URL"
        
        img_response = requests.get(img_url, headers=HEADERS, timeout=30, stream=True)
        img_response.raise_for_status()
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open('wb') as f:
            for chunk in img_response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return True, "Downloaded"
    
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            return False, "Access denied (may be private)"
        elif e.response.status_code == 404:
            return False, "Post not found"
        return False, f"HTTP error: {e.response.status_code}"
    except Exception as e:
        return False, str(e)


def main():
    parser = argparse.ArgumentParser(description="Download Instagram images (no login needed)")
    parser.add_argument("--urls", type=Path, default=Path("urls.txt"), help="File with Instagram URLs")
    parser.add_argument("--output", type=Path, default=Path("images"), help="Output folder")
    parser.add_argument("--max", type=int, default=None, help="Max posts to download")
    parser.add_argument("--delay", type=float, default=2.0, help="Delay between posts (seconds)")
    
    args = parser.parse_args()
    
    if not args.urls.exists():
        print(f"Error: File not found: {args.urls}")
        print("Create a urls.txt file with one Instagram URL per line")
        sys.exit(1)
    
    urls = load_urls(args.urls)
    if args.max:
        urls = urls[:args.max]
    
    print(f"Found {len(urls)} URLs")
    print(f"Output folder: {args.output}")
    print()
    
    successes = 0
    failures = []
    
    for idx, url in enumerate(urls, 1):
        shortcode = extract_shortcode(url)
        
        print(f"[{idx}/{len(urls)}] Downloading: {shortcode}")
        
        success, message = download_image(shortcode, args.output)
        
        if success:
            print(f"  -> {message}")
            successes += 1
        else:
            print(f"  -> FAILED: {message}")
            failures.append((url, message))
        
        time.sleep(random.uniform(args.delay * 0.7, args.delay * 1.3))
    
    print()
    print("=" * 50)
    print(f"DONE: {successes}/{len(urls)} downloaded")
    
    if failures:
        print(f"Failed: {len(failures)}")
        for url, err in failures[:5]:
            print(f"  - {url[:50]}...")
            print(f"    {err}")
        if len(failures) > 5:
            print(f"  ... and {len(failures) - 5} more")


if __name__ == "__main__":
    main()
