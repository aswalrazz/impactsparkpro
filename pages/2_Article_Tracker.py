import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from datetime import datetime

# Set page config
st.set_page_config(page_title="Article Tracker", page_icon="📄", layout="wide")

# Page title
st.title("Article Tracker")
st.markdown("Track and analyze individual articles or groups of articles")

# Check if search has been performed and data exists
if 'search_performed' not in st.session_state or not st.session_state.search_performed:
    st.info("Please perform a search on the main page first to track articles.")
    st.stop()
elif 'search_results' not in st.session_state or st.session_state.search_results is None or st.session_state.search_results.empty:
    st.warning("No articles available for tracking. Please search for scholarly content on the main page.")
    st.stop()

# Get data from session state
df = st.session_state.search_results.copy()

# Standardize column names - map 'source' to 'journal' if needed
if 'journal' not in df.columns and 'source' in df.columns:
    df['journal'] = df['source']

# Ensure required columns exist
required_columns = ['title', 'authors', 'publication_date', 'citations']
missing_columns = [col for col in required_columns if col not in df.columns]
if missing_columns:
    st.error(f"Missing required columns for analysis: {', '.join(missing_columns)}")
    st.stop()

# Convert publication_date column to datetime format
df['publication_date'] = pd.to_datetime(df['publication_date'], errors='coerce')

# Sidebar for article selection
with st.sidebar:
    st.header("Article Selection")

    selection_method = st.radio("Selection Method", ["Individual Article", "Multiple Articles"])

    if selection_method == "Individual Article":
        # Dropdown to select a specific article
        article_titles = df['title'].tolist()
        selected_article = st.selectbox("Select an article to track", options=article_titles)

        # Filter dataframe to get just the selected article
        selected_df = df[df['title'] == selected_article]

    else:  # Multiple Articles
        st.subheader("Filter Articles")

        # Filter by year range
        min_year = int(df['publication_date'].dt.year.min()) if not df['publication_date'].isna().all() else 2000
        max_year = int(df['publication_date'].dt.year.max()) if not df['publication_date'].isna().all() else datetime.now().year
        year_range = st.slider("Publication Year", min_value=min_year, max_value=max_year, value=(min_year, max_year))

        # Filter by journal if available
        if 'journal' in df.columns and not df['journal'].isna().all():
            journals = ['All'] + sorted(df['journal'].dropna().unique().tolist())
            selected_journal = st.selectbox("Journal", options=journals)
        else:
            selected_journal = 'All'
            st.info("Journal information not available")

        # Filter by author
        if 'authors' in df.columns:
            all_authors = set()
            for authors_str in df['authors'].dropna():
                all_authors.update([author.strip() for author in authors_str.split(',')])
            unique_authors = ['All'] + sorted(all_authors)
            selected_author = st.selectbox("Author", options=unique_authors)
        else:
            selected_author = 'All'

        # Apply filters
        selected_df = df[
            (df['publication_date'].dt.year >= year_range[0]) &
            (df['publication_date'].dt.year <= year_range[1])
        ]

        if selected_journal != 'All' and 'journal' in selected_df.columns:
            selected_df = selected_df[selected_df['journal'] == selected_journal]

        if selected_author != 'All' and 'authors' in selected_df.columns:
            selected_df = selected_df[selected_df['authors'].str.contains(selected_author, na=False)]

# Display article(s) information
if not selected_df.empty:
    if len(selected_df) == 1:
        article = selected_df.iloc[0]
        st.subheader(article['title'])

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Authors:** {article['authors']}")
            
            # Fix publication date formatting
            pub_date = pd.to_datetime(article['publication_date'], errors='coerce')
            pub_date_str = pub_date.strftime('%B %d, %Y') if pd.notna(pub_date) else 'Unknown'
            st.markdown(f"**Publication Date:** {pub_date_str}")

            journal_info = article.get('journal', article.get('source', 'Unknown'))
            st.markdown(f"**Journal/Source:** {journal_info if pd.notna(journal_info) else 'Unknown'}")

        with col2:
            doi = article.get('doi', '')
            if pd.notna(doi) and doi != '':
                st.markdown(f"**DOI:** [{doi}](https://doi.org/{doi})")
            else:
                st.markdown("**DOI:** Not available")
            
            citations = article.get('citations', 0)
            st.markdown(f"**Citations:** {int(citations) if pd.notna(citations) else 0}")
            
            pub_type = article.get('type', 'Unknown')
            st.markdown(f"**Type:** {pub_type if pd.notna(pub_type) else 'Unknown'}")

        if 'abstract' in article and pd.notna(article['abstract']) and article['abstract'] != '':
            with st.expander("Abstract", expanded=True):
                st.write(article['abstract'])

        if 'keywords' in article and pd.notna(article['keywords']) and article['keywords'] != '':
            with st.expander("Keywords/Concepts"):
                keywords = [kw.strip() for kw in article['keywords'].split(',')]
                st.write(", ".join(keywords))

        # Citation Metrics
        st.subheader("Impact Metrics")
        citations = int(article['citations']) if pd.notna(article['citations']) else 0
        years_since_pub = datetime.now().year - pub_date.year if pd.notna(pub_date) else 0
        citations_per_year = citations / max(1, years_since_pub)

        metric_col1, metric_col2, metric_col3 = st.columns(3)
        metric_col1.metric("Total Citations", citations)
        metric_col2.metric("Years Since Publication", years_since_pub)
        metric_col3.metric("Citations Per Year", f"{citations_per_year:.2f}")

        # Comparative Impact
        if len(df) > 1:
            st.subheader("Comparative Impact")
            same_year_df = df[df['publication_date'].dt.year == pub_date.year]
            avg_citations = same_year_df['citations'].mean()
            percentile = sum(df['citations'] <= citations) / len(df) * 100

            comp_col1, comp_col2 = st.columns(2)
            comp_col1.metric("Citations vs. Avg", f"{citations}", f"{citations - avg_citations:.1f}")
            comp_col2.metric("Citation Percentile", f"{percentile:.1f}%")

    else:
        st.subheader(f"Tracking {len(selected_df)} Articles")
        total_citations = selected_df['citations'].sum()
        avg_citations = selected_df['citations'].mean()

        stat_col1, stat_col2, stat_col3 = st.columns(3)
        stat_col1.metric("Total Articles", len(selected_df))
        stat_col2.metric("Total Citations", f"{total_citations:.0f}")
        stat_col3.metric("Average Citations", f"{avg_citations:.2f}")

        # Publications Over Time
        st.subheader("Publications Over Time")
        pub_by_year = selected_df.groupby(selected_df['publication_date'].dt.year).size().reset_index(name='count')

        fig1 = px.bar(pub_by_year, x='publication_date', y='count', title='Publications by Year')
        st.plotly_chart(fig1, use_container_width=True)

        # Most Cited Articles
        st.subheader("Most Cited Articles")
        top_papers = selected_df.sort_values('citations', ascending=False).head(10)
        
        # Determine which columns to display
        display_cols = ['title', 'authors', 'publication_date', 'citations', 'doi']
        if 'journal' in top_papers.columns:
            display_cols.insert(3, 'journal')  # Insert journal after publication_date if available
        
        st.dataframe(top_papers[display_cols])

else:
    st.warning("No articles match the selected criteria. Please adjust your filters.")