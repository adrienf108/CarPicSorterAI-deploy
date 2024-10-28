import streamlit as st
from streamlit.runtime.scriptrunner import RerunException
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from PIL import Image
import io
import base64
import zipfile
from database import Database
from ai_model import AIModel
from image_utils import image_to_base64, cleanup_temp_files
import bcrypt
import hashlib
import numpy as np
import logging
import os
import math
import gc
from datetime import datetime, timedelta

# Configure logging to be minimal
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

# Set chunk size to 5MB for efficient memory usage
CHUNK_SIZE = 5 * 1024 * 1024

# Constants for cleanup
CLEANUP_DAYS_THRESHOLD = 30
CLEANUP_SIZE_THRESHOLD_MB = 1000

# Category and subcategory number mappings
CATEGORY_NUMBERS = {
    'Exterior': '01',
    'Interior': '02',
    'Engine': '03',
    'Undercarriage': '04',
    'Documents': '05',
    'Uncategorized': '99'
}

SUBCATEGORY_NUMBERS = {
    'Exterior': {
        '3/4 front view': '01',
        'Side profile': '02',
        '3/4 rear view': '03',
        'Rear view': '04',
        'Wheels': '05',
        'Details': '06',
        'Defects': '07'
    },
    'Interior': {
        'Full interior view': '01',
        'Dashboard': '02',
        'Front seats': '03',
        "Driver's seat": '04',
        'Rear seats': '05',
        'Steering wheel': '06',
        'Gear shift': '07',
        'Pedals and floor mats': '08',
        'Gauges/Instrument cluster': '09',
        'Details': '10',
        'Trunk/Boot': '11'
    },
    'Engine': {
        'Full view': '01',
        'Detail': '02'
    },
    'Undercarriage': {
        'Undercarriage': '01'
    },
    'Documents': {
        'Invoices/Receipts': '01',
        'Service book': '02',
        'Technical inspections/MOT certificates': '03'
    },
    'Uncategorized': {
        'Uncategorized': '99'
    }
}

# Initialize database and AI model (with lazy loading)
db = None
ai_model = None

def get_db():
    global db
    if db is None:
        db = Database()
    return db

def get_ai_model():
    global ai_model
    if ai_model is None:
        ai_model = AIModel()
    return ai_model

class User:
    def __init__(self, id, username, role):
        self.id = id
        self.username = username
        self.role = role

def calculate_image_hash(image):
    """Calculate a hash for the image to detect duplicates."""
    try:
        return hashlib.md5(image.tobytes()).hexdigest()
    finally:
        gc.collect()

def process_chunk(chunk, filename, total_chunks, chunk_number, user_id):
    """Process a single chunk of file data with memory optimization"""
    logger.info(f"Processing chunk {chunk_number}/{total_chunks} for {filename}")
    
    try:
        # Clean up old temporary files before processing
        cleanup_temp_files()
        
        # If this is the first chunk, create a new file
        mode = 'ab' if chunk_number > 1 else 'wb'
        temp_path = f"/tmp/{filename}.partial"
        
        with open(temp_path, mode) as f:
            f.write(chunk)
        
        # If this is the last chunk, process the complete file
        if chunk_number == total_chunks:
            with open(temp_path, 'rb') as f:
                file_data = f.read()
            
            # Clean up temporary file immediately after reading
            os.remove(temp_path)
            
            # Process the file based on its type
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                process_single_image(filename, file_data, user_id)
            elif filename.lower().endswith('.zip'):
                process_zip_file(filename, file_data, user_id)
            
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error processing chunk: {str(e)}")
        if os.path.exists(f"/tmp/{filename}.partial"):
            os.remove(f"/tmp/{filename}.partial")
        return False
    finally:
        gc.collect()

