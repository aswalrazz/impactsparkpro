import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime

# Set page config
st.set_page_config(page_title="Citation Analytics", page_icon="📈", layout="wide")

# Page title
st.title("Citation Analytics")
st.markdown("Analyze citation patterns and impact trends of scholarly publications")

# Check if search has been performed and data exists
if 'search_performed' not in st.session_state or not st.session_state.search_performed:
    st.info("Please perform a search on the main page first to see citation analytics.")
    st.stop()
elif 'search_results' not in st.session_state or st.session_state.search_results is None or st.session_state.search_results.empty:
    st.warning("No data available for analysis. Please search for scholarly content on the main page.")
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

# Ensure publication_date is in datetime format
df['publication_date'] = pd.to_datetime(df['publication_date'], errors='coerce')

# Drop rows with NaT (invalid dates)
df = df.dropna(subset=['publication_date'])

# Sidebar for filtering
with st.sidebar:
    st.header("Filter Data")

    # Filter by publication year
    min_year = int(df['publication_date'].dt.year.min())
    max_year = int(df['publication_date'].dt.year.max())

    # Handle case where min_year equals max_year
    if min_year == max_year:
        min_year = 1900
        max_year = datetime.now().year

    selected_years = st.slider(
        "Publication Year Range",
        min_value=min_year,
        max_value=max_year,
        value=(min_year, max_year)
    )

    # Filter by citation count
    min_citations = int(df['citations'].min())
    max_citations = int(df['citations'].max())

    # Adjust citation range if needed
    if min_citations == max_citations:
        if min_citations == 0:
            max_citations = 10
        else:
            min_citations = 0
            max_citations = max(max_citations * 2, max_citations + 10)

    selected_citations = st.slider(
        "Citation Range",
        min_value=min_citations,
        max_value=max_citations,
        value=(min_citations, max_citations)
    )

    # Filter by journal
    if 'journal' in df.columns and not df['journal'].isna().all():
        journals = ['All'] + sorted(df['journal'].dropna().unique().tolist())
        selected_journal = st.selectbox("Filter by Journal", options=journals)
    else:
        selected_journal = 'All'
        st.info("Journal information not available")

# Apply filters
filtered_df = df[
    (df['publication_date'].dt.year >= selected_years[0]) &
    (df['publication_date'].dt.year <= selected_years[1]) &
    (df['citations'] >= selected_citations[0]) &
    (df['citations'] <= selected_citations[1])
]

if selected_journal != 'All' and 'journal' in filtered_df.columns:
    filtered_df = filtered_df[filtered_df['journal'] == selected_journal]

# Display filtered data metrics
if not filtered_df.empty:
    st.subheader("Citation Metrics")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Publications", len(filtered_df))
    col2.metric("Total Citations", int(filtered_df['citations'].sum()))
    col3.metric("Average Citations", f"{filtered_df['citations'].mean():.2f}")
    col4.metric("Median Citations", f"{filtered_df['citations'].median():.1f}")

    # Citation analytics visualizations
    st.subheader("Citation Distribution")

    viz_type = st.radio(
        "Select visualization type:",
        ["Histogram", "Box Plot", "Scatter Plot", "Time Series"]
    )

    if viz_type == "Histogram":
        fig = px.histogram(
            filtered_df,
            x='citations',
            title='Citation Distribution',
            labels={'citations': 'Number of Citations'},
            nbins=30
        )
        fig.update_layout(bargap=0.1)
        st.plotly_chart(fig, use_container_width=True)

    elif viz_type == "Box Plot":
        filtered_df['year'] = filtered_df['publication_date'].dt.year
        fig = px.box(
            filtered_df,
            x='year',
            y='citations',
            title='Citation Distribution by Publication Year',
            labels={'year': 'Publication Year', 'citations': 'Number of Citations'}
        )
        st.plotly_chart(fig, use_container_width=True)

    elif viz_type == "Scatter Plot":
        fig = px.scatter(
            filtered_df,
            x='publication_date',
            y='citations',
            color='citations',
            size='citations',
            hover_name='title',
            title='Citations by Publication Date'
        )
        st.plotly_chart(fig, use_container_width=True)

    elif viz_type == "Time Series":
        filtered_df['year'] = filtered_df['publication_date'].dt.year
        yearly_citations = filtered_df.groupby('year')['citations'].agg(['sum', 'mean']).reset_index()

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=yearly_citations['year'],
            y=yearly_citations['sum'],
            mode='lines+markers',
            name='Total Citations'
        ))
        fig.add_trace(go.Scatter(
            x=yearly_citations['year'],
            y=yearly_citations['mean'],
            mode='lines+markers',
            name='Average Citations'
        ))
        fig.update_layout(
            title='Citation Trends by Publication Year',
            xaxis_title='Publication Year',
            yaxis_title='Citations',
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
        )
        st.plotly_chart(fig, use_container_width=True)

    # Citation impact analysis
    st.subheader("Citation Impact Analysis")

    percentiles = [25, 50, 75, 90, 95, 99]
    citation_percentiles = np.percentile(filtered_df['citations'], percentiles)

    percentile_data = pd.DataFrame({
        'Percentile': [f"{p}th" for p in percentiles],
        'Citations': citation_percentiles
    })

    col1, col2 = st.columns([2, 3])

    with col1:
        st.write("Citation Percentiles")
        st.dataframe(percentile_data, use_container_width=True)

    with col2:
        ranges = [(0, 0), (1, 5), (6, 10), (11, 25), (26, 50), (51, 100), (101, float('inf'))]
        range_labels = ['0', '1-5', '6-10', '11-25', '26-50', '51-100', '100+']
        range_counts = [len(filtered_df[(filtered_df['citations'] >= r[0]) & (filtered_df['citations'] <= r[1])]) for r in ranges]

        range_df = pd.DataFrame({'Citation Range': range_labels, 'Number of Papers': range_counts})

        fig = px.bar(range_df, x='Citation Range', y='Number of Papers', title='Papers by Citation Range')
        st.plotly_chart(fig, use_container_width=True)

    # Top cited papers
    st.subheader("Top Cited Papers")
    top_papers = filtered_df.sort_values('citations', ascending=False).head(10)
    
    # Determine which columns to display
    display_cols = ['title', 'authors', 'publication_date', 'citations', 'doi']
    if 'journal' in top_papers.columns:
        display_cols.insert(3, 'journal')  # Insert journal after publication_date if available
    
    st.dataframe(
        top_papers[display_cols],
        use_container_width=True
    )
else:
    st.warning("No data matches the selected filters. Please adjust your filter criteria.")