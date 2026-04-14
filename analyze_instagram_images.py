"""
Vision-driven analyzer to infer what products/categories are being promoted in Instagram images.

Flow:
- Read images from a directory (recurses by default).
- Optional captions file (CSV with columns: image, caption OR JSON mapping filename->caption).
- Send each image to an OpenAI vision model with a structured prompt (no fixed catalog; optional Google Product Taxonomy mapping).
- Emit a CSV with industry, product category, detected products/brands, confidences, and optional taxonomy matches.

Example:
  python analyze_instagram_images.py --images data/images --output results.csv --captions captions.csv --model gpt-4o-mini
"""
import argparse
import base64
import difflib
import json
import mimetypes
import os
import random
import sys
import time
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI, RateLimitError, APIConnectionError

load_dotenv()

SYSTEM_PROMPT = (
    "You are an expert visual analyst for influencer marketing. "
    "Identify products that appear to be promoted. "
    "Do not rely on any fixed product catalog; infer from the visual evidence and optional caption. "
    "If multiple products appear, list them separately."
)


def encode_image_to_data_url(path: Path) -> str:
    mime, _ = mimetypes.guess_type(path.name)
    if mime is None:
        mime = "image/jpeg"
    with path.open("rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime};base64,{b64}"


def load_captions(path: Path | None) -> dict[str, str]:
    if path is None:
        return {}
    if not path.exists():
        raise FileNotFoundError(f"Captions file not found: {path}")

    if path.suffix.lower() == ".json":
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items()}
        raise ValueError("JSON captions file must be an object mapping filename -> caption.")

    # CSV fallback
    df = pd.read_csv(path)
    if "image" not in df.columns or "caption" not in df.columns:
        raise ValueError("CSV captions file must contain 'image' and 'caption' columns.")
    return {str(row["image"]): str(row["caption"]) for _, row in df.iterrows()}


def build_user_content(image_data_url: str, caption: str | None) -> list[dict]:
    caption_text = caption.strip() if caption else ""
    caption_block = caption_text if caption_text else "No caption provided."
    instructions = (
        "Look at the image and, using only what you see plus the optional caption, "
        "infer what is being promoted. Output JSON only. "
        "Use free-text labels (no fixed catalog). If you can, also map the product/category to a Google Product Taxonomy path; "
        "otherwise leave it empty.\n"
        "JSON schema:\n"
        "{\n"
        '  "industry": "<free-text industry>",\n'
        '  "product_category": "<concise free-text category>",\n'
        '  "google_product_taxonomy_path": "<best GPT path or empty if unknown>",\n'
        '  "products": [\n'
        '    {\n'
        '      "name_or_description": "<what the product is>",\n'
        '      "brand_or_logo": "<brand if visible, else empty>",\n'
        '      "promotion_likelihood": 0-1,\n'
        '      "confidence": 0-1,\n'
        '      "evidence": "<brief visual/text evidence>",\n'
        '      "google_product_taxonomy_path": "<best GPT path or empty if unknown>"\n'
        "    }\n"
        "  ],\n"
        '  "promotion_overall": 0-1,\n'
        '  "notes": "<optional short notes>"\n'
        "}\n"
        "Use 'Other' only when nothing else is clear."
    )
    return [
        {"type": "text", "text": instructions + f"\n\nCaption: {caption_block}"},
        {"type": "image_url", "image_url": {"url": image_data_url}},
    ]


def parse_response(raw: str) -> dict:
    try:
        # Strip potential markdown blocks
        cleaned = raw.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned.removeprefix("```json").removesuffix("```").strip()
        elif cleaned.startswith("```"):
            cleaned = cleaned.removeprefix("```").removesuffix("```").strip()
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {"parse_error": "Could not parse JSON", "raw": raw}


def analyze_image(
    client: OpenAI,
    model: str,
    image_path: Path,
    caption: str | None,
    temperature: float,
) -> dict:
    data_url = encode_image_to_data_url(image_path)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_content(data_url, caption)},
    ]

    max_retries = 3
    base_delay = 2

    for attempt in range(max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=600,
            )
            break
        except (RateLimitError, APIConnectionError) as e:
            if attempt == max_retries:
                raise  # Re-raise final exception
            
            # Exponential backoff with jitter
            sleep_time = (base_delay * (2 ** attempt)) + random.uniform(0, 1)
            print(f"Rate limit or connection error ({e}). Retrying in {sleep_time:.2f}s...")
            time.sleep(sleep_time)
            
    raw = response.choices[0].message.content.strip()
    parsed = parse_response(raw)
    result = {
        "image_path": str(image_path),
        "caption": caption or "",
        "raw_response": raw,
    }
    if isinstance(parsed, dict):
        result.update(parsed)
    else:
        result["parse_error"] = "Unexpected response type"
    return result


