import streamlit as st
import pandas as pd
import plotly.express as px
import asyncio
import nest_asyncio
import warnings

st.set_page_config(
    page_title="Job Market Intelligence",
    page_icon="",
    layout="wide"
)
nest_asyncio.apply()
warnings.filterwarnings("ignore")

if "page" not in st.session_state:
    st.session_state.page = "home_private"

if "scraped_data_private" not in st.session_state:
    st.session_state.scraped_data_private = None

if "scrape_counts" not in st.session_state:
    st.session_state.scrape_counts = {"Indeed": 0, "Naukri": 0, "LinkedIn": 0}

if "govt_data" not in st.session_state:
    st.session_state.govt_data = None

px.defaults.template = "plotly_dark"
px.defaults.color_discrete_sequence = px.colors.qualitative.Set2

from src.database import init_db, insert_job, load_all_jobs, save_to_csv
from src.scraper import SeleniumScraper, LinkedInScraper
from src.analytics_engine import extract_skills, clean_location
from src.recommender import get_recommendations

st.markdown(
    """
<style>
    .stApp { 
        background-color: #050816;
        color: #E5E7EB;
    }
    .main-title {
        font-size: 2.4rem;
        font-weight: 800;
        color: #F9FAFB;
        margin-bottom: 0.2rem;
    }
    .subtitle {
        font-size: 0.95rem;
        color: #9CA3AF;
        margin-bottom: 1.5rem;
    }
    .resource-card {
        background: radial-gradient(circle at top left, #1F2933, #020617);
        border-radius: 14px;
        padding: 15px;
        margin-bottom: 20px;
        height: 300px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        border: 1px solid #111827;
        box-shadow: 0 18px 40px rgba(0, 0, 0, 0.4);
        transition: transform 0.15s ease, box-shadow 0.15s ease, border 0.15s ease;
    }
    .resource-card:hover {
        transform: translateY(-4px);
        border: 1px solid #F97316;
        box-shadow: 0 20px 50px rgba(0, 0, 0, 0.6);
    }
    .card-img {
        width: 100%;
        height: 140px;
        object-fit: cover;
        border-radius: 10px;
        margin-bottom: 10px;
    }
    .card-title {
        font-weight: 600;
        font-size: 14px;
        color: #F9FAFB;
        margin-bottom: 5px;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    .card-tag {
        font-size: 11px;
        color: #D1D5DB;
        background: linear-gradient(to right, #111827, #1F2937);
        padding: 3px 10px;
        border-radius: 999px;
        width: fit-content;
        border: 1px solid #374151;
    }
    .card-btn {
        display: block;
        width: 100%;
        text-align: center;
        background: linear-gradient(90deg, #F97316, #EC4899);
        color: white !important;
        padding: 8px;
        border-radius: 999px;
        text-decoration: none;
        font-weight: 700;
        font-size: 13px;
        letter-spacing: 0.03em;
    }
    .card-btn:hover {
        background: linear-gradient(90deg, #FB923C, #F472B6);
    }
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #020617, #111827);
        border-right: 1px solid #1F2933;
    }
    .metric-label {
        font-size: 0.8rem;
        color: #9CA3AF;
    }
    .metric-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: #F9FAFB;
    }
</style>
""",
    unsafe_allow_html=True,
)


def render_resource_card(item, type_label):
    img_url = item.get("thumbnail")
    if not img_url or "http" not in img_url:
        img_url = (
            "https://images.unsplash.com/photo-1501504905252-473c47e087f8"
            "?w=500&auto=format&fit=crop&q=60"
        )

    return f"""
    <div class="resource-card">
        <div>
            <img src="{img_url}" class="card-img"
                onerror="this.src='https://images.unsplash.com/photo-1501504905252-473c47e087f8?w=500&auto=format&fit=crop&q=60'">
            <div class="card-title">{item['title']}</div>
            <div class="card-tag">{type_label}</div>
        </div>
        <a href="{item['link']}" target="_blank" class="card-btn">Open Resource</a>
    </div>
    """


