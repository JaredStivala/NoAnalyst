import streamlit as st
import requests
from tavily import TavilyClient
import os
from dotenv import load_dotenv
import matplotlib.pyplot as plt
import re
import time

# Load environment variables
load_dotenv()
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not TAVILY_API_KEY or not DEEPSEEK_API_KEY:
    st.error("Please set both TAVILY_API_KEY and DEEPSEEK_API_KEY in your .env file.")
    st.stop()

# Tavily setup
tavily = TavilyClient(api_key=TAVILY_API_KEY)

st.set_page_config(page_title="NoAnalyst", layout="centered")
st.markdown(
    """
<style>
body {
    background-color: #0b1120;
    color: #e0e6ed;
    font-family: 'Segoe UI', sans-serif;
}
.stButton>button {
    background-color: #3b82f6;
    color: white;
    font-size: 16px;
    border-radius: 8px;
    padding: 10px 20px;
}
.stMarkdown h2 {
    color: #93c5fd;
}
input {
    font-size: 18px !important;
}
</style>
""",
    unsafe_allow_html=True,
)

st.image("ed44c522-95c3-4198-95e1-9ac6d6e595c1.png", width=80)
st.markdown(
    "<h1 style='font-size:2.5em; color:#60a5fa;'>NoAnalyst</h1>", unsafe_allow_html=True
)
st.markdown(
    "<p style='font-size:1.2em;'>Automated customer sentiment & NPS intelligence reports from public data.</p>",
    unsafe_allow_html=True,
)

company = st.text_input(
    "", placeholder="Search any company...", label_visibility="collapsed"
)

if st.button("Generate Report") and company:
    with st.spinner("Searching web for insights..."):
        query = (
            f"{company} reviews, articles, and blogs site:reddit.com OR site:trustpilot.com OR site:g2.com OR "
            f"site:twitter.com OR site:producthunt.com OR site:appstore.com OR site:bbb.org OR "
            f"site:glassdoor.com OR site:indeed.com OR site:crunchbase.com OR site:slant.co OR "
            f"site:stackshare.io OR site:trustradius.com OR site:alternativeto.net OR site:sitejabber.com OR "
            f"site:facebook.com OR site:quora.com"
        )

        results = tavily.search(
            query=query,
            search_depth="advanced",
            include_raw_content=True,
            max_results=25,
        )
        raw_results = results.get("results") or []
        urls = []
        combined_list = []

        with st.status("🔍 Crawling web sources...", expanded=True) as status:
            for r in raw_results:
                if not r or not r.get("url"):
                    continue
                url = r["url"]
                st.write(f"Crawling [{url}]({url})")
                time.sleep(0.4)
                raw_text = r.get("raw_content") or ""
                snippet = raw_text[:2000].replace("\n", " ").replace("\r", " ").strip()
                if url not in urls:
                    urls.append(url)
                    combined_list.append(f"Source: {url}\n{snippet}")
            status.update(label="✅ Sources loaded.", state="complete")

        combined_text = "\n\n---\n\n".join(combined_list)

        prompt = f"""
You are a world-class product analyst. Based on the following customer reviews, generate a clean and highly readable customer intelligence dashboard for {company}.
Use plain markdown formatting (not raw HTML or inline CSS). Include:
- A clear bold title
- A one-paragraph executive summary
- A 3-column bulleted layout with: Top praised features | Most common complaints | Suggested improvements
- Sentiment distribution (positive/neutral/negative) in % with context
- Estimated Net Promoter Score (NPS) and what it implies
- Competitor mentions
- Actionable insights
Keep formatting lightweight and visually pleasing for display in a modern dark-themed dashboard.

```
{combined_text}
```
"""
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
        }

        dlr = requests.post(
            "https://api.deepseek.com/chat/completions", headers=headers, json=payload
        )
        if dlr.status_code != 200:
            st.error("DeepSeek error: " + dlr.text)
            st.stop()

        report = dlr.json().get("choices", [])[0].get("message", {}).get("content", "")

        st.markdown("---")
        st.markdown("## 📋 Insight Report")
        st.markdown(report)

        # Visualizations: Sentiment & NPS
        match = re.search(
            r"Sentiment distribution.*?(\d+)%.*?(\d+)%.*?(\d+)%", report, re.S
        )
        nps_match = re.search(r"Estimated Net Promoter Score.*?(\d+)", report, re.S)

        if match:
            pos, neg, neu = map(int, match.groups())
            fig, ax = plt.subplots()
            ax.pie(
                [pos, neg, neu],
                labels=["Positive", "Negative", "Neutral"],
                autopct="%1.1f%%",
                colors=["#10b981", "#ef4444", "#facc15"],
            )
            ax.set_title("Sentiment Distribution")
            st.pyplot(fig)

        if nps_match:
            nps_score = int(nps_match.group(1))
            fig, ax = plt.subplots()
            ax.bar(["NPS Score"], [nps_score], color="#60a5fa")
            ax.set_ylim(-100, 100)
            ax.set_ylabel("Net Promoter Score")
            st.pyplot(fig)