def load_taxonomy(path: Path | None) -> list[str]:
    """Load Google Product Taxonomy TSV (id <tab> path) or plain text (one path per line)."""
    if path is None:
        return []
    if not path.exists():
        raise FileNotFoundError(f"Taxonomy file not found: {path}")

    paths: list[str] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue
            if "\t" in stripped:
                _, path_str = stripped.split("\t", 1)
                paths.append(path_str.strip())
            else:
                paths.append(stripped)
    return paths


def best_taxonomy_match(label: str, taxonomy_paths: list[str], cutoff: float = 0.45) -> str:
    """Return the closest taxonomy path using difflib; empty string if no good match."""
    if not label or not taxonomy_paths:
        return ""
    match = difflib.get_close_matches(label, taxonomy_paths, n=1, cutoff=cutoff)
    return match[0] if match else ""


def apply_taxonomy(record: dict, taxonomy_paths: list[str]) -> dict:
    """Add local taxonomy matches when GPT did not return one."""
    if not taxonomy_paths:
        return record

    if not record.get("google_product_taxonomy_path"):
        record["google_product_taxonomy_path"] = best_taxonomy_match(record.get("product_category", ""), taxonomy_paths)

    products = record.get("products")
    if isinstance(products, list):
        updated_products = []
        for prod in products:
            if not isinstance(prod, dict):
                updated_products.append(prod)
                continue
            if not prod.get("google_product_taxonomy_path"):
                candidate = prod.get("name_or_description") or prod.get("brand_or_logo", "")
                prod["google_product_taxonomy_path"] = best_taxonomy_match(candidate, taxonomy_paths)
            updated_products.append(prod)
        record["products"] = updated_products

    return record


def find_images(images_dir: Path, recursive: bool) -> list[Path]:
    patterns = ("*.jpg", "*.jpeg", "*.png", "*.webp")
    paths: list[Path] = []
    if recursive:
        for pattern in patterns:
            paths.extend(images_dir.rglob(pattern))
    else:
        for pattern in patterns:
            paths.extend(images_dir.glob(pattern))
    return sorted({p.resolve() for p in paths})


def main():
    parser = argparse.ArgumentParser(description="Analyze Instagram images with an OpenAI vision model.")
    parser.add_argument("--images", required=True, type=Path, help="Directory containing images (post-download).")
    parser.add_argument("--output", required=True, type=Path, help="Path to output CSV.")
    parser.add_argument("--captions", type=Path, default=None, help="Optional captions file: CSV (image,caption) or JSON mapping filename->caption.")
    parser.add_argument("--taxonomy", type=Path, default=None, help="Optional Google Product Taxonomy file (TSV: id<TAB>path, or one path per line).")
    parser.add_argument("--model", type=str, default="gpt-4o-mini", help="OpenAI vision-capable model.")
    parser.add_argument("--temperature", type=float, default=0.0, help="Sampling temperature.")
    parser.add_argument("--max-images", type=int, default=None, help="Optional cap on number of images to process.")
    parser.add_argument("--delay", type=float, default=1.0, help="Seconds to sleep between requests (default 1.0).")
    parser.add_argument("--no-recursive", action="store_true", help="Only look at top-level of the images directory.")
    args = parser.parse_args()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY is not set in the environment.")
        sys.exit(1)

    client = OpenAI(api_key=api_key)

    try:
        captions_map = load_captions(args.captions)
    except Exception as exc:  # noqa: BLE001
        print(f"Failed to load captions: {exc}")
        sys.exit(1)

    try:
        taxonomy_paths = load_taxonomy(args.taxonomy)
    except Exception as exc:  # noqa: BLE001
        print(f"Failed to load taxonomy: {exc}")
        sys.exit(1)

    images = find_images(args.images, recursive=not args.no_recursive)
    if args.max_images:
        images = images[: args.max_images]

    if not images:
        print("No images found. Check the --images path and extensions.")
        sys.exit(0)

    print(f"Processing {len(images)} images with model {args.model} ...")
    records = []
    for idx, image_path in enumerate(images, 1):
        if idx > 1 and args.delay > 0:
            time.sleep(args.delay)
            
        caption = captions_map.get(image_path.name) or captions_map.get(str(image_path)) or ""
        try:
            result = analyze_image(client, args.model, image_path, caption, args.temperature)
            result = apply_taxonomy(result, taxonomy_paths)
            records.append(result)
            print(f"[{idx}/{len(images)}] OK - {image_path.name}")
        except Exception as exc:  # noqa: BLE001
            print(f"[{idx}/{len(images)}] FAIL - {image_path.name}: {exc}")
            records.append(
                {
                    "image_path": str(image_path),
                    "caption": caption,
                    "error": str(exc),
                }
            )

    df = pd.DataFrame(records)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.output, index=False)
    print(f"Saved results to {args.output}")


if __name__ == "__main__":
    main()