async def run_hybrid_scrape(
    keyword,
    location,
    limit,
    time_filter,
    work_type,
    exp_level,
    use_indeed,
    use_naukri,
    use_linkedin,
):
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
                for j in res:
                    insert_job(conn, j)
                    save_to_csv(j)
            except Exception as e:
                print("[Indeed Scraper Error]", e)
            progress_bar.progress(33)

        if use_naukri:
            status_text.text("Running Naukri Scraper...")
            try:
                res = sel_scraper.scrape_naukri(keyword, location, limit)
                jobs.extend(res)
                counts["Naukri"] = len(res)
                for j in res:
                    insert_job(conn, j)
                    save_to_csv(j)
            except Exception as e:
                print("[Naukri Scraper Error]", e)
            progress_bar.progress(66)

    if use_linkedin:
        status_text.text("Running LinkedIn Scraper...")
        lnk_scraper = LinkedInScraper()
        try:
            res = await lnk_scraper.scrape(
                keyword, location, limit, time_filter, work_type, exp_level
            )
            jobs.extend(res)
            counts["LinkedIn"] = len(res)
            for j in res:
                insert_job(conn, j)
                save_to_csv(j)
        except Exception as e:
            print("[LinkedIn Scraper Error]", e)
        progress_bar.progress(90)

    conn.close()
    progress_bar.progress(100)
    status_text.empty()

    return pd.DataFrame(jobs), counts


async def run_govt_scrape(limit, state_filter="None"):
    sel_scraper = SeleniumScraper()
    query = state_filter if state_filter.strip() else "None"
    jobs = sel_scraper.scrape_jobkaka(limit, query)

    conn = init_db()
    for j in jobs:
        insert_job(conn, j)
    conn.close()

    return pd.DataFrame(jobs)

