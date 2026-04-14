"""
Instagram Image Analysis Web App

A simple web interface for downloading Instagram images and generating Gemini prompts.

Run:
    streamlit run app.py
"""

import os
import re
import time
from pathlib import Path

import streamlit as st
import requests
from dotenv import load_dotenv

load_dotenv()


st.set_page_config(
    page_title="Instagram Image Analyzer",
    page_icon="📸",
    layout="wide"
)


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
}


def extract_shortcode(url: str) -> str | None:
    match = re.search(r'/(?:p|reel|tv)/([A-Za-z0-9_-]+)', url)
    return match.group(1) if match else None


def extract_shortcodes_from_text(text: str) -> list[str]:
    pattern = r'instagram\.com/(?:p|reel|tv)/([A-Za-z0-9_-]+)'
    return list(set(re.findall(pattern, text)))


def download_image(shortcode: str, output_dir: Path) -> dict:
    """
    Download Instagram image.
    
    Strategy:
    1. Try without session first (works ~90% of the time)
    2. If fails, retry with session ID if available
    """
    import instaloader
    
    output_path = output_dir / f"{shortcode}.jpg"
    
    if output_path.exists():
        return {"status": "skipped", "shortcode": shortcode, "message": "Already downloaded"}
    
    sessionid = os.getenv("INSTAGRAM_SESSIONID")
    
    def attempt_download(use_session: bool) -> dict:
        """Try to download with or without session."""
        loader = instaloader.Instaloader(
            dirname_pattern="{target}",
            download_video_thumbnails=False,
            download_videos=False,
            save_metadata=False,
            post_metadata_txt_pattern="",
        )
        
        if use_session and sessionid:
            try:
                sess = loader.context._session
                sess.cookies.set("sessionid", sessionid, domain="instagram.com")
                sess.cookies.set("ig_nrcb", "1", domain="instagram.com")
                sess.headers.update({
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"
                })
            except Exception:
                pass
        
        try:
            post = instaloader.Post.from_shortcode(loader.context, shortcode)
            
            img_url = post.url
            for node in post.get_sidecar_nodes():
                img_url = node.display_url
                break
            
            img_response = requests.get(img_url, headers=HEADERS, timeout=30, stream=True)
            img_response.raise_for_status()
            
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with output_path.open('wb') as f:
                for chunk in img_response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            method = "with session" if use_session else "without session"
            return {"status": "success", "shortcode": shortcode, "message": f"Downloaded ({method})"}
        
        except instaloader.exceptions.InstaloaderException as e:
            return {"status": "failed", "shortcode": shortcode, "message": str(e)[:80]}
        except Exception as e:
            return {"status": "failed", "shortcode": shortcode, "message": str(e)[:80]}
    
    # Try without session first
    result = attempt_download(use_session=False)
    
    # If failed and we have session, try with session
    if result["status"] == "failed" and sessionid:
        result = attempt_download(use_session=True)
    
    return result


st.set_page_config(page_title="Instagram Image Analyzer", page_icon="📸", layout="wide")

st.sidebar.title("📸 Instagram Image Analyzer")
st.sidebar.markdown("*Download & analyze Instagram images*")

page = st.sidebar.radio("Go to", [
    "🏠 About", 
    "🔑 Get Session ID",
    "📋 Extract URLs from Excel", 
    "📥 Download Images", 
    "📝 Generate Gemini Prompt",
    "🔗 Merge Results"
], label_visibility="collapsed")

if page == "🏠 About":
    st.header("About This Tool")
    
    st.markdown("""
    ### What Is This App For?
    
    This tool downloads Instagram images and prepares them for AI analysis.
    You can then use Gemini AI to analyze the images and merge results with your Excel data.
    
    ---
    
    ### The 4-Step Workflow
    
    **Step 1: Extract URLs**
    Upload your Excel file to extract Instagram post URLs
    
    **Step 2: Download Images**
    Download images from Instagram posts using the URLs
    
    **Step 3: Generate Gemini Prompt**
    Create instructions for Gemini AI to analyze your images
    
    **Step 4: Merge Results**
    Combine Gemini's analysis with your original Excel data
    
    ---
    
    ### Session ID (Optional)
    
    Downloads work ~90% without a session ID.
    If you get too many failures, get a session ID from the **🔑 Get Session ID** page.
    """)


