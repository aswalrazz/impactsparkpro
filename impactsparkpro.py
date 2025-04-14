import streamlit as st
import pandas as pd
import plotly.express as px
import time
from datetime import datetime, timedelta
from utils.api_clients import OpenAlexClient
from utils.data_processing import process_openalex_data, calculate_metrics
from utils.web_scraper import get_website_text_content, enrich_publication_data, find_related_publications
import requests

# Page Configuration
st.set_page_config(
    page_title="Impact Vizor - Scholarly Impact Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
def apply_custom_theme():
    st.markdown("""
    <style>
        :root {
            --primary: #6e48aa;
            --secondary: #9d50bb;
            --accent: #4776e6;
            --bg: #f9f9ff;
            --card-bg: #ffffff;
            --text: #333333;
            --light-text: #777777;
        }
        .stApp {
            background: linear-gradient(135deg, var(--bg) 0%, #eef2f5 100%);
            color: var(--text);
        }
        [data-testid="stSidebar"] {
            background: linear-gradient(195deg, var(--primary) 0%, var(--secondary) 100%) !important;
            color: white !important;
        }
        [data-testid="stSidebar"] .st-b7 {
            color: black !important;
        }
        .stButton>button {
            background: linear-gradient(90deg, var(--primary) 0%, var(--accent) 100%);
            color: white !important;
            border: none;
            border-radius: 8px;
            padding: 8px 16px;
            font-weight: 500;
            transition: all 0.3s ease;
        }
        .stButton>button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(110, 72, 170, 0.3);
        }
        [data-testid="metric-container"] {
            background: var(--card-bg) !important;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
            padding: 15px;
            border-left: 4px solid var(--primary);
            transition: all 0.3s ease;
        }
        [data-testid="metric-container"]:hover {
            transform: translateY(-3px);
            box-shadow: 0 6px 16px rgba(0,0,0,0.1);
        }
        .st-emotion-cache-2s0is{
            color: white !important;        
        }
    </style>
    """, unsafe_allow_html=True)

apply_custom_theme()

# Initialize session state
if 'search_performed' not in st.session_state:
    st.session_state.search_performed = False
if 'search_results' not in st.session_state:
    st.session_state.search_results = None
if 'selected_articles' not in st.session_state:
    st.session_state.selected_articles = []
if 'impact_data' not in st.session_state:
    st.session_state.impact_data = None
if 'metrics' not in st.session_state:
    st.session_state.metrics = None

# App title and description
st.markdown("""
<div class="animated-element">
    <h1 style="color: #6e48aa; text-align: center; margin-bottom: 0;">ImpactSpark</h1>
    <p style="text-align: center; color: #777; font-size: 1.1rem; margin-top: 0.5rem;">
    Scholarly Impact Analytics Platform
    </p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="animated-element" style="animation-delay: 0.2s;">
    <div style="background: linear-gradient(90deg, rgba(110,72,170,0.1) 0%, rgba(157,80,187,0.1) 50%, rgba(71,118,230,0.1) 100%); 
            padding: 1.5rem; border-radius: 12px; margin: 1rem 0;">
        <p style="margin: 0; color: #555;">
        This visual analytics tool provides insight into the reach and impact of scholarly content. 
        ImpactSpark integrates data from the Open API to help you make evidence-based 
        decisions about the impact and resonance of research publications.
        </p>
    </div>
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("""
    <div style="background: rgba(255,255,255,0.1); padding: 1rem; border-radius: 12px; margin-bottom: 1.5rem;">
        <h2 style="color: white; margin: 0;">🔍 Search Parameters</h2>
    </div>
    """, unsafe_allow_html=True)
    
    search_method = st.radio("Search by:", ["Topic/Keyword", "DOI"], key="search_method")
    if search_method == "Topic/Keyword":
        search_query = st.text_input("Enter a keyword or topic", key="keyword_search")
    elif search_method == "DOI":
        search_query = st.text_input("Enter DOI", key="doi_search")
    
    min_date = datetime(1900, 1, 1)
    default_start_date = datetime.now() - timedelta(days=365*10)
    date_range = st.date_input(
        "Publication date range",
        value=(default_start_date, datetime.now()),
        min_value=min_date,
        max_value=datetime.now(),
        key="date_range"
    )
    
    with st.expander("🔧 Advanced Filters", expanded=False):
        publication_types = ["article", "book", "book-chapter", "dissertation", "posted-content", 
                             "proceedings", "reference-entry", "report", "peer-review"]
        selected_types = st.multiselect("Publication Types", options=publication_types, key="pub_types")
        open_access = st.checkbox("Only Open Access", key="open_access")
        st.subheader("Citation Count Range")
        min_citations, max_citations = st.slider("Citation Range", 0, 10000, (0, 10000), step=10, key="citation_range")
        fields = ["Biology", "Chemistry", "Computer Science", "Economics", "Engineering", 
                  "Environmental Science", "Mathematics", "Medicine", "Physics", "Psychology", "Social Sciences"]
        selected_fields = st.multiselect("Research Fields", options=fields, key="research_fields")
        recent_only = st.checkbox("Recent Publications Only (Last 2 Years)", key="recent_only")
        languages = ["English", "Chinese", "Spanish", "German", "French", "Japanese"]
        selected_languages = st.multiselect("Languages", options=languages, key="languages")
    
    if (selected_types or open_access or min_citations > 0 or max_citations < 10000 or selected_fields or recent_only or selected_languages):
        st.markdown("""
        <div style="background: rgba(255,255,255,0.1); padding: 0.5rem 1rem; border-radius: 12px; margin: 1rem 0;">
            <h4 style="color: white; margin: 0.5rem 0;">Active Filters</h4>
        </div>
        """, unsafe_allow_html=True)
        active_filters = []
        if selected_types: active_filters.append(f"📄 Types: {', '.join(selected_types)}")
        if open_access: active_filters.append("🔓 Open Access Only")
        if min_citations > 0 or max_citations < 10000: active_filters.append(f"📊 Citations: {min_citations} - {max_citations}")
        if selected_fields: active_filters.append(f"🔬 Fields: {', '.join(selected_fields)}")
        if recent_only: active_filters.append("🆕 Recent Publications Only")
        if selected_languages: active_filters.append(f"🌐 Languages: {', '.join(selected_languages)}")
        for filter_text in active_filters:
            st.markdown(f"""
            <div style="background: rgba(255,255,255,0.05); padding: 0.5rem; border-radius: 8px; margin: 0.25rem 0;">
                {filter_text}
            </div>
            """, unsafe_allow_html=True)
    
    search_button = st.button("🚀 Search", use_container_width=True, key="search_button")

# Search logic
if search_button and search_query:
    with st.spinner("🔍 Fetching data from scholarly databases..."):
        progress_bar = st.progress(0)
        for percent_complete in range(100):
            time.sleep(0.02)
            progress_bar.progress(percent_complete + 1)
        
        openalex_client = OpenAlexClient()
        start_date = date_range[0].strftime("%Y-%m-%d")
        end_date = date_range[1].strftime("%Y-%m-%d") if len(date_range) > 1 else datetime.now().strftime("%Y-%m-%d")
        
        if recent_only:
            current_date = datetime.now()
            two_years_ago = (current_date - timedelta(days=365*2)).strftime("%Y-%m-%d")
            start_date = two_years_ago
        
        filters = {"publication_date": f"{start_date}:{end_date}"}
        if selected_types: filters["type"] = "|".join(selected_types)
        if open_access: filters["is_oa"] = "true"
        if selected_fields: filters["concepts.display_name"] = "|".join(selected_fields)
        if selected_languages: filters["language"] = "|".join(selected_languages)
        
        if search_method == "DOI":
            results = openalex_client.get_work_by_doi(search_query)
        else:
            results = openalex_client.search_works(
                query=search_query, filter_field="publication_date", filter_value=f"{start_date}:{end_date}",
                additional_filters={k: v for k, v in filters.items() if k != "publication_date"}
            )
        
        processed_results = process_openalex_data(results)
        
        if isinstance(processed_results, pd.DataFrame) and not processed_results.empty:
            if min_citations > 0 or max_citations < 10000:
                processed_results = processed_results[
                    (processed_results['citations'] >= min_citations) & 
                    (processed_results['citations'] <= max_citations)
                ]
            if not processed_results.empty:
                st.session_state.search_results = processed_results
                st.session_state.search_performed = True
                st.session_state.metrics = calculate_metrics(processed_results)
            else:
                st.error("No results match your citation filters. Please adjust the citation range.")
                st.session_state.search_performed = False
        else:
            st.error("No results found for your search criteria. Please try different keywords or filters.")
            st.session_state.search_performed = False

# Display results
if st.session_state.search_performed and st.session_state.search_results is not None:
    st.markdown("""
    <div class="animated-element" style="animation-delay: 0.3s;">
        <h2 style="color: #6e48aa; border-bottom: 2px solid #6e48aa; padding-bottom: 0.5rem;">📊 Search Results</h2>
    </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.metrics:
        col1, col2, col3, col4 = st.columns(4)
        with col1: st.metric("📑 Total Publications", st.session_state.metrics["total_publications"])
        with col2: st.metric("🔗 Total Citations", st.session_state.metrics["total_citations"])
        with col3: st.metric("📈 Avg. Citations per Article", f"{st.session_state.metrics['avg_citations']:.2f}")
        with col4: st.metric("🏆 h-index", st.session_state.metrics["h_index"])
    
    display_columns = [
        'title', 'authors', 'year', 'publication_date', 'source', 'institutions', 'country_codes', 'citations', 'cited_by', 
        'related_count', 'fwci', 'citation_percentile', 'h_index_contribution', 'type', 'topic', 'subfield', 
        'field', 'domain', 'open_access_status', 'doi'
    ]
    available_columns = [col for col in display_columns if col in st.session_state.search_results.columns]
    
    if 'doi' in st.session_state.search_results.columns:
        st.session_state.search_results['doi_url'] = st.session_state.search_results['doi'].apply(
            lambda x: f"https://doi.org/{x}" if x and not str(x).startswith('http') else x
        )
        available_columns = [col for col in available_columns if col != 'doi'] + ['doi_url']
    
    column_config = {
        "title": st.column_config.TextColumn("Title"),
        "authors": st.column_config.TextColumn("Authors"),
        "year": st.column_config.NumberColumn("Year", format="%d"),
        "publication_date": st.column_config.DateColumn("Publication Date"),
        "source": st.column_config.TextColumn("Source/Journal"),
        "institutions": st.column_config.TextColumn("Institutions"),
        "country_codes": st.column_config.TextColumn("Country Codes"),
        "citations": st.column_config.NumberColumn("Citations", format="%d"),
        "cited_by": st.column_config.NumberColumn("Cited By", format="%d"),
        "related_count": st.column_config.NumberColumn("Related Works", format="%d"),
        "fwci": st.column_config.NumberColumn("FWCI", format="%.3f"),
        "citation_percentile": st.column_config.NumberColumn("Citation Percentile", format="%.2f"),
        "h_index_contribution": st.column_config.NumberColumn("H-index", format="%d"),
        "type": st.column_config.TextColumn("Type"),
        "topic": st.column_config.TextColumn("Topic"),
        "subfield": st.column_config.TextColumn("Subfield"),
        "field": st.column_config.TextColumn("Field"),
        "domain": st.column_config.TextColumn("Domain"),
        "open_access_status": st.column_config.TextColumn("Open Access"),
        "doi_url": st.column_config.LinkColumn("DOI", display_text="🌐 View", width="small"),
    }
    
    with st.expander("⚙️ Table Display Settings", expanded=False):
        selected_columns = st.multiselect(
            "Select columns to display", options=available_columns,
            default=['title', 'authors', 'year', 'institutions', 'country_codes', 'citations', 'doi_url'], key="column_selector"
        )
        if selected_columns:
            display_columns = selected_columns
        else:
            default_columns = ['title', 'authors', 'year', 'institutions', 'country_codes', 'citations', 'doi_url']
            display_columns = [col for col in default_columns if col in available_columns]
        
        sort_options = [col for col in ['citations', 'year', 'publication_date', 'title', 'fwci', 'citation_percentile'] 
                        if col in st.session_state.search_results.columns]
        if sort_options:
            sort_by = st.selectbox("Sort results by", options=sort_options, index=0 if 'citations' in sort_options else 0, key="sort_by")
            sort_order = st.radio("Sort order", options=["Descending", "Ascending"], horizontal=True, key="sort_order")
            ascending = sort_order == "Ascending"
            st.session_state.search_results = st.session_state.search_results.sort_values(by=sort_by, ascending=ascending)
    
    valid_display_columns = [col for col in display_columns if col in st.session_state.search_results.columns]
    st.dataframe(
        st.session_state.search_results[valid_display_columns], use_container_width=True,
        column_config={col: config for col, config in column_config.items() if col in valid_display_columns}, height=400
    )
    
    csv = st.session_state.search_results.to_csv(index=False)
    col1, col2 = st.columns(2)
    with col1:
        st.download_button("💾 Download results as CSV", csv, "impact_vizor_results.csv", "text/csv", key='download-csv')
    with col2:
        if st.button("✨ Enrich Data with Web Scraping", key="enrich_button"):
            with st.spinner("🔍 Enriching publication data..."):
                max_items = 10 if len(st.session_state.search_results) > 10 else len(st.session_state.search_results)
                st.info(f"Processing {max_items} publications...")
                enriched_df = enrich_publication_data(st.session_state.search_results, max_items=max_items)
                st.session_state.search_results = enriched_df
                st.success(f"✅ Successfully enhanced {max_items} publications.")
                enriched_csv = enriched_df.to_csv(index=False)
                st.download_button("💾 Download Enhanced Results as CSV", enriched_csv, "impact_vizor_enriched_results.csv", "text/csv", key='download-enriched-csv')
    
    st.markdown("""
    <div class="animated-element" style="animation-delay: 0.4s;">
        <h2 style="color: #6e48aa; border-bottom: 2px solid #6e48aa; padding-bottom: 0.5rem;">📄 Detailed Publication Information</h2>
    </div>
    """, unsafe_allow_html=True)
    
    paper_selector = st.selectbox(
        "Select a publication to view detailed information", options=st.session_state.search_results['title'].tolist(),
        format_func=lambda x: x[:100] + "..." if len(x) > 100 else x, key="paper_selector"
    )
    
    if paper_selector:
        selected_paper = st.session_state.search_results[st.session_state.search_results['title'] == paper_selector].iloc[0]
        with st.container():
            st.markdown(f"""
            <div style="background: linear-gradient(90deg, rgba(110,72,170,0.1) 0%, rgba(157,80,187,0.1) 100%); 
                    padding: 1.5rem; border-radius: 12px; margin: 1rem 0;">
                <h2 style="color: #6e48aa; margin: 0;">{selected_paper['title']}</h2>
            </div>
            """, unsafe_allow_html=True)
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("### 📋 Publication Info")
                st.markdown(f"**Year:** {selected_paper.get('year', '')}")
                st.markdown(f"**Type:** {selected_paper.get('type', '')}")
                st.markdown(f"**Source:** {selected_paper.get('source', selected_paper.get('journal', ''))}")
                st.markdown(f"**Open Access:** {selected_paper.get('open_access_status', '')}")
                if 'doi' in selected_paper and selected_paper['doi']:
                    st.markdown(f"**DOI:** [🌐 View Paper](https://doi.org/{selected_paper['doi']})")
            with col2:
                st.markdown("### 👥 Author Information")
                st.markdown(f"**Authors:** {selected_paper.get('authors', '')}")
                st.markdown(f"**Institutions:** {selected_paper.get('institutions', '')}")
                st.markdown(f"**Countries:** {selected_paper.get('country_codes', '')}")
            with col3:
                st.markdown("### 📈 Impact Metrics")
                st.markdown(f"**Citations:** {int(selected_paper.get('citations', 0))}")
                st.markdown(f"**Cited by:** {int(selected_paper.get('cited_by', 0))}")
                st.markdown(f"**Related papers:** {int(selected_paper.get('related_count', 0))}")
                st.markdown(f"**FWCI:** {selected_paper.get('fwci', 0):.3f}")
                st.markdown(f"**Citation percentile:** {selected_paper.get('citation_percentile', 0):.2f}")
                st.markdown(f"**H-index contribution:** {int(selected_paper.get('h_index_contribution', 0))}")
            
            st.markdown("### 🏷️ Subject Classification")
            subj_cols = st.columns(4)
            with subj_cols[0]: st.markdown(f"**Topic:** {selected_paper.get('topic', '')}")
            with subj_cols[1]: st.markdown(f"**Subfield:** {selected_paper.get('subfield', '')}")
            with subj_cols[2]: st.markdown(f"**Field:** {selected_paper.get('field', '')}")
            with subj_cols[3]: st.markdown(f"**Domain:** {selected_paper.get('domain', '')}")
            
            st.markdown("### 📝 Abstract")
            has_abstract = 'abstract' in selected_paper and selected_paper['abstract']
            if has_abstract:
                st.markdown(f"""
                <div style="background: rgba(110,72,170,0.05); padding: 1rem; border-radius: 8px;">
                    {selected_paper['abstract']}
                </div>
                """, unsafe_allow_html=True)
            else:
                if 'doi' in selected_paper and selected_paper['doi']:
                    doi_url = f"https://doi.org/{selected_paper['doi']}" if not str(selected_paper['doi']).startswith('http') else selected_paper['doi']
                    if st.button("🔍 Fetch Abstract from Web", key="fetch_abstract"):
                        with st.spinner("Fetching abstract..."):
                            content = get_website_text_content(doi_url)
                            if content:
                                abstract_preview = content[:1000] + "..." if len(content) > 1000 else content
                                st.markdown(f"""
                                <div style="background: rgba(110,72,170,0.05); padding: 1rem; border-radius: 8px;">
                                    {abstract_preview}
                                </div>
                                """, unsafe_allow_html=True)
                                if 'full_text' not in st.session_state:
                                    st.session_state.full_text = {}
                                st.session_state.full_text[selected_paper['doi']] = content
                                if st.button("📄 View Full Text", key="view_full_text"):
                                    st.text_area("Full Publication Text", content, height=400)
                            else:
                                st.warning("Could not extract content from the publication source.")
                    else:
                        st.info("No abstract available. Click the button to attempt retrieval.")
                else:
                    st.info("No abstract or DOI available.")
            
            if 'doi' in selected_paper and selected_paper['doi']:
                st.markdown("### 🔗 Related Publications")
                doi_url = f"https://doi.org/{selected_paper['doi']}" if not str(selected_paper['doi']).startswith('http') else selected_paper['doi']
                if 'related_pubs' not in st.session_state:
                    st.session_state.related_pubs = {}
                if selected_paper['doi'] in st.session_state.related_pubs:
                    related_links = st.session_state.related_pubs[selected_paper['doi']]
                    if related_links:
                        for i, link in enumerate(related_links):
                            st.markdown(f"{i+1}. [{link}]({link})")
                    else:
                        st.info("No related publications found.")
                else:
                    if st.button("🔍 Find Related Publications", key="find_related"):
                        with st.spinner("Searching for related publications..."):
                            related_links = find_related_publications(doi_url)
                            st.session_state.related_pubs[selected_paper['doi']] = related_links
                            if related_links:
                                for i, link in enumerate(related_links):
                                    st.markdown(f"{i+1}. [{link}]({link})")
                            else:
                                st.info("No related publications found.")
    
    # Impact Visualization
    if not st.session_state.search_results.empty:
        st.markdown("""
        <div class="animated-element" style="animation-delay: 0.5s;">
            <h2 style="color: #6e48aa; border-bottom: 2px solid #6e48aa; padding-bottom: 0.5rem;">📊 Impact Visualization</h2>
        </div>
        """, unsafe_allow_html=True)
        
        with st.expander("🎨 Visualization Settings", expanded=False):
            viz_col1, viz_col2 = st.columns(2)
            with viz_col1:
                color_schemes = {
                    "Cyber Science": ["#6e48aa", "#9d50bb", "#4776e6", "#5e72e4", "#825ee4"],
                    "Viridis": px.colors.sequential.Viridis,
                    "Plasma": px.colors.sequential.Plasma,
                    "Blues": px.colors.sequential.Blues,
                    "Reds": px.colors.sequential.Reds,
                    "Greens": px.colors.sequential.Greens,
                    "Spectral": px.colors.diverging.Spectral
                }
                selected_color_scheme = st.selectbox("Color Scheme", options=list(color_schemes.keys()), index=0, key="color_scheme")
                line_styles = ["solid", "dot", "dash", "longdash", "dashdot"]
                selected_line_style = st.selectbox("Line Style", options=line_styles, index=0, key="line_style")
                show_grid = st.checkbox("Show Grid Lines", value=True, key="show_grid")
            with viz_col2:
                chart_types = ["Line", "Bar", "Area"]
                selected_chart_type = st.selectbox("Chart Type", options=chart_types, index=0, key="chart_type")
                smoothing_enabled = st.checkbox("Enable Smoothing", value=True, key="smoothing")
                smoothing_line_shape = "spline" if smoothing_enabled else "linear"
                animation_enabled = st.checkbox("Enable Animation", value=False, key="animation")
        
        tab1, tab2, tab3, tab4 = st.tabs(["📅 Publications Timeline", "📈 Citation Analysis", "👥 Author Metrics", "🌍 Geo Distribution"])
        
        with tab1:
            df_grouped = st.session_state.search_results.copy()
            df_grouped['year'] = pd.to_datetime(df_grouped['publication_date']).dt.year
            pub_by_year = df_grouped.groupby('year').size().reset_index(name='count')
            pub_by_year['cumulative'] = pub_by_year['count'].cumsum()
            pub_by_year['growth_rate'] = pub_by_year['count'].pct_change() * 100
            color_sequence = color_schemes.get(selected_color_scheme, color_schemes["Cyber Science"])
            
            if selected_chart_type == "Bar":
                fig1 = px.bar(pub_by_year, x='year', y=['count', 'cumulative'], title='Publication Trends Over Time',
                              labels={'count': 'Annual Publications', 'cumulative': 'Cumulative Publications', 'year': 'Year'},
                              color_discrete_sequence=color_sequence, barmode='group')
            elif selected_chart_type == "Area":
                fig1 = px.area(pub_by_year, x='year', y=['count', 'cumulative'], title='Publication Trends Over Time',
                               labels={'count': 'Annual Publications', 'cumulative': 'Cumulative Publications', 'year': 'Year'},
                               color_discrete_sequence=color_sequence)
            else:
                fig1 = px.line(pub_by_year, x='year', y=['count', 'cumulative'], title='Publication Trends Over Time',
                               labels={'count': 'Annual Publications', 'cumulative': 'Cumulative Publications', 'year': 'Year'},
                               line_shape=smoothing_line_shape, markers=True, color_discrete_sequence=color_sequence)
            
            if selected_chart_type == "Line":
                for trace in fig1.data:
                    trace.update(line=dict(dash=selected_line_style))
            
            fig1.update_layout(
                hovermode="x unified", legend=dict(orientation="h", yanchor="top", y=1.02, xanchor="right", x=1),
                plot_bgcolor='white', xaxis=dict(gridcolor='lightgray' if show_grid else None, showgrid=show_grid, title=dict(font=dict(size=14))),
                yaxis=dict(gridcolor='lightgray' if show_grid else None, showgrid=show_grid, title=dict(font=dict(size=14)))
            )
            if animation_enabled:
                fig1.update_layout(updatemenus=[{"type": "buttons", "showactive": False, "buttons": [{"label": "Play", "method": "animate", "args": [None, {"frame": {"duration": 500, "redraw": True}, "fromcurrent": True}]}]}], transitions=[{'duration': 500, 'easing': 'cubic-in-out'}])
            st.plotly_chart(fig1, use_container_width=True)
            
            if len(pub_by_year) > 2:
                growth_data = pub_by_year.dropna(subset=['growth_rate'])
                if not growth_data.empty:
                    fig_growth = px.bar(growth_data, x='year', y='growth_rate', title='Year-on-Year Publication Growth Rate (%)',
                                        color='growth_rate', color_continuous_scale=px.colors.diverging.RdBu, color_continuous_midpoint=0, text='growth_rate')
                    fig_growth.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                    fig_growth.update_layout(plot_bgcolor='white', xaxis=dict(gridcolor='lightgray'), yaxis=dict(gridcolor='lightgray'))
                    st.plotly_chart(fig_growth, use_container_width=True)
        
        with tab2:
            if 'citations' in st.session_state.search_results.columns:
                col1, col2 = st.columns(2)
                total_citations = int(st.session_state.search_results['citations'].sum())
                avg_citations = st.session_state.search_results['citations'].mean()
                max_citations = st.session_state.search_results['citations'].max()
                citation_median = st.session_state.search_results['citations'].median()
                with col1:
                    st.metric("📊 Total Citations", f"{total_citations:,}")
                    st.metric("🏆 Maximum Citations", f"{int(max_citations):,}")
                with col2:
                    st.metric("📈 Average Citations", f"{avg_citations:.2f}")
                    st.metric("⚖️ Median Citations", f"{citation_median:.1f}")
                
                use_log = st.checkbox("Use logarithmic scale", value=True, key="log_scale")
                valid_citations = st.session_state.search_results['citations'].dropna()
                if not valid_citations.empty:
                    fig2 = px.histogram(st.session_state.search_results, x='citations', title='Citation Distribution',
                                        labels={'citations': 'Number of Citations', 'count': 'Number of Articles'},
                                        nbins=min(30, len(valid_citations.unique())), opacity=0.8, color_discrete_sequence=[color_sequence[0]])
                    if use_log:
                        fig2.update_layout(xaxis_type="log")
                    fig2.update_layout(bargap=0.1, plot_bgcolor='white',
                                       xaxis=dict(gridcolor='lightgray' if show_grid else None, showgrid=show_grid, title=dict(font=dict(size=14))),
                                       yaxis=dict(gridcolor='lightgray' if show_grid else None, showgrid=show_grid, title=dict(font=dict(size=14))))
                    st.plotly_chart(fig2, use_container_width=True)
                    
                    st.subheader("🏅 Most Cited Publications")
                    top_cited = st.session_state.search_results.sort_values('citations', ascending=False).head(5)
                    fig_top = px.bar(top_cited, y='title', x='citations', orientation='h', title='Top 5 Most Cited Publications',
                                     text='citations', color='citations', color_continuous_scale=color_sequence)
                    fig_top.update_traces(textposition='outside')
                    fig_top.update_layout(plot_bgcolor='white',
                                          xaxis=dict(gridcolor='lightgray' if show_grid else None, showgrid=show_grid, title=dict(font=dict(size=14))),
                                          yaxis=dict(categoryorder='total ascending', gridcolor='lightgray' if show_grid else None, showgrid=show_grid))
                    st.plotly_chart(fig_top, use_container_width=True)
                else:
                    st.warning("No valid citation data available.")
            else:
                st.warning("Citation data not available.")
        
        with tab3:
            if 'authors' in st.session_state.search_results.columns:
                all_authors = []
                for authors_str in st.session_state.search_results['authors']:
                    if pd.notna(authors_str) and authors_str:
                        author_list = [a.strip() for a in authors_str.split(',')]
                        all_authors.extend(author_list)
                if all_authors:
                    author_counts = pd.Series(all_authors).value_counts()
                    top_authors = author_counts.head(10)
                    fig_authors = px.bar(x=top_authors.index, y=top_authors.values, title='Top 10 Contributing Authors',
                                         labels={'x': 'Author', 'y': 'Number of Publications'}, color=top_authors.values,
                                         color_continuous_scale=color_sequence, text=top_authors.values)
                    fig_authors.update_traces(textposition='outside')
                    fig_authors.update_layout(plot_bgcolor='white',
                                              xaxis=dict(gridcolor='lightgray' if show_grid else None, showgrid=show_grid, tickangle=45),
                                              yaxis=dict(gridcolor='lightgray' if show_grid else None, showgrid=show_grid))
                    st.plotly_chart(fig_authors, use_container_width=True)
                else:
                    st.info("No author information available.")
            else:
                st.info("Author information not available.")
        
        with tab4:  # Geo Distribution Tab
            st.subheader("🌍 Geographic Distribution of Citations by Country")
            st.write("This map shows the total citations aggregated by country based on institution affiliations.")
            
            import pycountry
            
            if 'country_codes' in st.session_state.search_results.columns:
                st.write("Sample of country_codes column:")
                st.write(st.session_state.search_results[['title', 'country_codes']].head())
                
                country_citations = []
                for idx, row in st.session_state.search_results.iterrows():
                    if pd.notna(row['country_codes']) and row['country_codes']:
                        countries = [c.strip().upper() for c in row['country_codes'].split(',') if c.strip()]
                        for country in countries:
                            if len(country) == 2 and country.isalpha():
                                try:
                                    # Convert 2-letter to 3-letter ISO code
                                    country_3 = pycountry.countries.get(alpha_2=country).alpha_3
                                    country_citations.append({'country': country_3, 'citations': row['citations']})
                                except AttributeError:
                                    st.warning(f"Could not convert country code: '{country}' in row {idx}")
                            else:
                                st.warning(f"Invalid country code found: '{country}' in row {idx}")
                
                if country_citations:
                    country_df = pd.DataFrame(country_citations)
                    country_df = country_df.groupby('country', as_index=False)['citations'].sum()
                    st.write("Aggregated citations by country (3-letter ISO codes):")
                    st.write(country_df)
                    
                    fig_geo = px.choropleth(
                        country_df, 
                        locations="country", 
                        locationmode="ISO-3", 
                        color="citations",
                        hover_name="country", 
                        title="Citations by Country", 
                        color_continuous_scale=color_sequence,
                        projection="natural earth"
                    )
                    fig_geo.update_layout(
                        plot_bgcolor='white', 
                        geo=dict(
                            showcountries=True, 
                            countrycolor='lightgray'  # Use countrycolor for border lines
                        ),
                        margin={"r":0, "t":50, "l":0, "b":0}
                    )
                    st.plotly_chart(fig_geo, use_container_width=True)
                    
                    st.subheader("Top Countries by Citations")
                    top_countries = country_df.sort_values('citations', ascending=False).head(5)
                    st.dataframe(top_countries, use_container_width=True)
                else:
                    st.warning("No valid country codes extracted from 'country_codes' column. Ensure data contains valid 2-letter ISO codes (e.g., 'US', 'GB').")
            else:
                st.error("No 'country_codes' column found in search results. Check data processing logic.")

else:
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(110,72,170,0.1) 0%, rgba(157,80,187,0.1) 100%); 
            padding: 2rem; border-radius: 12px; margin: 1rem 0; text-align: center;">
        <h3 style="color: #6e48aa; margin-top: 0;">🌟 Welcome to ImpactSpark!</h3>
        <p style="color: #555;">
        To get started:<br>
        1️⃣ Use the sidebar to set your search parameters<br>
        2️⃣ Click the "Search" button to retrieve scholarly impact data<br>
        3️⃣ Explore the various visualizations and analytics tools<br>
        </p>
        <p style="font-size: 0.9em; color: #777;">
        Navigate between different analytics views using the page selector in the sidebar.
        </p>
    </div>
    """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #6e48aa; font-size: 0.8em; padding: 1rem;">
    Developed with ❤ by <strong>Data SparkLabs</strong> | Last updated: {}
    </div>
    """.format(datetime.now().strftime("%Y-%m-%d")),
    unsafe_allow_html=True
)
