import pandas as pd
import streamlit as st
import requests
import os
import time
import json

# Constants
MAX_INITIAL_BOOKS = 5
MAX_DESCRIPTION_LENGTH = 200
MAX_API_RESULTS = 40  # Maximum number of results to fetch from API

# Set page configuration
st.set_page_config(
    page_title="Book Recommendation System",
    layout="wide",
    initial_sidebar_state="expanded"
)

# App title and description
st.title("📚 Book Recommendation System")
st.markdown("""
Discover your next favorite book based on titles, authors, and categories you enjoy!
""")

# Function to load data from Open Library API
@st.cache_data(ttl=3600)  # Cache for 1 hour
def search_books(query, max_results=MAX_API_RESULTS, search_type=None):
    """
    Search for books in the Open Library API.
    
    Parameters:
    - query: Search term
    - max_results: Maximum number of results to return
    - search_type: Can be None, 'author', 'title', or 'subject'
    """
    base_url = "https://openlibrary.org/search.json"
    
    # Start with empty results
    all_items = []
    
    params = {
        'q': query,
        'limit': max_results,
        'fields': 'key,title,author_name,subject,first_publish_year,publisher,isbn,cover_i,first_sentence,language'
    }
    
    # Add search type parameter if specified
    if search_type == 'author':
        params['author'] = query
    elif search_type == 'title':
        params['title'] = query
    elif search_type == 'subject':
        params['subject'] = query
    
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()  # Raise exception for HTTP errors
        data = response.json()
        
        # Check if there are items
        if 'docs' in data and len(data['docs']) > 0:
            all_items = data['docs']
        
        # Avoid hitting API rate limits
        time.sleep(0.5)
        
    except Exception as e:
        st.error(f"API Error: {e}")
    
    # Limit to max_results
    return all_items[:max_results]

# Function to get book details from Open Library
@st.cache_data(ttl=3600)
def get_book_details(work_key):
    if not work_key:
        return {}
        
    url = f"https://openlibrary.org{work_key}.json"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.warning(f"Could not fetch detailed information: {e}")
        return {}

# Function to create a dataframe from API results
@st.cache_data
def create_books_dataframe(items):
    books = []
    
    for item in items:
        # Extract relevant fields with fallbacks for missing data
        book = {
            'title': item.get('title', 'Unknown Title'),
            'authors': ', '.join(item.get('author_name', ['Unknown Author'])),
            'categories': ', '.join(item.get('subject', ['Uncategorized']))[:100],
            'description': item.get('first_sentence', ['No description available'])[0] if isinstance(item.get('first_sentence'), list) else 'No description available',
            'publishedDate': str(item.get('first_publish_year', 'Unknown')),
            'thumbnail': f"https://covers.openlibrary.org/b/id/{item.get('cover_i')}-M.jpg" if item.get('cover_i') else '',
            'work_key': item.get('key', '') if item.get('key', '').startswith('/works/') else ''
        }
        books.append(book)
    
    df = pd.DataFrame(books)
    return df

# Function to get initial book collection
@st.cache_data
def get_initial_book_collection():
    # Search for popular books across different genres
    popular_queries = [
        "bestseller fiction", 
        "popular science", 
        "classic literature",
        "history",
        "biography"
    ]
    
    all_books = []
    for query in popular_queries:
        items = search_books(query, max_results=10)  # 10 books per category
        all_books.extend(items)
    
    return create_books_dataframe(all_books)

# Load initial book collection
try:
    with st.spinner("Loading books from Open Library..."):
        books_df = get_initial_book_collection()
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

# Define column names
title_column = 'title'
author_column = 'authors'
category_column = 'categories'
description_column = 'description'

# Extract unique values
unique_authors = sorted(books_df[author_column].dropna().unique())
unique_categories = sorted(books_df[category_column].str.split(',').explode().str.strip().dropna().unique())

# Basic data exploration
with st.expander("Dataset Information"):
    st.dataframe(books_df.head())
    st.write(f"Dataset contains {books_df.shape[0]} books and {books_df.shape[1]} features.")
    st.write(f"Number of unique authors: {len(unique_authors)}")
    st.write(f"Number of unique categories: {len(unique_categories)}")

# Sidebar for filters
st.sidebar.header("Find Books By:")

# Search options
st.sidebar.markdown("### Search Open Library")
search_query = st.sidebar.text_input("Search for books", "")

# At the beginning of your app, after initializing other session state variables
if 'search_results_displayed' not in st.session_state:
    st.session_state.search_results_displayed = False

