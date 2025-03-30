import pandas as pd
import streamlit as st
import os

# Constants
MAX_INITIAL_BOOKS = 5
MAX_DESCRIPTION_LENGTH = 200

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

CSV_PATH = "books.csv"

# Function to load and process data
@st.cache_data
def load_data():
    # Check if file exists
    if not os.path.exists(CSV_PATH):
        st.error(f"Database file not found at {CSV_PATH}. Please make sure the file exists.")
        st.stop()
    
    df = pd.read_csv(CSV_PATH)
    # Clean the data
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].fillna('')
        else:
            df[col] = df[col].fillna(0)
    return df

# Load data
try:
    books_df = load_data()
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

# Filter method - store in session state
if 'filter_method' not in st.session_state:
    st.session_state.filter_method = None

# Filter method
filter_method = st.sidebar.radio(
    "Search method",
    [None, "By Author", "By Category", "By Title", "Get Recommendations"],
    format_func=lambda x: "Select a method..." if x is None else x
)

# Update session state
st.session_state.filter_method = filter_method

# Main Content Area
if filter_method is None:
    # Landing page content
    st.markdown("""
    ## Welcome to the Book Recommendation System!
    
    This application helps you discover books based on your preferences. Here's how you can use it:
    
    ### Search Methods:
    
    **By Author**: Browse books written by a specific author
    
    **By Category**: Find books in categories like Fiction, Science, History, etc.
    
    **By Title**: Search for specific book titles
    
    **Get Recommendations**: Discover books similar to ones you already enjoy!
    
    ### How to Get Started:
    
    1. Select a search method from the sidebar on the left
    2. Use the filters to narrow down your selection
    3. Explore book details and recommendations
    
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
            st.markdown(f"### {row[title_column]}")
            st.markdown(f"**Category:** {row[category_column]}")
            # Truncate long descriptions
            description = row[description_column][:MAX_DESCRIPTION_LENGTH]
            if len(row[description_column]) > MAX_DESCRIPTION_LENGTH:
                description += "..."
            st.markdown(f"**Description:** {description}")
            st.divider()
    else:
        st.write("No books found for this author.")

# By Category Section
elif filter_method == "By Category":
    selected_category = st.sidebar.selectbox("Select Category", unique_categories)
    filtered_books = books_df[books_df[category_column].str.contains(selected_category, na=False)]
    
    st.header(f"Books in {selected_category} category")
    if not filtered_books.empty:
        total_books = len(filtered_books)
        for i, (_, row) in enumerate(filtered_books.iterrows()):
            if i >= MAX_INITIAL_BOOKS:
                st.info(f"Showing {MAX_INITIAL_BOOKS} out of {total_books} books in {selected_category} category.")
                break
            st.markdown(f"### {row[title_column]}")
            st.markdown(f"**Author:** {row[author_column]}")
            # Truncate long descriptions
            description = row[description_column][:MAX_DESCRIPTION_LENGTH]
            if len(row[description_column]) > MAX_DESCRIPTION_LENGTH:
                description += "..."
            st.markdown(f"**Description:** {description}")
            st.divider()
    else:
        st.write("No books found in this category.")

# By Title Section
elif filter_method == "By Title":
    user_input = st.sidebar.text_input("Enter a book title")
    if user_input:
        matched_titles = books_df[books_df[title_column].str.contains(user_input, case=False)]
        if not matched_titles.empty:
            selected_title = st.sidebar.selectbox("Select the exact title", 
                                         matched_titles[title_column].tolist())
            book_details = books_df[books_df[title_column] == selected_title].iloc[0]
            
            st.header(f"Details for '{selected_title}'")
            st.markdown(f"**Author:** {book_details[author_column]}")
            st.markdown(f"**Category:** {book_details[category_column]}")
            st.markdown(f"**Description:** {book_details[description_column]}")
        else:
            st.warning(f"No books found containing '{user_input}'")

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
        
        # Create a scoring system
        books_df['score'] = 0
        
        # Add points for matching categories
        for category in book_categories:
            category = category.strip()
            books_df.loc[books_df[category_column].str.contains(category, na=False), 'score'] += 1
        
        # Add points for same author
        books_df.loc[books_df[author_column] == book_author, 'score'] += 2
        
        # Get recommendations
        recommendations = books_df[books_df[title_column] != title].copy()
        recommendations = recommendations.nlargest(num_rec, 'score')
        recommendations['match_score'] = recommendations['score'] / (len(book_categories) + 2)
        
        return recommendations
    
    if book_selection_method == "By Title":
        user_input = st.sidebar.text_input("Enter a book title")
        if user_input:
            matched_titles = books_df[books_df[title_column].str.contains(user_input, case=False)]
            if not matched_titles.empty:
                selected_title = st.sidebar.selectbox("Select the exact title", 
                                             matched_titles[title_column].tolist())
            else:
                st.warning(f"No books found containing '{user_input}'")
                st.stop()
        else:
            st.info("Enter a book title to get recommendations.")
            st.stop()
    else:  # By Author then Title
        selected_author = st.sidebar.selectbox("Select Author", unique_authors)
        author_books = books_df[books_df[author_column] == selected_author][title_column].tolist()
        selected_title = st.sidebar.selectbox("Select a book", author_books)
    
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
                st.markdown(f"### {original_book[title_column]}")
                st.markdown(f"**Author:** {original_book[author_column]}")
                st.markdown(f"**Category:** {original_book[category_column]}")
                st.markdown(f"**Description:** {original_book[description_column]}")
            
            # Display recommendations
            for _, row in recommendations.iterrows():
                col1, col2 = st.columns([1, 4])
                
                with col1:
                    match_percentage = row['match_score'] * 100
                    st.markdown(f"**Match Score:**")
                    st.progress(row['match_score'])
                    st.markdown(f"**{match_percentage:.1f}%**")
                
                with col2:
                    st.markdown(f"### {row[title_column]}")
                    st.markdown(f"**Author:** {row[author_column]}")
                    st.markdown(f"**Category:** {row[category_column]}")
                    # Truncate long descriptions
                    description = row[description_column][:MAX_DESCRIPTION_LENGTH]
                    if len(row[description_column]) > MAX_DESCRIPTION_LENGTH:
                        description += "..."
                    st.markdown(f"**Description:** {description}")
                
                st.divider()

# Add additional information in sidebar
st.sidebar.markdown("---")
st.sidebar.header("About This App")
st.sidebar.info("""
This app helps you discover new books based on:
- Authors you enjoy
- Categories you're interested in
- Books with similar themes

The recommendation system uses a simple scoring method:
- +1 point for each matching category
- +2 points for the same author
""")