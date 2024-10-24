import streamlit as st
import os
import bcrypt
import pandas as pd
from database import Database
from ai_model import AIModel
from image_utils import resize_image, image_to_base64
from PIL import Image
import io
import zipfile
import logging
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database and AI model
db = Database()
ai_model = AIModel()

def init_session_state():
    """Initialize session state variables."""
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'total_tokens' not in st.session_state:
        st.session_state.total_tokens = 0
    if 'processed_images' not in st.session_state:
        st.session_state.processed_images = 0

def login_user(username, password):
    """Authenticate user and set session state."""
    user = db.get_user_by_username(username)
    if user and bcrypt.checkpw(password.encode('utf-8'), user[2].encode('utf-8')):
        st.session_state.user = {'id': user[0], 'username': user[1], 'role': user[3]}
        return True
    return False

def register_user(username, password):
    """Register a new user."""
    try:
        user_id = db.create_user(username, password)
        if user_id:
            st.success("Registration successful! Please log in.")
            return True
    except Exception as e:
        st.error(f"Registration failed: {str(e)}")
    return False

def is_admin():
    """Check if current user is an admin."""
    return st.session_state.user and st.session_state.user['role'] == 'admin'

def login_page():
    """Display login/register page."""
    st.title("Car Image Categorization System")
    
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login"):
            if login_user(username, password):
                st.success("Logged in successfully!")
                st.rerun()
            else:
                st.error("Invalid username or password")
    
    with tab2:
        new_username = st.text_input("Username", key="register_username")
        new_password = st.text_input("Password", type="password", key="register_password")
        if st.button("Register"):
            register_user(new_username, new_password)

def process_image(image_file):
    """Process a single image file."""
    try:
        # Read and resize image
        image_bytes = image_file.read()
        image = Image.open(io.BytesIO(image_bytes))
        resized_image = resize_image(image)
        
        # Get AI predictions
        main_category, subcategory, confidence = ai_model.predict(resized_image)
        
        # Save to database
        image_data = image_to_base64(resized_image)
        db.save_image(
            image_file.name,
            image_data,
            main_category,
            subcategory,
            st.session_state.user['id'],
            confidence
        )
        
        return True
    except Exception as e:
        st.error(f"Error processing image {image_file.name}: {str(e)}")
        return False

def upload_page():
    """Display upload page."""
    st.title("Upload Car Images")
    
    uploaded_files = st.file_uploader(
        "Choose image files",
        type=['png', 'jpg', 'jpeg'],
        accept_multiple_files=True
    )
    
    if uploaded_files:
        progress_bar = st.progress(0)
        total_files = len(uploaded_files)
        processed_files = 0
        duplicates_count = 0
        
        for uploaded_file in uploaded_files:
            if process_image(uploaded_file):
                processed_files += 1
            else:
                duplicates_count += 1
            progress_bar.progress(processed_files / total_files)
        
        st.success(f"Successfully uploaded and processed {total_files} images!")
        if duplicates_count > 0:
            st.info(f"Skipped {duplicates_count} duplicate image(s) during this upload.")
        
        # Display token usage statistics
        if 'total_tokens' in st.session_state and 'processed_images' in st.session_state:
            total_tokens = st.session_state.total_tokens
            processed_images = st.session_state.processed_images
            avg_tokens = total_tokens / processed_images if processed_images > 0 else 0
            
            st.write("---")
            st.subheader("Token Usage Statistics")
            st.write(f"Total tokens used: {total_tokens:,}")
            st.write(f"Images processed: {processed_images}")
            st.write(f"Average tokens per image: {avg_tokens:,.1f}")
            
            # Reset counters for next batch
            st.session_state.total_tokens = 0
            st.session_state.processed_images = 0

def review_page():
    """Display review page."""
    st.title("Review Images")
    
    # Get all images from database
    images = db.get_all_images()
    logger.info(f"Retrieved {len(images)} images for review")
    
    if not images:
        st.info("No images to review.")
        return
    
    # Display images in a grid
    cols = st.columns(4)
    for idx, image in enumerate(images):
        col = cols[idx % 4]
        with col:
            st.image(
                f"data:image/png;base64,{image['image_data']}",
                caption=f"{image['filename']}\n{image['category']} - {image['subcategory']}",
                use_column_width=True
            )
            logger.info(f"Displaying image {image['filename']} with categories: {image['category']} - {image['subcategory']}")

def statistics_page():
    """Display statistics page."""
    st.title("AI Performance Statistics")
    
    stats = db.get_statistics()
    
    # Overall Statistics
    st.subheader("Overall Statistics")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Images", stats['total_images'])
    with col2:
        st.metric("Overall Accuracy", f"{stats['accuracy']:.1f}%")
    
    # Category Distribution
    st.subheader("Category Distribution")
    category_df = pd.DataFrame(stats['category_distribution'])
    if not category_df.empty:
        fig = px.bar(category_df, x='category', y='count')
        st.plotly_chart(fig)
    
    # Accuracy Over Time
    st.subheader("Accuracy Over Time")
    accuracy_df = pd.DataFrame(stats['accuracy_over_time'])
    if not accuracy_df.empty:
        fig = px.line(accuracy_df, x='date', y='accuracy')
        st.plotly_chart(fig)
    
    # Confusion Matrix
    st.subheader("Confusion Matrix")
    categories = stats['confusion_categories']
    confusion_matrix = stats['confusion_matrix']
    
    if categories and confusion_matrix:
        fig = go.Figure(data=go.Heatmap(
            z=confusion_matrix,
            x=categories,
            y=categories,
            colorscale='Viridis'
        ))
        fig.update_layout(
            title='Confusion Matrix',
            xaxis_title='Predicted Category',
            yaxis_title='Actual Category'
        )
        st.plotly_chart(fig)
    
    # Top Misclassifications
    st.subheader("Top Misclassifications")
    if stats['top_misclassifications']:
        st.table(stats['top_misclassifications'])
    
    # Confidence Distribution
    st.subheader("Confidence Distribution")
    confidence_df = pd.DataFrame(stats['confidence_distribution'])
    if not confidence_df.empty:
        fig = px.histogram(confidence_df, x='confidence', nbins=20)
        st.plotly_chart(fig)

def admin_page():
    """Display admin page."""
    st.title("Admin Panel")
    
    users = db.get_all_users()
    
    st.subheader("User Management")
    for user in users:
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.write(f"Username: {user['username']}")
        with col2:
            st.write(f"Role: {user['role']}")
        with col3:
            if user['role'] == 'user':
                if st.button(f"Promote to Admin", key=f"promote_{user['id']}"):
                    db.update_user_role(user['id'], 'admin')
                    st.success(f"Promoted {user['username']} to admin")
                    st.rerun()

def main():
    """Main application."""
    st.set_page_config(page_title="Car Image Categorization", layout="wide")
    init_session_state()
    
    if not st.session_state.user:
        login_page()
    else:
        # Sidebar navigation
        st.sidebar.title(f"Welcome, {st.session_state.user['username']}!")
        
        pages = {
            "Upload Images": upload_page,
            "Review Images": review_page,
            "Statistics": statistics_page
        }
        
        if is_admin():
            pages["Admin Panel"] = admin_page
        
        st.sidebar.write("---")
        selected_page = st.sidebar.radio("Navigation", list(pages.keys()))
        
        # Logout button
        if st.sidebar.button("Logout"):
            st.session_state.user = None
            st.rerun()
        
        # Display selected page
        pages[selected_page]()

if __name__ == "__main__":
    main()
