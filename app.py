import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from io import BytesIO
from urllib.parse import urlparse
import os
import time
import concurrent.futures

# Title
st.title("🕷️ Bulk Web Content Scraper Tool")
st.markdown("Enter your XML sitemap URL to extract and scrape all web pages for clean, human-readable content.")

# Input sitemap URL with placeholder
DEFAULT_URL = "https://example.com/sitemap.xml"
sitemap_url = st.text_input("Enter Sitemap URL", value="", placeholder=DEFAULT_URL).strip() or DEFAULT_URL

# Button
if st.button("Scrape Sitemap"):
    try:
        with st.spinner("Fetching and parsing sitemap..."):
            res = requests.get(sitemap_url)
            if res.status_code != 200:
                st.error("Failed to fetch sitemap. Check the URL.")
                st.stop()
            soup = BeautifulSoup(res.content, 'xml')
            urls = [loc.text.strip() for loc in soup.find_all('loc')]

        st.success(f"Found {len(urls)} URLs. Starting scraping...")

        progress_bar = st.progress(0)
        status_text = st.empty()
        results = []

        def scrape_page(url):
            try:
                r = requests.get(url, timeout=30)
                r.encoding = r.apparent_encoding  # Ensure full character decoding
                s = BeautifulSoup(r.text, 'html.parser')
                for tag in s(['script', 'style', 'header', 'footer', 'nav']):
                    tag.decompose()
                content = []
                body = s.body or s  # fallback to entire doc if body is missing
                for element in body.descendants:
                    if element.name in ['h1', 'h2', 'h3']:
                        content.append(f"\n# {element.get_text(strip=True)}\n")
                    elif element.name == 'p':
                        text = element.get_text(" ", strip=True)
                        if text and len(text.split()) > 3:
                            content.append(text)
                    elif element.name in ['ul', 'ol']:
                        items = element.find_all('li')
                        for li in items:
                            li_text = li.get_text(" ", strip=True)
                            if li_text:
                                content.append(f"• {li_text}")
                return {"URL": url, "Content": "\n\n".join(content).strip()}
            except Exception as e:
                return {"URL": url, "Content": f"Error: {str(e)}"}

        # Concurrent scraping for performance boost
        total = len(urls)
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_url = {executor.submit(scrape_page, url): url for url in urls}
            for i, future in enumerate(concurrent.futures.as_completed(future_to_url)):
                status_text.text(f"Scraping {i+1}/{total}: {future_to_url[future]}")
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    results.append({"URL": future_to_url[future], "Content": f"Error: {str(e)}"})
                progress_bar.progress((i + 1) / total)

        df = pd.DataFrame(results)
        st.success("✅ Scraping complete!")

        # Save DataFrame to BytesIO buffer
        buffer = BytesIO()
        df.to_excel(buffer, index=False, engine='openpyxl')
        buffer.seek(0)

        # Extract filename from sitemap URL
        parsed_url = urlparse(sitemap_url)
        file_slug = os.path.basename(parsed_url.path) or "sitemap"
        filename = f"{file_slug.replace('.xml', '')}_scraped_output.xlsx"

        st.download_button(
            "📥 Download as Excel",
            data=buffer,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        for row in results:
            st.subheader(row['URL'])
            st.text_area("Content", row['Content'], height=300)

    except Exception as e:
        st.error(f"❌ Something went wrong: {e}")
