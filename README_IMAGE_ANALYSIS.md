# Instagram Image Analysis Workflow

A web-based tool for downloading Instagram images and preparing them for AI analysis.

## Quick Start

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open [http://localhost:8501](http://localhost:8501) in your browser.

---

## Setup (One-time)

### 1. Install Python Packages
```bash
pip install -r requirements.txt
```

### 2. Get Instagram Session ID
1. Log into Instagram in your browser
2. Open Developer Tools (F12) > Application tab > Cookies
3. Find `sessionid` cookie and copy its value
4. Create a `.env` file with:
```
INSTAGRAM_SESSIONID=your_session_id_here
```

---

## Web App Pages

### 🏠 About
Explains the workflow and what this tool does.

### 📥 Download Images
- Paste Instagram URLs (any format - works with mixed text too!)
- Download images to your computer
- Images are saved with their post ID as filename

### 📝 Generate Gemini Prompt
- Customize theme categories
- Generate a ready-to-use prompt for Gemini
- Download or copy the prompt

### 🔗 URL Extractor
- Extract URLs from pasted text
- Extract URLs from Excel files
- Download as txt file

---

## Command Line (Alternative)

For technical users who prefer command line:

### Download Images
```bash
python download_images.py --urls urls.txt --output images --max 50
```

### Generate Prompts
```bash
python generate_prompts.py --themes "Health,Fitness,Beauty"
```

### Merge Results
```bash
python merge_results.py --analysis image_analysis.csv
```

---

## File Structure
```
folder/
├── .env                  # Your Instagram session ID
├── app.py                # Web app (run with streamlit)
├── urls.txt              # Instagram post URLs
├── downloaded_images/    # Downloaded images
│   ├── DAgykYOyWJ_.jpg
│   └── ...
├── image_analysis.csv     # Gemini output (YOU create this)
├── enriched_data.xlsx    # Final merged file
└── requirements.txt
```

---

## Troubleshooting

**"No matches found" when merging:**
- Check that your analysis CSV has a `shortcode` column
- Shortcode = Instagram post ID (e.g., "DAgykYOyWJ_")

**Download failures:**
- Your session ID may have expired - get a new one
- Some posts may be private or deleted

**Gemini not analyzing all images:**
- Upload in smaller batches (25-30)
- Use Gemini Pro model