elif page == "🔑 Get Session ID":
    st.header("🔑 Get Your Instagram Session ID")
    
    st.markdown("""
    ### What is this?
    
    This helps downloads work better. Without it, some images may fail.
    
    This is **optional** - downloads work 90% of the time without it.
    
    ---
    """)
    
    # Check if session already exists
    sessionid = os.getenv("INSTAGRAM_SESSIONID")
    if sessionid:
        st.success("Session ID already saved! You're all set.")
    else:
        if 'chrome_opened' not in st.session_state:
            st.session_state.chrome_opened = False
        
        if not st.session_state.chrome_opened:
            st.markdown("""
            ### Step 1: Open Chrome
            
            Click the button below to open Chrome with Instagram.
            """)
            
            if st.button("🌐 Open Instagram in Chrome", type="primary"):
                import subprocess
                import sys
                
                # Run a simpler script that just opens Chrome
                subprocess.Popen([sys.executable, "-c", 
                    "from selenium import webdriver; "
                    "from selenium.webdriver.chrome.options import Options; "
                    "from webdriver_manager.chrome import ChromeDriverManager; "
                    "from selenium.webdriver.chrome.service import Service; "
                    "options = Options(); "
                    "options.add_argument('--disable-blink-features=AutomationControlled'); "
                    "options.add_argument('--no-sandbox'); "
                    "driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options); "
                    "driver.get('https://www.instagram.com')"
                ])
                
                st.session_state.chrome_opened = True
                st.rerun()
        else:
            st.success("Chrome is open! Now log in to Instagram.")
            
            st.markdown("""
            ### Step 2: Log in to Instagram
            
            1. In the Chrome window that opened, log in to your Instagram account
            2. Wait for your feed to load
            3. Come back here and click the button below
            """)
            
            if st.button("✅ I'm logged in - Get Session ID", type="primary"):
                with st.spinner("Getting session ID..."):
                    import subprocess
                    import sys
                    import re
                    
                    # Run script to get session from existing Chrome
                    result = subprocess.run(
                        [sys.executable, "-c", 
                            "from selenium import webdriver; "
                            "from selenium.webdriver.chrome.options import Options; "
                            "from webdriver_manager.chrome import ChromeDriverManager; "
                            "from selenium.webdriver.chrome.service import Service; "
                            "options = Options(); "
                            "options.add_argument('--disable-blink-features=AutomationControlled'); "
                            "options.add_argument('--no-sandbox'); "
                            "driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options); "
                            "driver.get('https://www.instagram.com'); "
                            "import time; time.sleep(2); "
                            "cookies = driver.get_cookies(); "
                            "for c in cookies: "
                            "    if c['name'] == 'sessionid' and c['value']: "
                            "        print(c['value']); "
                            "        break; "
                            "driver.quit()"
                        ],
                        capture_output=True,
                        text=True
                    )
                    
                    session_id = result.stdout.strip()
                    
                    if session_id and len(session_id) > 10:
                        env_path = Path(".env")
                        existing = ""
                        if env_path.exists():
                            existing = env_path.read_text()
                        
                        if "INSTAGRAM_SESSIONID=" in existing:
                            existing = re.sub(r'INSTAGRAM_SESSIONID=.*', f'INSTAGRAM_SESSIONID={session_id}', existing)
                        else:
                            existing += f"\nINSTAGRAM_SESSIONID={session_id}\n"
                        
                        env_path.write_text(existing.strip() + "\n")
                        st.session_state.chrome_opened = False
                        st.success("Session ID saved! You can close Chrome now.")
                        st.balloons()
                    else:
                        st.error("Could not find session. Make sure you're logged in to Instagram.")
            
            if st.button("🔄 Start Over"):
                st.session_state.chrome_opened = False
                st.rerun()


