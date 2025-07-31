import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from io import BytesIO

# Title
st.title("🕷️ Sitemap Web Scraper Tool")
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

        @st.cache_data(show_spinner=False)
        def scrape_page(url):
            try:
                r = requests.get(url, timeout=10)
                s = BeautifulSoup(r.text, 'html.parser')
                for tag in s(['script', 'style', 'header', 'footer', 'nav']):
                    tag.decompose()
                content = []
                for tag in s.find_all(['h1', 'h2', 'h3', 'p', 'ul', 'ol']):
                    if tag.name in ['h1', 'h2', 'h3']:
                        content.append(f"\n# {tag.get_text(strip=True)}\n")
                    elif tag.name == 'p':
                        text = tag.get_text(strip=True)
                        if text and len(text.split()) > 3:
                            content.append(text)
                    elif tag.name in ['ul', 'ol']:
                        items = tag.find_all('li')
                        for li in items:
                            li_text = li.get_text(" ", strip=True)
                            if li_text:
                                content.append(f"• {li_text}")
                return "\n\n".join(content).strip()
            except Exception as e:
                return f"Error: {str(e)}"

        results = []
        for url in urls[:20]:  # Limit to 20 for demo
            st.write(f"🔎 Scraping: {url}")
            content = scrape_page(url)
            results.append({"URL": url, "Content": content})

        df = pd.DataFrame(results)
        st.success("✅ Scraping complete!")

        # Save DataFrame to BytesIO buffer
        buffer = BytesIO()
        df.to_excel(buffer, index=False, engine='openpyxl')
        buffer.seek(0)

        st.download_button(
            "📥 Download as Excel",
            data=buffer,
            file_name="sitemap_scraped_output.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        for row in results:
            st.subheader(row['URL'])
            st.write(row['Content'][:1500] + ("..." if len(row['Content']) > 1500 else ""))

    except Exception as e:
        st.error(f"❌ Something went wrong: {e}")