def show_private_results_page(keyword):
    df = st.session_state.scraped_data_private
    counts = st.session_state.scrape_counts

    if df is None or df.empty:
        st.error("No scraped data available. Please run a new scrape.")
        if st.button("Back to Home"):
            st.session_state.page = "home_private"
            st.rerun()
        return

    expected_cols = [
        "title",
        "company",
        "location",
        "salary",
        "experience",
        "description",
        "date_posted",
        "site",
    ]
    for col in expected_cols:
        if col not in df.columns:
            df[col] = "Not Disclosed"

    df = df.rename(
        columns={
            "title": "Title",
            "company": "Company",
            "location": "Location",
            "site": "Platform",
            "salary": "Salary",
            "experience": "Experience",
            "date_posted": "Date Posted",
        }
    )

    if "Title" in df.columns and "Company" in df.columns:
        df.drop_duplicates(subset=["Title", "Company"], inplace=True)

    st.success(f"Scraped and analyzed {len(df)} fresh job postings.")

    m1, m2, m3 = st.columns(3)
    m1.markdown(
        f"<div class='metric-label'>Unique Companies</div>"
        f"<div class='metric-value'>{df['Company'].nunique()}</div>",
        unsafe_allow_html=True,
    )
    m2.markdown(
        f"<div class='metric-label'>Distinct Locations</div>"
        f"<div class='metric-value'>{df['Location'].nunique()}</div>",
        unsafe_allow_html=True,
    )
    m3.markdown(
        f"<div class='metric-label'>Active Platforms</div>"
        f"<div class='metric-value'>{sum(1 for v in counts.values() if v > 0)}</div>",
        unsafe_allow_html=True,
    )

    st.markdown("---")

    p1, p2, p3 = st.columns(3)
    p1.metric("LinkedIn Jobs", counts["LinkedIn"])
    p2.metric("Indeed Jobs", counts["Indeed"])
    p3.metric("Naukri Jobs", counts["Naukri"])

    tab1, tab2, tab3 = st.tabs(
        ["Market Data (This Run)", "Raw Data", "Learning Path"]
    )

    with tab1:
        c1, c2 = st.columns(2)

        with c1:
            st.subheader("Top Skills in Current Search")
            skills_df = extract_skills(df)
            if not skills_df.empty:
                fig = px.scatter(
                    skills_df,
                    x="Skill",
                    y="Count",
                    size="Count",
                    color="Skill",
                    size_max=50,
                    title="Most Mentioned Skills",
                )
                fig.update_layout(margin=dict(l=10, r=10, t=40, b=10))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No skills extracted from the current batch.")

        with c2:
            st.subheader("Location Spread")
            df_hist["Exp_Clean"] = df_hist["Experience"].apply(bucket_exp)
            df_exp = df_hist[df_hist["Exp_Clean"] != "Unknown"]

            if df_exp.empty:
                st.info("No valid experience data available.")

            else:
                bucket_order = ["0-1 years", "1-3 years", "3-5 years", "5-10 years", "10+ years"]

                exp_counts = (
                    df_exp["Exp_Clean"]
                    .value_counts()
                  .reindex(bucket_order, fill_value=0)
                   .reset_index()
                )

                exp_counts.columns = ["Experience", "Count"]

                fig = px.bar(
                    exp_counts,
                    x="Experience",
                    y="Count",
                    title="Experience Levels (Historical)",
                )

                fig.update_layout(
                    xaxis={'categoryorder':'array', 'categoryarray': bucket_order},
                    margin=dict(l=10, r=10, t=40, b=10)
                )

                st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("Scraped Job Listings")
        st.dataframe(df, use_container_width=True, height=600)
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download as CSV",
            data=csv,
            file_name=f"job_scrape_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
        )

    with tab3:
        st.subheader("Curated Learning Path")

        skills_df = extract_skills(df)
        if not skills_df.empty:
            top_skill = skills_df.iloc[0]["Skill"]
            topic = f"{top_skill} course"
            st.info(f"Focus Skill: {top_skill} (most in-demand in this search)")
        else:
            topic = f"{keyword} tutorial"

        with st.spinner("Fetching learning resources..."):
            resources = get_recommendations(topic)

        c1, c2, c3 = st.columns(3)

        with c1:
            st.markdown("Free (YouTube)")
            if resources.get("free"):
                for rec in resources["free"][:3]:
                    st.markdown(
                        render_resource_card(rec, "Video"),
                        unsafe_allow_html=True,
                    )
            else:
                st.warning("No videos found.")

        with c2:
            st.markdown("University")
            if resources.get("university"):
                for rec in resources["university"][:3]:
                    st.markdown(
                        render_resource_card(rec, "Lecture"),
                        unsafe_allow_html=True,
                    )
            else:
                st.info("No university lectures found.")

        with c3:
            st.markdown("Certificates")
            if resources.get("paid"):
                for rec in resources["paid"][:3]:
                    st.markdown(
                        render_resource_card(rec, "Certificate"),
                        unsafe_allow_html=True,
                    )
            else:
                st.info("No paid courses found.")