elif page == "📥 Download Images":
    st.header("📥 Download Images")
    st.markdown("*Download images from Instagram URLs*")
    
    st.markdown("---")
    
    # Default URLs for quick testing
    default_urls = """https://www.instagram.com/p/C6b9MUXpO7_/
https://www.instagram.com/p/C6gPbEDO3_C/
https://www.instagram.com/reel/C20NPYHJssM/"""
    
    st.markdown("### Paste Instagram URLs (one per line)")
    
    url_input = st.text_area(
        "Instagram URLs",
        value=default_urls,
        height=200,
        label_visibility="collapsed"
    )
    
    with col1:
        max_downloads = st.number_input(
            "Max images to download", 
            min_value=1, 
            max_value=2000, 
            value=50, 
            step=10,
            help="How many images to download"
        )
    
    with col2:
        delay = st.number_input(
            "Delay (seconds)", 
            min_value=0.5, 
            max_value=10.0, 
            value=2.0,
            step=0.5,
            help="Recommended: 2 seconds. Min: 0.5 seconds. Higher = more reliable, lower = faster."
        )
    
    st.markdown("---")
    
    if st.button("🚀 Start Downloading", type="primary"):
        shortcodes = extract_shortcodes_from_text(url_input)
        
        if not shortcodes:
            st.error("No valid Instagram URLs found!")
        else:
            shortcodes = shortcodes[:max_downloads]
            
            st.info(f"📥 Starting download of {len(shortcodes)} images...")
            
            # Use temp directory for cloud deployment
            import tempfile
            import zipfile
            import os
            
            temp_dir = tempfile.mkdtemp()
            output_dir = Path(temp_dir)
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            results = {"success": 0, "error": 0}
            downloaded_files = []
            errors = []
            
            for i, shortcode in enumerate(shortcodes):
                progress_bar.progress((i + 1) / len(shortcodes))
                status_text.text(f"Downloading {i + 1}/{len(shortcodes)}: {shortcode}")
                
                result = download_image(shortcode, output_dir)
                
                if result["status"] == "success":
                    results["success"] += 1
                    downloaded_files.append(output_dir / f"{shortcode}.jpg")
                else:
                    results["error"] += 1
                    errors.append(f"{shortcode}: {result['message']}")
                
                time.sleep(delay)
            
            status_text.text("Done!")
            
            st.markdown("---")
            
            if results["success"] > 0:
                # Create zip file
                zip_path = Path(temp_dir) / "instagram_images.zip"
                
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for img_path in downloaded_files:
                        if img_path.exists():
                            zipf.write(img_path, img_path.name)
                
                # Read zip for download
                with open(zip_path, 'rb') as f:
                    zip_data = f.read()
                
                # Clean up individual images (keep zip for now)
                for img_path in downloaded_files:
                    if img_path.exists():
                        img_path.unlink()
                
                # Success message
                if results["error"] == 0:
                    st.success(f"### ✅ Downloaded {results['success']} images!")
                else:
                    st.warning(f"### ⚠️ Downloaded {results['success']} images ({results['error']} failed)")
                
                # Download button
                st.download_button(
                    label=f"📥 Download {results['success']} Images (ZIP)",
                    data=zip_data,
                    file_name="instagram_images.zip",
                    mime="application/zip",
                    type="primary"
                )
                
                st.info("💾 Save the ZIP file to your computer, then extract it!")
            else:
                st.error("❌ No images downloaded. Try getting a session ID.")
            
            # Show errors
            if errors and len(errors) <= 10:
                with st.expander("⚠️ Show errors"):
                    for err in errors:
                        st.text(err)
            
            # Clean up temp directory
            try:
                import shutil
                shutil.rmtree(temp_dir)
            except:
                pass
            
            if results['success'] > 0:
                st.markdown("""
                ---
                ### Next Step: 📝 Generate Gemini Prompt
                
                Upload the images folder to Gemini and create your prompt!
                """)


