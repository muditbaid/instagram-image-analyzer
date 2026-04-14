
import pandas as pd
from pathlib import Path

def main():
    excel_path = "Health_and_Influencers_Jan_24-June_25.xlsx"
    header_row = 9  # 0-indexed, so row 10 in Excel is index 9
    
    print(f"Reading {excel_path}...")
    try:
        df = pd.read_excel(excel_path, header=header_row)
    except PermissionError:
        # Fallback for when the file is open: copy to temp
        print("File is locked. Copying to temporary file...")
        import shutil
        temp_path = "temp_extract_urls.xlsx"
        shutil.copyfile(excel_path, temp_path)
        df = pd.read_excel(temp_path, header=header_row)
        Path(temp_path).unlink(missing_ok=True)

    if 'Url' not in df.columns:
        print("Error: 'Url' column not found.")
        print("Available columns:", df.columns.tolist())
        return

    # Extract, clean, and deduplicate
    urls = df['Url'].dropna().astype(str).str.strip().unique()
    
    # Filter for likely valid URLs (basic check)
    valid_urls = [u for u in urls if "instagram.com" in u]

    output_path = "urls.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        for url in valid_urls:
            f.write(url + "\n")

    print(f"Success! Extracted {len(valid_urls)} URLs to {output_path}")

if __name__ == "__main__":
    main()
