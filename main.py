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

def clear_previous_session():
    """Clear all temporary files and session data from previous upload sessions"""
    try:
        # Clear session state for upload tracking
        if 'processed_hashes' in st.session_state:
            del st.session_state['processed_hashes']
        if 'duplicates_count' in st.session_state:
            st.session_state['duplicates_count'] = 0
        
        # Remove all temporary files
        cleanup_temp_files(max_age_minutes=0)  # Clear all temp files regardless of age
        
        # Remove any partial uploads
        temp_dir = "/tmp"
        if os.path.exists(temp_dir):
            for filename in os.listdir(temp_dir):
                if filename.endswith('.partial'):
                    try:
                        os.remove(os.path.join(temp_dir, filename))
                    except OSError:
                        continue
        
        # Force garbage collection
        gc.collect()
        
    except Exception as e:
        logger.error(f"Error clearing previous session: {str(e)}")

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
    
    # Initialize or reset session for new upload
    if 'upload_session_started' not in st.session_state:
        st.session_state['upload_session_started'] = True
        st.session_state['duplicates_count'] = 0
        # Clear previous session data and temporary files
        clear_previous_session()
    
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

def review_page():
    """Handle image review and categorization."""
    st.header("Review and Correct Categorizations")
    
    images = get_cached_images()
    logger.info(f"Retrieved {len(images)} images for review")
    
    if not images:
        st.warning("No images to review.")
        return

    cols = st.columns(3)
    for i, image in enumerate(images):
        with cols[i % 3]:
            with st.container():
                st.image(base64.b64decode(image['image_data']), use_column_width=True)
                logger.info(f"Displaying image {image['filename']} with categories: {image['category']} - {image['subcategory']}")
                st.write(f"Current: {image['category']} - {image['subcategory']}")
                
                button_key = f"buttons_{image['id']}"
                
                if button_key not in st.session_state:
                    st.session_state[button_key] = {"state": "main", "selected_category": None}
                
                if st.session_state[button_key]["state"] == "main":
                    st.write("Select Main Category:")
                    cols_categories = st.columns(3)
                    for idx, category in enumerate(get_ai_model().model.main_categories + ['Uncategorized']):
                        with cols_categories[idx % 3]:
                            if st.button(category, key=f"{button_key}_{category}"):
                                st.session_state[button_key]["state"] = "sub"
                                st.session_state[button_key]["selected_category"] = category
                                st.rerun()
                
                elif st.session_state[button_key]["state"] == "sub":
                    selected_category = st.session_state[button_key]["selected_category"]
                    if selected_category != 'Uncategorized':
                        st.write(f"Select Subcategory for {selected_category}:")
                        cols_subcategories = st.columns(3)
                        subcategories = get_ai_model().model.subcategories[selected_category]
                        for idx, subcategory in enumerate(subcategories):
                            with cols_subcategories[idx % 3]:
                                if st.button(subcategory, key=f"{button_key}_{subcategory}"):
                                    get_db().update_categorization(image['id'], selected_category, subcategory)
                                    get_ai_model().learn_from_manual_categorization(
                                        Image.open(io.BytesIO(base64.b64decode(image['image_data']))),
                                        selected_category,
                                        subcategory
                                    )
                                    st.session_state[button_key]["state"] = "main"
                                    st.rerun()
                    else:
                        if st.button("Confirm Uncategorized", key=f"{button_key}_uncategorized"):
                            get_db().update_categorization(image['id'], 'Uncategorized', 'Uncategorized')
                            st.session_state[button_key]["state"] = "main"
                            st.rerun()
                    
                    if st.button("Back", key=f"{button_key}_back"):
                        st.session_state[button_key]["state"] = "main"
                        st.rerun()

    st.write("---")
    st.subheader("Download All Images")
    
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        file_counter = 1
        
        sorted_images = sorted(images, key=lambda x: (
            CATEGORY_NUMBERS.get(x['category'], '99'),
            SUBCATEGORY_NUMBERS.get(x['category'], {}).get(x['subcategory'], '99')
        ))
        
        for image in sorted_images:
            cat_num = CATEGORY_NUMBERS.get(image['category'], '99')
            subcat_num = SUBCATEGORY_NUMBERS.get(image['category'], {}).get(image['subcategory'], '99')
            
            _, ext = os.path.splitext(image['filename'])
            if not ext:
                ext = '.jpg'
            
            filename = f"{cat_num}{subcat_num}_{file_counter:04d}{ext}"
            
            img_bytes = base64.b64decode(image['image_data'])
            zf.writestr(filename, img_bytes)
            
            file_counter += 1
            gc.collect()
    
    zip_buffer.seek(0)
    
    st.download_button(
        label="Download All Images (Organized by Category)",
        data=zip_buffer,
        file_name="all_car_images.zip",
        mime="application/zip",
        key="download_all_images_button"
    )