elif page == "📝 Generate Gemini Prompt":
    st.header("📝 Generate Gemini Prompt")
    st.markdown("*Create instructions for AI image analysis*")
    
    st.markdown("---")
    st.markdown("""
    ### How Gemini Analysis Works:
    
    1. Copy the generated prompt
    2. Go to [gemini.google.com](https://gemini.google.com)
    3. Upload your **downloaded_images** folder
    4. Paste the prompt
    5. Copy Gemini's CSV output
    6. Save as `image_analysis.csv`
    
    ---
    """)
    
    st.subheader("🎯 Customize Themes")
    
    theme_mode = st.radio("Theme selection", ["Use default themes (Health/Fitness/Beauty)", "Enter custom themes"])
    
    if theme_mode == "Use default themes (Health/Fitness/Beauty)":
        default_themes = """Health/Nutrition
Fitness/Exercise
Mental Health
Beauty/Self-care
Lifestyle
Medical/Healthcare
Family/Parenting
Weight Loss
Other"""
        themes = st.text_area("Themes (one per line)", value=default_themes, height=180)
    else:
        themes_input = st.text_input("Themes (comma-separated)", placeholder="Health, Fitness, Beauty, Lifestyle")
        themes = "\n".join([t.strip() for t in themes_input.split(",") if t.strip()])
        if not themes_input:
            themes = default_themes
    
    st.subheader("⚙️ Additional Options")
    
    col1, col2 = st.columns(2)
    with col1:
        include_caption_analysis = st.checkbox("Include text overlay analysis", value=True)
        include_engagement_predict = st.checkbox("Predict engagement potential", value=True)
    with col2:
        include_quality_score = st.checkbox("Rate visual quality", value=True)
        include_mood = st.checkbox("Identify mood/tone", value=True)
    
    st.markdown("---")
    
    if st.button("📋 Generate Prompt", type="primary"):
        theme_list = [t.strip() for t in themes.split("\n") if t.strip()]
        
        if not theme_list:
            st.error("Please enter at least one theme")
        else:
            theme_section = "; ".join(theme_list)
            
            prompt = f"""You are analyzing Instagram images for a social media research project.

## Your Task
Analyze ALL images in the folder you will upload and classify each one.

## Image Naming Convention
Images are named with their Instagram shortcode (e.g., ABC123xyz.jpg)
This shortcode links to the original post at: https://www.instagram.com/p/[SHORTCODE]/

## Required Output
Create a CSV with these columns:
- shortcode: The image filename (without .jpg)
- url: https://www.instagram.com/p/[SHORTCODE]/
- theme: One theme from this list (choose exactly one):
  [{theme_section}]
- theme_confidence: How confident you are (high/medium/low)
"""
            
            if include_caption_analysis:
                prompt += """- text_visible: yes/no (is there text overlay?)
- text_content: what text is visible (or empty)
"""
            
            prompt += "- image_type: photo / reel_thumbnail / carousel / other\n"
            
            if include_quality_score:
                prompt += "- visual_quality: good / medium / poor\n"
            
            if include_engagement_predict:
                prompt += "- engagement_potential: high / medium / low\n"
            
            if include_mood:
                prompt += "- mood: positive / negative / neutral / aspirational / informational\n"
            
            prompt += """- main_subject: what/who is the focus
- has_human: yes/no
- has_product: yes/no

## Important Rules
1. Analyze EVERY image in the folder (not just samples!)
2. Use EXACT theme names from the list above
3. Be consistent in your classifications
4. Output a COMPLETE CSV with ALL images

## Your Response
Return the complete CSV with ALL images analyzed."""

            st.subheader("📋 Your Gemini Prompt")
            st.code(prompt, language="markdown", height=400)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.download_button(
                    label="💾 Download Prompt (.md)",
                    data=prompt,
                    file_name="gemini_image_analysis_prompt.md",
                    mime="text/markdown"
                )
            
            with col2:
                st.session_state.prompt_ready = True
            
            st.markdown("""
            ---
            ### 🚀 How to Use:
            
            1. **Copy** the prompt above
            2. Go to **[gemini.google.com](https://gemini.google.com)**
            3. **Log in** with your UGA email (for Pro features)
            4. **Create a new chat**
            5. **Paste** the prompt
            6. **Upload** your `downloaded_images` folder
            7. **Wait** for Gemini to analyze
            8. **Copy** the CSV output from Gemini
            9. **Save** as `image_analysis.csv` in this folder
            
            Then go to **🔗 Merge Results** page!
            """)