# When displaying search results, set the flag
if st.sidebar.button("Search"):
    if search_query:
        with st.spinner("Searching Open Library..."):
            search_results = search_books(search_query)
            if search_results:
                books_df = create_books_dataframe(search_results)
                st.success(f"Found {len(books_df)} books matching '{search_query}'")
                
                # Set the flag to indicate search results are displayed
                st.session_state.search_results_displayed = True
                
                # Update unique values after search
                unique_authors = sorted(books_df[author_column].dropna().unique())
                unique_categories = sorted(books_df[category_column].str.split(',').explode().str.strip().dropna().unique())
                
                # Automatically show search results
                st.header(f"Search results for '{search_query}'")
                total_books = len(books_df)
                
                # Show all books or limit to MAX_INITIAL_BOOKS with a message
                display_limit = min(total_books, 20)  # Show up to 20 books
                
                for i, (_, row) in enumerate(books_df.iterrows()):
                    if i >= display_limit:
                        st.info(f"Showing {display_limit} out of {total_books} books. Use the search methods in the sidebar to narrow down results.")
                        break
                    
                    col1, col2 = st.columns([1, 3])
                    
                    with col1:
                        if row.get('thumbnail'):
                            st.image(row['thumbnail'], width=130)
                        else:
                            st.markdown("📚")  # Book emoji as placeholder
                    
                    with col2:
                        st.markdown(f"### {row[title_column]}")
                        st.markdown(f"**Author:** {row[author_column]}")
                        st.markdown(f"**Category:** {row[category_column]}")
                        # Truncate long descriptions
                        description = row[description_column][:MAX_DESCRIPTION_LENGTH]
                        if len(row[description_column]) > MAX_DESCRIPTION_LENGTH:
                            description += "..."
                        st.markdown(f"**Description:** {description}")
                        st.markdown(f"**Published:** {row['publishedDate']}")
                    
                    st.divider()
                
                # Set filter_method to None to avoid showing conflicting content
                filter_method = None
                st.session_state.filter_method = None
            else:
                st.warning(f"No books found for '{search_query}'")

# Filter method - store in session state
if 'filter_method' not in st.session_state:
    st.session_state.filter_method = None

# Filter method - now with only By Author and Get Recommendations
filter_method = st.sidebar.radio(
    "Search method",
    [None, "By Author", "Get Recommendations"],
    format_func=lambda x: "Select a method..." if x is None else x
)

# Update session state
st.session_state.filter_method = filter_method

# Main Content Area
if filter_method is None and not st.session_state.search_results_displayed:
    # Landing page content
    st.markdown("""
    ## Welcome to the Book Recommendation System!
    
    This application helps you discover books based on your preferences. Here's how you can use it:
    
    ### Search Methods:
    
    **Search Open Library**: Find books by keyword in the sidebar
    
    **By Author**: Browse books written by a specific author
    
    **Get Recommendations**: Discover books similar to ones you already enjoy!
    
    ### How to Get Started:
    
    1. Search for books using the search box in the sidebar
    2. Select a search method to browse the results
    3. Use the filters to narrow down your selection
    4. Explore book details and recommendations
    
    ### About the Recommendation System:
    
    Our recommendation system uses a simple but effective approach:
    - Matching categories between books (+1 point per match)
    - Books by the same author receive higher priority (+2 points)
    
    The higher the match percentage, the more likely you'll enjoy the recommended book!
    """)
    
    # Display some statistics or featured books
    with st.expander("Book Collection Statistics"):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Books", books_df.shape[0])
        with col2:
            st.metric("Unique Authors", len(unique_authors))
        with col3:
            st.metric("Categories", len(unique_categories))