def process_single_image(filename, file_data, user_id):
    """Process a single image file with memory optimization"""
    try:
        with Image.open(io.BytesIO(file_data)) as img:
            img_hash = calculate_image_hash(img)
            
            # Check for duplicates
            if 'processed_hashes' not in st.session_state:
                st.session_state['processed_hashes'] = set()
                
            if img_hash in st.session_state['processed_hashes']:
                st.session_state['duplicates_count'] = st.session_state.get('duplicates_count', 0) + 1
                return
                
            st.session_state['processed_hashes'].add(img_hash)
            
            main_category, subcategory, confidence, token_usage, image_size = get_ai_model().predict(img)
            logger.info(f"AI Model prediction for {filename}: {main_category} - {subcategory} (Confidence: {confidence})")
            
            image_data = image_to_base64(img)
            get_db().save_image(filename, image_data, main_category, subcategory, user_id, float(confidence), token_usage, image_size)
            
            # Create a smaller copy for display
            display_image = img.copy()
            display_image.thumbnail((300, 300))
            
            if main_category == 'Uncategorized':
                st.image(display_image, caption=f"{filename}: Uncategorized (Confidence: {confidence:.2f})", use_column_width=True)
            else:
                st.image(display_image, caption=f"{filename}: {main_category} - {subcategory} (Confidence: {confidence:.2f})", use_column_width=True)
                
    except Exception as e:
        logger.error(f"Error processing image {filename}: {str(e)}")
        st.error(f"Error processing image {filename}: {str(e)}")
    finally:
        gc.collect()

def process_zip_file(filename, file_data, user_id):
    """Process a zip file containing images with memory optimization"""
    try:
        with zipfile.ZipFile(io.BytesIO(file_data)) as z:
            for filename in z.namelist():
                if filename.lower().endswith(('.png', '.jpg', '.jpeg')) and not filename.startswith('__MACOSX/'):
                    with z.open(filename) as file:
                        process_single_image(filename, file.read(), user_id)
                gc.collect()
    except Exception as e:
        logger.error(f"Error processing zip file {filename}: {str(e)}")
        st.error(f"Error processing zip file {filename}: {str(e)}")
    finally:
        gc.collect()

@st.cache_data(ttl=300)
def get_cached_images():
    """Cache image data for 5 minutes to reduce database load"""
    return get_db().get_all_images()

@st.cache_data(ttl=300)
def get_cached_statistics():
    """Cache statistics for 5 minutes to reduce database load"""
    return get_db().get_statistics()

def check_and_cleanup_uploads():
    """Check and cleanup old uploads if needed"""
    try:
        if 'last_cleanup' not in st.session_state:
            st.session_state['last_cleanup'] = datetime.now() - timedelta(days=1)  # Force first cleanup
            
        # Check if it's time for cleanup (once per day)
        if datetime.now() - st.session_state['last_cleanup'] > timedelta(days=1):
            deleted_count = get_db().clear_old_uploads(
                days_threshold=CLEANUP_DAYS_THRESHOLD,
                size_threshold_mb=CLEANUP_SIZE_THRESHOLD_MB
            )
            if deleted_count > 0:
                st.warning(f"Cleaned up {deleted_count} old or unused images to free up space.")
            st.session_state['last_cleanup'] = datetime.now()
            
            # Clear memory caches
            if 'image_cache' in st.session_state:
                del st.session_state['image_cache']
            if 'stats_cache' in st.session_state:
                del st.session_state['stats_cache']
            gc.collect()
            
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")