elif page == "🔗 Merge Results":
    st.header("🔗 Merge Results")
    st.markdown("*Combine Gemini image analysis with your original Excel data*")
    
    st.markdown("---")
    st.markdown("""
    ### How Merging Works
    
    1. Your original Excel file has URLs in a column
    2. Gemini analysis has shortcodes and image classifications
    3. We match them by the Instagram post ID (shortcode)
    4. The result is a new Excel file with all data combined
    """)
    
    st.markdown("---")
    st.markdown("### Upload Your Files")
    
    col1, col2 = st.columns(2)
    
    with col1:
        excel_file = st.file_uploader(
            "📁 Original Excel file",
            type=["xlsx", "xls"],
            help="Your original Excel file with Instagram URLs"
        )
    
    with col2:
        analysis_file = st.file_uploader(
            "📁 Gemini Analysis CSV",
            type=["csv"],
            help="The CSV file you got from Gemini (save as image_analysis.csv)"
        )
    
    if excel_file and analysis_file:
        import pandas as pd
        import re
        
        st.markdown("---")
        st.markdown("### Configure Merge")
        
        header_row = st.number_input(
            "Header row in Excel (row with column names)",
            min_value=0,
            max_value=20,
            value=9,
            help="Usually row 10 (index 9) for Instagram data"
        )
        
        url_column = st.text_input(
            "URL column name",
            value="Url",
            help="The column name that contains Instagram URLs"
        )
        
        if st.button("🔄 Merge Data", type="primary"):
            with st.spinner("Loading files..."):
                try:
                    excel_df = pd.read_excel(excel_file, header=header_row)
                    analysis_df = pd.read_csv(analysis_file)
                    
                    st.success(f"Loaded: {len(excel_df)} Excel rows, {len(analysis_df)} analysis rows")
                    
                    # Extract shortcodes from URLs
                    def extract_shortcode(url):
                        if pd.isna(url):
                            return ""
                        match = re.search(r'/(?:p|reel|tv)/([A-Za-z0-9_-]+)', str(url))
                        return match.group(1) if match else ""
                    
                    excel_df['shortcode'] = excel_df[url_column].apply(extract_shortcode)
                    
                    # Check matches
                    excel_codes = set(excel_df['shortcode'])
                    analysis_codes = set(analysis_df['shortcode'])
                    matches = len(excel_codes & analysis_codes)
                    
                    st.info(f"Shortcodes in Excel: {len(excel_codes)}")
                    st.info(f"Shortcodes in Analysis: {len(analysis_codes)}")
                    st.info(f"Matching shortcodes: {matches}")
                    
                    if matches == 0:
                        st.error("No matches found! Check column names and CSV format.")
                    else:
                        # Merge
                        analysis_subset = analysis_df.copy()
                        analysis_subset.columns = ['shortcode'] + [f"image_{c}" for c in analysis_df.columns if c != 'shortcode']
                        
                        merged = excel_df.merge(analysis_subset, on='shortcode', how='left')
                        
                        # Download
                        csv = merged.to_csv(index=False)
                        st.success(f"✅ Merged! {len(merged)} total rows")
                        
                        st.download_button(
                            label="📥 Download Merged Excel (CSV)",
                            data=csv,
                            file_name="enriched_data.csv",
                            mime="text/csv"
                        )
                        
                        # Show preview
                        st.markdown("### Preview (first 5 rows)")
                        st.dataframe(merged.head(), use_container_width=True)
                        
                        # Show theme breakdown
                        if 'image_theme' in merged.columns:
                            st.markdown("### Theme Breakdown")
                            analyzed = merged[merged['image_theme'].notna()]
                            if len(analyzed) > 0:
                                theme_counts = analyzed['image_theme'].value_counts()
                                st.bar_chart(theme_counts)
                
                except Exception as e:
                    st.error(f"Error: {e}")
    
    if not excel_file or not analysis_file:
        st.info("👆 Upload both files above to merge")