# By Author Section
elif filter_method == "By Author":
    selected_author = st.sidebar.selectbox("Select Author", unique_authors)
    filtered_books = books_df[books_df[author_column] == selected_author]
    
    st.header(f"Books by {selected_author}")
    if not filtered_books.empty:
        total_books = len(filtered_books)
        for i, (_, row) in enumerate(filtered_books.iterrows()):
            if i >= MAX_INITIAL_BOOKS:
                st.info(f"Showing {MAX_INITIAL_BOOKS} out of {total_books} books by {selected_author}.")
                break
                
            col1, col2 = st.columns([1, 3])
            
            with col1:
                if row.get('thumbnail'):
                    st.image(row['thumbnail'], width=130)
                else:
                    st.markdown("📚")  # Book emoji as placeholder
            
            with col2:
                st.markdown(f"### {row[title_column]}")
                st.markdown(f"**Category:** {row[category_column]}")
                # Truncate long descriptions
                description = row[description_column][:MAX_DESCRIPTION_LENGTH]
                if len(row[description_column]) > MAX_DESCRIPTION_LENGTH:
                    description += "..."
                st.markdown(f"**Description:** {description}")
                st.markdown(f"**Published:** {row['publishedDate']}")
            
            st.divider()
    else:
        st.write("No books found for this author.")
        
        # Offer better author search options
        st.markdown("### Search for this author")
        search_method = st.radio(
            "How would you like to search?", 
            ["By Author Name", "By Author + 'author'", "Custom Search"]
        )
        
        if st.button(f"Search Open Library for books by {selected_author}"):
            with st.spinner(f"Searching for books by {selected_author}..."):
                # Modify the search query based on selection
                if search_method == "By Author Name":
                    search_query = selected_author
                elif search_method == "By Author + 'author'":
                    search_query = f"{selected_author} author"
                else:  # Custom Search
                    search_query = st.text_input("Enter custom search", f"{selected_author} books")
                    
                search_results = search_books(selected_author, search_type='author')
                if search_results:
                    new_books = create_books_dataframe(search_results)
                    
                    # Filter to only include books where the author name appears
                    author_parts = selected_author.lower().split()
                    filtered_new_books = new_books[
                        new_books[author_column].str.lower().apply(
                            lambda x: all(part in x.lower() for part in author_parts)
                        )
                    ]
                    
                    if not filtered_new_books.empty:
                        books_df = pd.concat([books_df, filtered_new_books]).drop_duplicates(subset=[title_column])
                        st.success(f"Found {len(filtered_new_books)} books by {selected_author}")
                        
                        # Show the found books immediately
                        for _, row in filtered_new_books.iterrows():
                            col1, col2 = st.columns([1, 3])
                            
                            with col1:
                                if row.get('thumbnail'):
                                    st.image(row['thumbnail'], width=130)
                                else:
                                    st.markdown("📚")  # Book emoji as placeholder
                            
                            with col2:
                                st.markdown(f"### {row[title_column]}")
                                st.markdown(f"**Category:** {row[category_column]}")
                                # Truncate long descriptions
                                description = row[description_column][:MAX_DESCRIPTION_LENGTH]
                                if len(row[description_column]) > MAX_DESCRIPTION_LENGTH:
                                    description += "..."
                                st.markdown(f"**Description:** {description}")
                                st.markdown(f"**Published:** {row['publishedDate']}")
                            
                            st.divider()
                        
                        # Update unique values after search
                        unique_authors = sorted(books_df[author_column].dropna().unique())
                        unique_categories = sorted(books_df[category_column].str.split(',').explode().str.strip().dropna().unique())
                    else:
                        st.warning(f"Found books, but none appear to be by {selected_author}")
                        
                        # Offer to show all results anyway
                        if st.button("Show all search results anyway"):
                            books_df = pd.concat([books_df, new_books]).drop_duplicates(subset=[title_column])
                            st.success(f"Added {len(new_books)} books to the collection")
                else:
                    st.error(f"No books found using the search term: {search_query}")

