"""
CLI helper to download images from a list of Instagram post URLs.

Uses instaloader (public/login) to fetch post media. It creates one folder per post
inside the output directory and stores all images (and cover frames for reels).

Usage:
  python scrape_instagram_images.py --urls urls.txt --output data/images
  python scrape_instagram_images.py --urls urls.txt --output data/images --username YOURUSER --password YOURPASS
  python scrape_instagram_images.py --urls urls.txt --output data/images --sessionid YOUR_SESSIONID

Notes:
- Provide a sessionid or login for higher reliability on rate-limited posts.
- URLs file: one post URL per line (supports /p/, /reel/, /tv/).
"""
import argparse
import os
import re
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
import instaloader


SHORTCODE_RE = re.compile(r"(?:instagram\\.com)?/(?:p|reel|tv)/([A-Za-z0-9_-]+)/?")


def extract_shortcode(url: str) -> str:
    match = SHORTCODE_RE.search(url)
    if not match:
        raise ValueError(f"Could not find shortcode in URL: {url}")
    return match.group(1)


def load_urls(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.lstrip().startswith("#")]


def init_loader(sessionid: str | None, username: str | None, password: str | None) -> instaloader.Instaloader:
    loader = instaloader.Instaloader(
        dirname_pattern="{target}",
        download_video_thumbnails=True,
        download_videos=False,
        save_metadata=False,
        post_metadata_txt_pattern="",
    )

    if sessionid:
        print(f"Using provided sessionid: {sessionid[:4]}***")
        
        # Logic from reference file (scrape_instagram_comments.py) to improve reliability
        sess = loader.context._session
        sess.cookies.set("sessionid", sessionid, domain="instagram.com")
        sess.cookies.set("ig_nrcb", "1", domain="instagram.com")
        sess.cookies.set("csrftoken", "missing", domain="instagram.com")
        sess.cookies.set("mid", "missing", domain="instagram.com")
        
        loader.context._session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
                )
            }
        )
        loader.context.username = username or "session"
        
        # Verify login
        try:
            if not loader.test_login():
                print("WARNING: Session ID might be invalid or expired.")
        except Exception as e:
            print(f"WARNING: Issue checking session: {e}")

    elif username and password:
        print(f"Attempting login as {username}...")
        try:
            loader.login(username, password)
            print("Login successful.")
        except instaloader.TwoFactorAuthRequiredException:
            print("ERROR: 2FA is required. Please use --sessionid instead.")
            sys.exit(1)
        except instaloader.ConnectionException as e:
            print(f"Login failed: {e}")
            sys.exit(1)
    else:
        print("WARNING: No credentials provided. Running anonymously. Expect rate limits and failures.")
    
    return loader


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="Download Instagram post images from URLs.")
    parser.add_argument("--urls", required=True, type=Path, help="Path to a text file with Instagram post URLs (one per line).")
    parser.add_argument("--output", type=Path, default=Path("login_images"), help="Directory to store downloaded images. Defaults to 'login_images'.")
    parser.add_argument("--username", type=str, default=os.getenv("INSTAGRAM_USERNAME"), help="Instagram username (optional, for login). defaults to env var INSTAGRAM_USERNAME")
    parser.add_argument("--password", type=str, default=os.getenv("INSTAGRAM_PASSWORD"), help="Instagram password (optional, for login). defaults to env var INSTAGRAM_PASSWORD")
    parser.add_argument("--sessionid", type=str, default=os.getenv("INSTAGRAM_SESSIONID"), help="Instagram sessionid cookie (optional alternative to username/password). defaults to env var INSTAGRAM_SESSIONID")
    args = parser.parse_args()

    urls_file = args.urls
    out_dir = args.output
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        urls = load_urls(urls_file)
    except FileNotFoundError:
        print(f"URLs file not found: {urls_file}")
        sys.exit(1)

    if not urls:
        print("No URLs found in the file. Exiting.")
        sys.exit(0)

    loader = init_loader(args.sessionid, args.username, args.password)

    print(f"Found {len(urls)} URLs. Downloading to {out_dir} ...")
    successes = 0
    failures = []

    for url in urls:
        try:
            shortcode = extract_shortcode(url)
            target_dir = out_dir / shortcode
            
            # Optimization: Skip if we already have images for this post
            # valid images usually end in .jpg or .webp
            if target_dir.exists() and any(f.suffix.lower() in ('.jpg', '.png', '.webp') for f in target_dir.iterdir()):
                print(f"[SKIP] {url} -> {target_dir} (Already downloaded)")
                continue

            post = instaloader.Post.from_shortcode(loader.context, shortcode)
            loader.download_post(post, target=str(target_dir))
            successes += 1
            print(f"[OK] {url} -> {target_dir}")
            # Be nice to Instagram to avoid 429/403
            time.sleep(5)
        except KeyboardInterrupt:
            print("\nAborted by user.")
            break
        except Exception as exc:  # noqa: BLE001
            failures.append((url, str(exc)))
            print(f"[FAIL] {url} | {exc}")
            # Sleep a bit longer on failure
            time.sleep(10)

    print(f"Done. Success: {successes}, Failures: {len(failures)}")
    if failures:
        print("Failures:")
        for url, err in failures:
            print(f"- {url}: {err}")


if __name__ == "__main__":
    main()