def statistics_page():
    """Display AI performance analytics dashboard."""
    st.header("AI Performance Analytics Dashboard")
    
    stats = get_cached_statistics()
    token_stats = stats['token_usage']
    
    # Performance Metrics
    st.subheader("Performance Metrics")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Images", stats['total_images'])
    with col2:
        st.metric("Overall Accuracy", f"{stats['accuracy']:.2f}%")
    with col3:
        st.metric("Total Tokens Used", f"{token_stats['total_tokens']:,}")
    with col4:
        st.metric("Avg. Tokens/Image", f"{token_stats['avg_tokens_per_image']:.1f}")
    
    # Token Usage Over Time
    if token_stats['usage_over_time']:
        token_usage_df = pd.DataFrame(token_stats['usage_over_time'])
        
        # Daily Token Usage
        fig = px.line(token_usage_df, x='date', y='tokens',
                     title='Daily Token Usage',
                     labels={'tokens': 'Tokens Used', 'date': 'Date'})
        st.plotly_chart(fig, use_container_width=True)
        
        # Images Processed Over Time
        fig = px.line(token_usage_df, x='date', y='images',
                     title='Daily Images Processed',
                     labels={'images': 'Images Processed', 'date': 'Date'})
        st.plotly_chart(fig, use_container_width=True)
        
        # Average Token Usage per Image Over Time
        token_usage_df['avg_tokens_per_image'] = token_usage_df['tokens'] / token_usage_df['images']
        fig = px.line(token_usage_df, x='date', y='avg_tokens_per_image',
                     title='Average Tokens per Image Over Time',
                     labels={'avg_tokens_per_image': 'Avg. Tokens/Image', 'date': 'Date'})
        st.plotly_chart(fig, use_container_width=True)
        
        # Clear dataframes to free memory
        del token_usage_df
        gc.collect()
    else:
        st.info("No token usage data available yet. Upload some images to see the statistics.")
    
    # Category Distribution
    st.subheader("Category Distribution")
    category_df = pd.DataFrame(stats['category_distribution'])
    fig = px.pie(category_df, values='count', names='category',
                 title='Category Distribution')
    st.plotly_chart(fig, use_container_width=True)
    del category_df
    gc.collect()
    
    # Accuracy Over Time
    st.subheader("Accuracy Over Time")
    accuracy_df = pd.DataFrame(stats['accuracy_over_time'])
    fig = px.line(accuracy_df, x='date', y='accuracy',
                  title='AI Model Accuracy Over Time')
    st.plotly_chart(fig, use_container_width=True)
    del accuracy_df
    gc.collect()
    
    # Confusion Matrix
    st.subheader("Confusion Matrix")
    confusion_matrix = np.array(stats['confusion_matrix'])
    categories = stats['confusion_categories']
    
    fig = go.Figure(data=go.Heatmap(
        z=confusion_matrix,
        x=categories,
        y=categories,
        hoverongaps=False,
        colorscale='Viridis'
    ))
    fig.update_layout(
        title='Confusion Matrix',
        xaxis_title='Predicted Category',
        yaxis_title='True Category'
    )
    st.plotly_chart(fig, use_container_width=True)
    del confusion_matrix
    gc.collect()
    
    # Top Misclassifications
    st.subheader("Top Misclassifications")
    misclass_df = pd.DataFrame(stats['top_misclassifications'])
    st.table(misclass_df)
    del misclass_df
    gc.collect()
    
    # Confidence Distribution
    st.subheader("Confidence Distribution")
    confidence_df = pd.DataFrame(stats['confidence_distribution'])
    fig = px.histogram(confidence_df, x='confidence', nbins=20,
                      title='Distribution of AI Confidence Scores')
    st.plotly_chart(fig, use_container_width=True)
    del confidence_df
    gc.collect()

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