elif page == "📋 Extract URLs from Excel":
    st.header("📋 Extract URLs from Excel")
    st.markdown("*Extract Instagram URLs from your Excel file*")
    
    st.markdown("---")
    st.markdown("""
    ### Upload your Excel file with Instagram URLs
    """)
    
    uploaded_file = st.file_uploader("📁 Upload Excel file (.xlsx)", type=["xlsx", "xls"], label_visibility="collapsed")
    
    if uploaded_file:
        import pandas as pd
        
        # Save to session state
        st.session_state.excel_file = uploaded_file
        
        try:
            # Preview the file
            df_preview = pd.read_excel(uploaded_file, header=None, nrows=10)
            st.write("📄 **Preview (first 10 rows):**")
            st.dataframe(df_preview.head(10), use_container_width=True)
            
            st.markdown("---")
            st.markdown("### Configure extraction")
            
            col1, col2 = st.columns(2)
            
            with col1:
                header_row = st.number_input(
                    "Header row (row number with column names)", 
                    min_value=0, 
                    max_value=20, 
                    value=9,
                    help="Usually row 10 (index 9) for Instagram data"
                )
            
            with col2:
                url_column = st.text_input(
                    "Column name with URLs",
                    value="Url",
                    help="Type the exact column name that contains Instagram URLs"
                )
            
            if st.button("🔍 Extract URLs", type="primary"):
                df = pd.read_excel(uploaded_file, header=header_row)
                
                # Show available columns
                st.write(f"**Available columns:** `{list(df.columns)}`")
                
                if url_column not in df.columns:
                    st.error(f"Column '{url_column}' not found!")
                    
                    # Try to find similar column names
                    similar = [c for c in df.columns if 'url' in str(c).lower() or 'link' in str(c).lower()]
                    if similar:
                        st.info(f"Did you mean: {similar}")
                else:
                    # Extract URLs
                    all_urls = []
                    for val in df[url_column].dropna():
                        found = re.findall(r'https?://(?:www\.)?instagram\.com/(?:p|reel|tv)/[A-Za-z0-9_-]+/?', str(val))
                        all_urls.extend(found)
                    
                    unique_urls = list(dict.fromkeys(all_urls))
                    
                    if unique_urls:
                        # Save to session state for next step
                        st.session_state.extracted_urls = unique_urls
                        
                        st.success(f"✅ Found **{len(unique_urls)}** unique Instagram URLs!")
                        
                        st.markdown("---")
                        st.markdown("### Extracted URLs")
                        
                        st.text_area(
                            "URLs (copy this if needed)", 
                            value="\n".join(unique_urls[:50]), 
                            height=200,
                            label_visibility="collapsed"
                        )
                        
                        if len(unique_urls) > 50:
                            st.info(f"Showing first 50 of {len(unique_urls)} URLs")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.download_button(
                                label="💾 Download URLs as txt",
                                data="\n".join(unique_urls),
                                file_name="urls.txt",
                                mime="text/plain"
                            )
                        
                        with col2:
                            st.session_state.urls_ready = True
                            st.info("🚀 Go to **Download Images** page to download these!")
                        
                        # Show preview of what you'll download
                        st.markdown("---")
                        st.markdown("### Sample URLs:")
                        for url in unique_urls[:5]:
                            st.markdown(f"- {url}")
                    else:
                        st.warning("No Instagram URLs found in that column. Check the column name and try again.")
                        
        except Exception as e:
            st.error(f"Error reading file: {e}")
            import traceback
            st.code(traceback.format_exc())


st.sidebar.markdown("---")
st.sidebar.markdown("""
### Quick Links
- [Gemini Google](https://gemini.google.com)
- [Get Session ID](https://help.instagram.com/158891534410507496)

### Need Help?
Make sure your `.env` file contains:
```
INSTAGRAM_SESSIONID=your_session_id
```
""")
