import streamlit as st
import pandas as pd
import plotly.express as px
import asyncio
import nest_asyncio
import warnings

st.set_page_config(page_title="Job Market Intelligence", page_icon="🕵️", layout="wide")
nest_asyncio.apply()
warnings.filterwarnings("ignore")

from src.database import init_db, insert_job, load_all_jobs
from src.scraper import SeleniumScraper, LinkedInScraper
from src.analytics_engine import extract_skills, clean_location
from src.recommender import get_recommendations


st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    
    .resource-card {
        background-color: #262730;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 20px;
        height: 300px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        border: 1px solid #333;
    }
    .resource-card:hover { border: 1px solid #FF4B4B; }
    .card-img {
        width: 100%;
        height: 140px;
        object-fit: cover;
        border-radius: 5px;
        margin-bottom: 10px;
    }
    .card-title {
        font-weight: bold;
        font-size: 14px;
        color: #FFF;
        margin-bottom: 5px;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    .card-tag {
        font-size: 11px;
        color: #AAA;
        background-color: #1E1E1E;
        padding: 2px 8px;
        border-radius: 4px;
        width: fit-content;
    }
    .card-btn {
        display: block;
        width: 100%;
        text-align: center;
        background-color: #FF4B4B;
        color: white !important;
        padding: 8px;
        border-radius: 5px;
        text-decoration: none;
        font-weight: bold;
    }
    .card-btn:hover { background-color: #FF2B2B; }
</style>
""", unsafe_allow_html=True)

st.title("Unified Job Market Intelligence")

with st.sidebar:
    st.header("Scraper Settings")
    keyword = st.text_input("Job Role", "Data Scientist")
    location = st.text_input("Location", "India")
    
    st.divider()
    st.subheader("Filters")
    time_filter = st.selectbox("Date Posted", ["Any Time", "Past 24 Hours", "Past Week", "Past Month"], index=1)
    work_type = st.selectbox("Work Type", ["Any", "On-site", "Hybrid", "Remote"])
    exp_level = st.selectbox("Experience Level", ["Any", "Internship", "Entry Level", "Associate", "Mid-Senior"])
    
    st.divider()
    limit = st.slider("Jobs per Site", 5, 100, 20)
    st.caption("Select Sources:")
    use_linkedin = st.checkbox("LinkedIn", value=True)
    use_indeed = st.checkbox("Indeed", value=True)
    use_naukri = st.checkbox("Naukri", value=True)
    
    scrape_btn = st.button("Start Scraping", type="primary")


def render_resource_card(item, type_label):
    img_url = item.get('thumbnail')

    if not img_url or "http" not in img_url:
        img_url = "https://images.unsplash.com/photo-1501504905252-473c47e087f8?w=500&auto=format&fit=crop&q=60"
    
    return f"""
    <div class="resource-card">
        <div>
            <img src="{img_url}" class="card-img" onerror="this.src='https://images.unsplash.com/photo-1501504905252-473c47e087f8?w=500&auto=format&fit=crop&q=60'">
            <div class="card-title">{item['title']}</div>
            <div class="card-tag">{type_label}</div>
        </div>
        <a href="{item['link']}" target="_blank" class="card-btn">Open Resource ➜</a>
    </div>
    """

async def run_hybrid_scrape(keyword, location, limit, time_filter, work_type, exp_level):
    jobs = []
    status_text = st.empty()
    progress_bar = st.progress(0)
    conn = init_db()
    
    counts = {"Indeed": 0, "Naukri": 0, "LinkedIn": 0}
    
    if use_indeed or use_naukri:
        sel_scraper = SeleniumScraper()
        
        if use_indeed:
            status_text.text("Running Indeed Scraper...")
            try:
                res = sel_scraper.scrape_indeed(keyword, limit, time_filter) 
                jobs.extend(res)
                counts["Indeed"] = len(res)
                for j in res: insert_job(conn, j)
            except Exception as e: print("[Scraper Error]", e)
            progress_bar.progress(33)

        if use_naukri:
            status_text.text("Running Naukri Scraper...")
            try:
                res = sel_scraper.scrape_naukri(keyword, location, limit)
                jobs.extend(res)
                counts["Naukri"] = len(res)
                for j in res: insert_job(conn, j)
            except Exception as e: print("[Scraper Error]", e)
            progress_bar.progress(66)

    if use_linkedin:
        status_text.text("Running LinkedIn Scraper...")
        lnk_scraper = LinkedInScraper()
        try:
            res = await lnk_scraper.scrape(keyword, location, limit, time_filter, work_type, exp_level)
            jobs.extend(res)
            counts["LinkedIn"] = len(res)
            for j in res: insert_job(conn, j)
        except Exception as e: print("[Scraper Error]", e)
        progress_bar.progress(90)

    conn.close()
    progress_bar.progress(100)
    status_text.empty()
    
    return pd.DataFrame(jobs), counts

if scrape_btn:
    if not (use_linkedin or use_indeed or use_naukri):
        st.error("Please select at least one website.")
    else:
        with st.spinner(f"Searching..."):

            df, counts = asyncio.run(run_hybrid_scrape(keyword, location, limit, time_filter, work_type, exp_level))
        
        if df.empty:
            st.error("No jobs found. The scrapers might be blocked by the websites.")
        else:
            expected_cols = ["title", "company", "location", "salary", "experience", "description", "date_posted", "site"]
            for col in expected_cols:
                if col not in df.columns:
                    df[col] = "Not Disclosed"


            df = df.rename(columns={
                "title": "Title",
                "company": "Company",
                "location": "Location",
                "site": "Platform",
                "salary": "Salary",
                "experience": "Experience",
                "date_posted": "Date Posted"
            })

            if "Title" in df.columns and "Company" in df.columns:
                df.drop_duplicates(subset=["Title", "Company"], inplace=True)
                
            else:
                st.warning("Some expected columns are missing; duplicate removal skipped.")


            
            st.success(f"Analyzed {len(df)} jobs.")
            
            b1, b2, b3 = st.columns(3)
            b1.metric("LinkedIn", counts["LinkedIn"])
            b2.metric("Indeed", counts["Indeed"])
            b3.metric("Naukri", counts["Naukri"])
            
            tab1, tab2, tab3 = st.tabs(["Market Data", "Raw Data", "Learning Path"])
            
            
            with tab1:
                c1, c2 = st.columns(2)
                with c1:
                    st.subheader("Top Skills")
                    skills_df = extract_skills(df)
                    if not skills_df.empty:
                        fig = px.scatter(skills_df, x='Skill', y='Count', size='Count', color='Skill', size_max=50)
                        st.plotly_chart(fig, use_container_width=True)
                    else: st.info("No skills extracted.")
                with c2:
                    st.subheader("Locations")
                    df['Clean_Loc'] = df['Location'].apply(clean_location)
                    fig_loc = px.pie(df, names='Clean_Loc', hole=0.4)
                    st.plotly_chart(fig_loc, use_container_width=True)


            with tab2:
                st.subheader("Scraped Job Listings")
                st.dataframe(df, use_container_width=True, height=600)

            with tab3:
                st.subheader("Curated Learning Path")
                
                if not skills_df.empty:
                    top_skill = skills_df.iloc[0]['Skill']
                    topic = f"{top_skill} course"
                    st.info(f"Focus Skill: **{top_skill}** (Most demanded in this search)")
                else:
                    topic = f"{keyword} tutorial"
                
                with st.spinner("Fetching best courses..."):
                    resources = get_recommendations(topic)

                c1, c2, c3 = st.columns(3)
                
                with c1:
                    st.markdown("#### Free (YouTube)")
                    if resources.get("free"):
                        for rec in resources["free"][:3]:
                            st.markdown(render_resource_card(rec, "Video"), unsafe_allow_html=True)
                    else: st.warning("No videos found.")

                with c2:
                    st.markdown("#### University")
                    if resources.get("university"):
                        for rec in resources["university"][:3]:
                            st.markdown(render_resource_card(rec, "Lecture"), unsafe_allow_html=True)
                    else: st.info("No university lectures found.")

                with c3:
                    st.markdown("#### Certificates")
                    if resources.get("paid"):
                        for rec in resources["paid"][:3]:
                            st.markdown(render_resource_card(rec, "Certificate"), unsafe_allow_html=True)
                    else: st.info("No paid courses found.")

else:
    st.info("Select filters in the sidebar and click 'Start Scraping'")
    st.subheader("Historical Market Insights")
    df_hist = load_all_jobs()

    if df_hist.empty:
        st.warning("No historical data available. Scrape jobs to begin.")

    else:
        df_hist = df_hist.rename(columns={
            "title": "Title", "company": "Company", "location": "Location", 
            "site": "Platform", "salary": "Salary", "experience": "Experience", 
            "date_posted": "Date Posted"
        })

        st.subheader("Top Skills from Historical Data")
        skills_df = extract_skills(df_hist)

        if not skills_df.empty:
            fig = px.bar(skills_df, x="Skill", y="Count", title="Top Skills (Historical)")
            st.plotly_chart(fig, use_container_width=True)


        st.subheader("Job Distribution by Location")
        df_hist['Clean_Loc'] = df_hist['Location'].apply(clean_location)
        fig_loc = px.pie(df_hist, names='Clean_Loc', title="Locations (Historical)")
        st.plotly_chart(fig_loc, use_container_width=True)

        st.subheader("Jobs per Platform")
        fig_plat = px.histogram(df_hist, x="Platform", title="Jobs by Platform (Historical)")
        st.plotly_chart(fig_plat, use_container_width=True)
