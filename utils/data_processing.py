import pandas as pd
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process_openalex_data(data):
    """
    Process raw OpenAlex API response data into a structured pandas DataFrame.
    
    Args:
        data (dict): Raw response from OpenAlex API, typically containing a 'results' key with a list of works.
    
    Returns:
        pd.DataFrame: Processed data with relevant fields, or an empty DataFrame if processing fails.
    """
    processed_data = []
    
    # Check if data is valid and contains results
    if not isinstance(data, dict) or 'results' not in data:
        logger.warning("Invalid OpenAlex data format or no results found.")
        return pd.DataFrame()
    
    for item in data.get('results', []):
        try:
            # Handle title safely
            title = item.get('title', '')
            if title is not None:
                title = title.replace('\n', ' ').strip()
            else:
                title = 'Untitled'

            # Handle authors (list of authorship dictionaries)
            authors_list = []
            for authorship in item.get('authorships', []):
                author_name = authorship.get('author', {}).get('display_name', '')
                if author_name:
                    authors_list.append(author_name)
            authors = ', '.join(authors_list) if authors_list else 'Unknown Author'

            # Extract country codes from institutions (assuming first author's institutions)
            country_codes = []
            if item.get('authorships'):
                for institution in item.get('authorships', [{}])[0].get('institutions', []):
                    country_code = institution.get('country_code', '')
                    if country_code:
                        country_codes.append(country_code)
            country_codes_str = ','.join(country_codes) if country_codes else ''

            # Extract source/journal name
            source = item.get('primary_location', {}).get('source', {}).get('display_name', '')

            # Build the processed item dictionary
            processed_item = {
                'title': title,
                'authors': authors,
                'year': item.get('publication_year', ''),
                'publication_date': item.get('publication_date', ''),
                'source': source if source else item.get('host_venue', {}).get('display_name', ''),
                'institutions': ','.join([inst.get('display_name', '') for inst in item.get('authorships', [{}])[0].get('institutions', [])]) if item.get('authorships') else '',
                'country_codes': country_codes_str,
                'citations': item.get('cited_by_count', 0),
                'cited_by': item.get('cited_by_count', 0),  # Alias for consistency with app.py
                'related_count': len(item.get('related_works', [])),
                'fwci': item.get('fwci', 0.0),  # Field-weighted citation impact, if available
                'citation_percentile': item.get('citation_percentile', 0.0),  # Placeholder
                'h_index_contribution': item.get('cited_by_count', 0),  # Simplified for individual contribution
                'type': item.get('type', ''),
                'topic': ','.join([concept.get('display_name', '') for concept in item.get('concepts', [])[:1]]) if item.get('concepts') else '',
                'subfield': ','.join([concept.get('display_name', '') for concept in item.get('concepts', [])[1:2]]) if len(item.get('concepts', [])) > 1 else '',
                'field': ','.join([concept.get('display_name', '') for concept in item.get('concepts', [])[2:3]]) if len(item.get('concepts', [])) > 2 else '',
                'domain': item.get('primary_topic', {}).get('domain', {}).get('display_name', '') if item.get('primary_topic') else '',
                'open_access_status': 'Yes' if item.get('open_access', {}).get('is_oa', False) else 'No',
                'doi': item.get('doi', '').replace('https://doi.org/', '') if item.get('doi') else '',
                'abstract': item.get('abstract_inverted_index', '') or ''  # Simplified, may need custom processing
            }
            processed_data.append(processed_item)
        except Exception as e:
            logger.error(f"Error processing OpenAlex item: {str(e)} - Item data: {item}")
    
    # Return DataFrame, or empty DataFrame if no valid data
    return pd.DataFrame(processed_data) if processed_data else pd.DataFrame()

def calculate_metrics(df):
    """
    Calculate impact metrics from a processed DataFrame.
    
    Args:
        df (pd.DataFrame): DataFrame containing publication data with 'citations' column.
    
    Returns:
        dict: Metrics including total publications, total citations, average citations, and h-index.
    """
    if df.empty:
        return {
            "total_publications": 0,
            "total_citations": 0,
            "avg_citations": 0,
            "h_index": 0
        }
    
    total_pubs = len(df)
    total_cites = df['citations'].sum()
    avg_cites = total_cites / total_pubs if total_pubs > 0 else 0
    
    # Calculate h-index
    sorted_cites = df['citations'].sort_values(ascending=False).tolist()
    h_index = 0
    for i, cite in enumerate(sorted_cites):
        if cite >= i + 1:
            h_index = i + 1
        else:
            break
    
    return {
        "total_publications": total_pubs,
        "total_citations": total_cites,
        "avg_citations": avg_cites,
        "h_index": h_index
    }