def show_private_home_page():
    st.markdown(
        "<div class='main-title'>Unified Job Market Intelligence</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="subtitle">Track private sector roles across LinkedIn, Indeed and '
        "Naukri and blend fresh scrapes with historical data to spot hiring trends.</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<h4 style='color:#F97316; margin-top:0.5rem;'>"
        "Configure filters on the left and hit Start Scraping, "
        "or explore historical trends below."
        "</h4>",
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.subheader("Historical Market Insights (Private)")

    df_hist = load_all_jobs()

    if df_hist.empty:
        st.warning(
            "No historical data available yet. Run a scrape to start building your dataset."
        )
        return

    if "site" in df_hist.columns:
        df_hist = df_hist[df_hist["site"].isin(["LinkedIn", "Indeed", "Naukri"])]

    if df_hist.empty:
        st.warning("Historical data exists but none from private platforms yet.")
        return

    expected_hist = [
        "title",
        "company",
        "location",
        "salary",
        "experience",
        "description",
        "date_posted",
        "site",
    ]
    for col in expected_hist:
        if col not in df_hist.columns:
            df_hist[col] = "Not Disclosed"

    df_hist = df_hist.rename(
        columns={
            "title": "Title",
            "company": "Company",
            "location": "Location",
            "site": "Platform",
            "salary": "Salary",
            "experience": "Experience",
            "date_posted": "Date Posted",
        }
    )

    if "Title" in df_hist.columns and "Company" in df_hist.columns:
        df_hist.drop_duplicates(subset=["Title", "Company"], inplace=True)

    st.success(f"Loaded {len(df_hist)} private-sector historical job entries.")
    h1, h2, h3 = st.columns(3)
    h1.markdown(
        f"<div class='metric-label'>Unique Companies</div>"
        f"<div class='metric-value'>{df_hist['Company'].nunique()}</div>",
        unsafe_allow_html=True,
    )
    h2.markdown(
        f"<div class='metric-label'>Distinct Locations</div>"
        f"<div class='metric-value'>{df_hist['Location'].nunique()}</div>",
        unsafe_allow_html=True,
    )
    h3.markdown(
        f"<div class='metric-label'>Platforms Used</div>"
        f"<div class='metric-value'>{df_hist['Platform'].nunique()}</div>",
        unsafe_allow_html=True,
    )

    st.markdown("---")

    st.subheader("Top Skills from Historical Data")
    skills_df = extract_skills(df_hist)
    if not skills_df.empty:
        fig = px.bar(
            skills_df,
            x="Skill",
            y="Count",
            title="Most In-Demand Skills (Historical)",
        )
        fig.update_layout(margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No skill data found.")

    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Top Hiring Companies")
        comp_counts = df_hist["Company"].value_counts().head(15)
        fig = px.bar(
            comp_counts,
            orientation="h",
            title="Top Hiring Companies (Historical)",
        )
        fig.update_layout(margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.subheader("Experience Requirements")
        exp_counts = df_hist["Experience"].value_counts().head(10)
        fig = px.bar(exp_counts, title="Experience Levels (Historical)")
        fig.update_layout(margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig, use_container_width=True)

    c3, c4 = st.columns(2)

    with c3:
        st.subheader("Job Distribution by Location")
        df_hist["Clean_Loc"] = df_hist["Location"].apply(clean_location)
        loc_counts = df_hist["Clean_Loc"].value_counts().head(15)
        fig = px.bar(
            loc_counts,
            orientation="h",
            title="Top Locations (Historical)",
        )
        fig.update_layout(margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig, use_container_width=True)

    with c4:
        st.subheader("Jobs per Platform")
        fig = px.pie(
            df_hist,
            names="Platform",
            title="Jobs by Platform (Historical)",
        )
        fig.update_layout(margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig, use_container_width=True)

    with st.expander("Peek at raw historical data"):
        st.dataframe(df_hist, use_container_width=True, height=400)


def show_govt_page():
    st.markdown(
        "<div class='main-title'>Government Job Notifications</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="subtitle">Latest Central and State Government recruitments, '
        "Admit Cards, and Results.</div>",
        unsafe_allow_html=True,
    )

    df_govt = st.session_state.govt_data

    if df_govt is None:
        st.info(
            "Use the sidebar to set filters and click 'Fetch Govt Jobs' to see notifications."
        )
        return

    if df_govt.empty:
        st.error(
            "Could not fetch government jobs. The source might be down or returned no data."
        )
        return

    rename_map = {}
    if "title" in df_govt.columns:
        rename_map["title"] = "Post Name"
    if "company" in df_govt.columns:
        rename_map["company"] = "Education"
    if "job_url" in df_govt.columns:
        rename_map["job_url"] = "Link"

    df_govt = df_govt.rename(columns=rename_map)

    display_cols = []
    for c in ["Post Name", "Education", "Link"]:
        if c in df_govt.columns:
            display_cols.append(c)

    if not display_cols:
        display_cols = df_govt.columns.tolist()

    df_to_display = df_govt[display_cols]

    st.success(f"Fetched {len(df_govt)} active notifications.")
    st.subheader("Live Notifications")

    st.dataframe(
        df_to_display,
        column_config={
            "Link": st.column_config.LinkColumn("Apply / Details"),
        },
        use_container_width=True,
        height=700,
    )

with st.sidebar:
    st.title("Portal Mode")

    portal_mode = st.radio(
        "Select Sector:",
        ["Private / Corporate", "Government / PSU"],
        index=0,
    )

    st.divider()

    if portal_mode == "Private / Corporate":
        st.header("Private Scraper Settings")
        keyword = st.text_input("Job Role", "Data Scientist")
        location = st.text_input("Location", "India")

        st.subheader("Filters")
        time_filter = st.selectbox(
            "Date Posted",
            ["Any Time", "Past 24 Hours", "Past Week", "Past Month"],
            index=1,
        )
        work_type = st.selectbox(
            "Work Type",
            ["Any", "On-site", "Hybrid", "Remote"],
        )
        exp_level = st.selectbox(
            "Experience Level",
            ["Any", "Internship", "Entry Level", "Associate", "Mid-Senior"],
        )

        st.subheader("Other Settings")
        limit = st.slider("Jobs per Site", 5, 100, 20)
        st.caption("Select Sources:")
        use_linkedin = st.checkbox("LinkedIn", value=True)
        use_indeed = st.checkbox("Indeed", value=True)
        use_naukri = st.checkbox("Naukri", value=True)

        scrape_btn_private = st.button("Start Scraping", type="primary")

    else:
        st.header("Government Job Filters")
        govt_location = st.text_input(
            "State Filter (Optional)",
            placeholder="e.g. Maharashtra",
        )
        g_limit = st.slider("Number of Notifications", 10, 50, 20)
        scrape_btn_govt = st.button("Fetch Govt Jobs", type="primary")

if portal_mode == "Private / Corporate":
    col1, col2, col3 = st.columns([6, 1, 1])
    with col2:
        if st.session_state.page != "home_private":
            if st.button("Home", key="home_btn"):
                st.session_state.page = "home_private"
                st.rerun()
    with col3:
        if (
            st.session_state.page != "results_private"
            and st.session_state.scraped_data_private is not None
        ):
            if st.button("Results", key="results_btn"):
                st.session_state.page = "results_private"
                st.rerun()
    st.markdown("---")

if portal_mode == "Private / Corporate":
    if "scrape_btn_private" in locals() and scrape_btn_private:
        if not (use_linkedin or use_indeed or use_naukri):
            st.error("Please select at least one website.")
        else:
            with st.spinner("Scraping live job listings..."):
                df, counts = asyncio.run(
                    run_hybrid_scrape(
                        keyword,
                        location,
                        limit,
                        time_filter,
                        work_type,
                        exp_level,
                        use_indeed,
                        use_naukri,
                        use_linkedin,
                    )
                )

            if df.empty:
                st.error(
                    "No jobs found. The scrapers might be blocked or returned no results."
                )
            else:
                st.session_state.scraped_data_private = df
                st.session_state.scrape_counts = counts
                st.session_state.page = "results_private"
                st.rerun()

    if st.session_state.page == "results_private":
        show_private_results_page(keyword)
    else:
        show_private_home_page()

else:
    if "scrape_btn_govt" in locals() and scrape_btn_govt:
        with st.spinner("Fetching latest government circulars..."):
            df_govt = asyncio.run(run_govt_scrape(g_limit, govt_location))
        st.session_state.govt_data = df_govt

    show_govt_page()