# Recommendation Section
else:  # Get Recommendations
    st.sidebar.markdown("### Find Similar Books")
    
    # Book selection method
    book_selection_method = st.sidebar.radio(
        "How would you like to select a book?",
        ["By Title", "By Author then Title"]
    )
    
    def get_book_recommendations(title, num_rec=5):
        # Get the selected book's details
        book = books_df[books_df[title_column] == title].iloc[0]
        book_author = book[author_column]
        book_categories = book[category_column].split(',')
        
        # Create a scoring system - make a copy to avoid modifying the original
        temp_df = books_df.copy()
        temp_df['score'] = 0
        
        # Add points for matching categories
        for category in book_categories:
            category = category.strip()
            temp_df.loc[temp_df[category_column].str.contains(category, na=False), 'score'] += 1
        
        # Add points for same author
        temp_df.loc[temp_df[author_column] == book_author, 'score'] += 2
        
        # Get recommendations
        recommendations = temp_df[temp_df[title_column] != title].copy()
        recommendations = recommendations.nlargest(num_rec, 'score')
        
        # Calculate match score based on maximum possible score
        max_possible_score = len(book_categories) + 2  # categories + author
        recommendations['match_score'] = recommendations['score'] / max_possible_score
        
        return recommendations
    
    if book_selection_method == "By Title":
        user_input = st.sidebar.text_input("Enter a book title")
        if user_input:
            # First try to find in existing dataframe
            matched_titles = books_df[books_df[title_column].str.contains(user_input, case=False)]
            
            # If not found in dataframe, automatically search the API
            if matched_titles.empty:
                with st.spinner(f"Searching Open Library for '{user_input}'..."):
                    search_results = search_books(user_input)
                    if search_results:
                        new_books = create_books_dataframe(search_results)
                        books_df = pd.concat([books_df, new_books]).drop_duplicates(subset=[title_column])
                        st.success(f"Found {len(new_books)} books matching '{user_input}'")
                        # Update unique values after search
                        unique_authors = sorted(books_df[author_column].dropna().unique())
                        unique_categories = sorted(books_df[category_column].str.split(',').explode().str.strip().dropna().unique())
                        # Try matching titles again
                        matched_titles = books_df[books_df[title_column].str.contains(user_input, case=False)]
            
            # Now check if we have matches
            if not matched_titles.empty:
                selected_title = st.sidebar.selectbox("Select the exact title", 
                                             matched_titles[title_column].tolist())
            else:
                st.error(f"No books found for '{user_input}' even after searching Open Library.")
                st.stop()
        else:
            st.info("Enter a book title to get recommendations.")
            st.stop()
    else:  # By Author then Title
        selected_author = st.sidebar.selectbox("Select Author", unique_authors)
        
        # Check if author has books
        author_books = books_df[books_df[author_column] == selected_author][title_column].tolist()
        
        # If author has no books, automatically search for them
        if not author_books:
            with st.spinner(f"Finding books by {selected_author}..."):
                search_results = search_books(selected_author, search_type='author')
                if search_results:
                    new_books = create_books_dataframe(search_results)
                    # Filter to include only books by this author
                    author_parts = selected_author.lower().split()
                    filtered_new_books = new_books[
                        new_books[author_column].str.lower().apply(
                            lambda x: all(part in x.lower() for part in author_parts)
                        )
                    ]
                    
                    if not filtered_new_books.empty:
                        books_df = pd.concat([books_df, filtered_new_books]).drop_duplicates(subset=[title_column])
                        st.success(f"Found {len(filtered_new_books)} books by {selected_author}")
                        # Update author books list
                        author_books = books_df[books_df[author_column] == selected_author][title_column].tolist()
                        # Update unique values after search
                        unique_authors = sorted(books_df[author_column].dropna().unique())
                        unique_categories = sorted(books_df[category_column].str.split(',').explode().str.strip().dropna().unique())
        
        # Now check if we have books for this author
        if author_books:
            selected_title = st.sidebar.selectbox("Select a book", author_books)
        else:
            st.error(f"No books found by {selected_author} even after searching Open Library.")
            st.stop()
    
    # Number of recommendations
    num_recommendations = st.sidebar.slider("Number of recommendations", 1, 20, 5)
    
    # Get and display recommendations
    if 'selected_title' in locals():
        with st.spinner("Finding similar books..."):
            recommendations = get_book_recommendations(selected_title, num_recommendations)
            
            st.header(f"Books similar to '{selected_title}'")
            st.markdown("*Based on matching categories and authors*")
            
            # Display original book details
            original_book = books_df[books_df[title_column] == selected_title].iloc[0]
            with st.expander("Selected Book Details", expanded=True):
                col1, col2 = st.columns([1, 3])
                
                with col1:
                    if original_book.get('thumbnail'):
                        st.image(original_book['thumbnail'], width=150)
                    else:
                        st.markdown("📚")  # Book emoji as placeholder
                
                with col2:
                    st.markdown(f"### {original_book[title_column]}")
                    st.markdown(f"**Author:** {original_book[author_column]}")
                    st.markdown(f"**Category:** {original_book[category_column]}")
                    st.markdown(f"**Description:** {original_book[description_column]}")
                    st.markdown(f"**Published:** {original_book['publishedDate']}")
            
            # Display recommendations
            if not recommendations.empty:
                for _, row in recommendations.iterrows():
                    col1, col2, col3 = st.columns([1, 1, 3])
                    
                    with col1:
                        if row.get('thumbnail'):
                            st.image(row['thumbnail'], width=100)
                        else:
                            st.markdown("📚")  # Book emoji as placeholder
                    
                    with col2:
                        match_percentage = row['match_score'] * 100
                        st.markdown(f"**Match Score:**")
                        st.progress(row['match_score'])
                        st.markdown(f"**{match_percentage:.1f}%**")
                    
                    with col3:
                        st.markdown(f"### {row[title_column]}")
                        st.markdown(f"**Author:** {row[author_column]}")
                        st.markdown(f"**Category:** {row[category_column]}")
                        # Truncate long descriptions
                        description = row[description_column][:MAX_DESCRIPTION_LENGTH]
                        if len(row[description_column]) > MAX_DESCRIPTION_LENGTH:
                            description += "..."
                        st.markdown(f"**Description:** {description}")
                        st.markdown(f"**Published:** {row['publishedDate']}")
                    
                    st.divider()
            else:
                st.warning("No similar books found. This might be because the selected book has unique categories or the author doesn't have similar works in our database.")

# Add additional information in sidebar
st.sidebar.markdown("---")
st.sidebar.header("About This App")
st.sidebar.info("""
This app helps you discover new books based on:
- Authors you enjoy
- Books with similar themes and categories

The recommendation system uses a simple scoring method:
- +1 point for each matching category
- +2 points for the same author

Data provided by Open Library API.
""")