def upload_page():
    """Handle file uploads and image processing."""
    st.header("Upload Car Images")
    
    # Check and perform cleanup if needed
    check_and_cleanup_uploads()
    
    # Initialize or reset duplicates count for new upload session
    if 'upload_session_started' not in st.session_state:
        st.session_state['upload_session_started'] = True
        st.session_state['duplicates_count'] = 0
    
    # Display warning for duplicate images if any were found
    if st.session_state.get('duplicates_count', 0) > 0:
        st.warning(f"{st.session_state['duplicates_count']} duplicate images were skipped.")
    
    # Display storage status
    with st.expander("Storage Status"):
        try:
            with get_db().conn.cursor() as cur:
                cur.execute("SELECT COUNT(*), SUM(image_size) FROM images")
                count, total_size = cur.fetchone()
                if total_size:
                    total_size_mb = total_size / (1024 * 1024)
                    st.info(f"Current storage: {total_size_mb:.2f}MB used by {count} images")
                    if total_size_mb > CLEANUP_SIZE_THRESHOLD_MB * 0.8:  # 80% of threshold
                        st.warning("Storage usage is high. Old images may be automatically removed.")
        except Exception as e:
            logger.error(f"Error getting storage status: {str(e)}")
    
    uploaded_files = st.file_uploader(
        "Choose image files or a zip file",
        type=['png', 'jpg', 'jpeg', 'zip'],
        accept_multiple_files=True
    )
    
    if uploaded_files:
        progress_text = "Processing files..."
        progress_bar = st.progress(0)
        
        total_files = len(uploaded_files)
        for i, uploaded_file in enumerate(uploaded_files):
            file_data = uploaded_file.read()
            total_size = len(file_data)
            total_chunks = math.ceil(total_size / CHUNK_SIZE)
            
            for chunk_number in range(1, total_chunks + 1):
                start = (chunk_number - 1) * CHUNK_SIZE
                end = min(chunk_number * CHUNK_SIZE, total_size)
                chunk = file_data[start:end]
                
                process_chunk(
                    chunk,
                    uploaded_file.name,
                    total_chunks,
                    chunk_number,
                    st.session_state['user'].id
                )
            
            # Update progress
            progress = (i + 1) / total_files
            progress_bar.progress(progress)
            
        st.success("Upload complete!")
        # Reset upload session
        st.session_state['upload_session_started'] = False
        st.session_state['duplicates_count'] = 0
        
        # Force cleanup check after large uploads
        if total_files > 10:
            st.session_state['last_cleanup'] = datetime.now() - timedelta(days=1)

def login_page():
    """Handle user login and registration."""
    st.header("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Login"):
            user = get_db().get_user_by_username(username)
            if user and bcrypt.checkpw(password.encode('utf-8'), user[2].encode('utf-8')):
                st.session_state['user'] = User(user[0], user[1], user[3])
                st.success("Logged in successfully!")
                st.rerun()
            else:
                st.error("Invalid username or password")
    
    with col2:
        if st.button("Register"):
            if username and password:
                existing_user = get_db().get_user_by_username(username)
                if existing_user:
                    st.error("Username already exists")
                else:
                    user_count = len(get_db().get_all_users())
                    role = 'admin' if user_count == 0 else 'user'
                    user_id = get_db().create_user(username, password, role)
                    st.session_state['user'] = User(user_id, username, role)
                    st.success("Registered successfully!")
                    st.rerun()
            else:
                st.error("Please enter both username and password")

def user_management_page():
    """Handle user management for administrators."""
    st.header("User Management")
    
    users = get_db().get_all_users()
    for user in users:
        st.write(f"Username: {user['username']}, Role: {user['role']}")
        if user['role'] == 'user':
            if st.button(f"Promote {user['username']} to Admin"):
                get_db().update_user_role(user['id'], 'admin')
                st.success(f"{user['username']} promoted to Admin")
                st.rerun()

def main():
    """Main application entry point."""
    # Clean up any old temporary files and force garbage collection
    cleanup_temp_files()
    gc.collect()
    
    # Initialize session state for page navigation if not exists
    if 'page' not in st.session_state:
        st.session_state['page'] = 'Upload'

    # Check if user is logged in
    if 'user' not in st.session_state or not st.session_state['user']:
        login_page()
    else:
        st.title("AI-powered Car Image Categorization")
        
        # Sidebar for navigation
        st.sidebar.title("Navigation")
        pages = ["Upload", "Review", "Statistics"]
        if st.session_state['user'].role == 'admin':
            pages.append("User Management")
        
        selected_page = st.sidebar.selectbox("Go to", pages, index=pages.index(st.session_state['page']))
        
        # Update session state when page changes
        if selected_page != st.session_state['page']:
            st.session_state['page'] = selected_page
            st.rerun()

        # Display the selected page
        if st.session_state['page'] == "Upload":
            upload_page()
        elif st.session_state['page'] == "Review":
            review_page()
        elif st.session_state['page'] == "Statistics":
            statistics_page()
        elif st.session_state['page'] == "User Management" and st.session_state['user'].role == 'admin':
            user_management_page()
        else:
            st.warning("You don't have permission to access this page.")

        if st.sidebar.button("Logout"):
            st.session_state['user'] = None
            st.session_state['page'] = 'Upload'
            st.rerun()

if __name__ == "__main__":
    main()
