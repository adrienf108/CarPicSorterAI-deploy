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
from image_utils import image_to_base64
import bcrypt
import hashlib
import numpy as np
import logging
import os
import math

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set chunk size to 5MB
CHUNK_SIZE = 5 * 1024 * 1024

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

# Initialize database and AI model
db = Database()
ai_model = AIModel()

class User:
    def __init__(self, id, username, role):
        self.id = id
        self.username = username
        self.role = role

def calculate_image_hash(image):
    """Calculate a hash for the image to detect duplicates."""
    return hashlib.md5(image.tobytes()).hexdigest()

def process_chunk(chunk, filename, total_chunks, chunk_number, user_id):
    """Process a single chunk of file data"""
    logger.info(f"Processing chunk {chunk_number}/{total_chunks} for {filename}")
    
    try:
        # If this is the first chunk, create a new file
        mode = 'ab' if chunk_number > 1 else 'wb'
        temp_path = f"/tmp/{filename}.partial"
        
        with open(temp_path, mode) as f:
            f.write(chunk)
        
        # If this is the last chunk, process the complete file
        if chunk_number == total_chunks:
            with open(temp_path, 'rb') as f:
                file_data = f.read()
            
            # Clean up temporary file
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

def process_single_image(filename, file_data, user_id):
    """Process a single image file"""
    try:
        img = Image.open(io.BytesIO(file_data))
        img_hash = calculate_image_hash(img)
        
        # Check for duplicates
        if 'processed_hashes' not in st.session_state:
            st.session_state['processed_hashes'] = set()
            
        if img_hash in st.session_state['processed_hashes']:
            st.session_state['duplicates_count'] = st.session_state.get('duplicates_count', 0) + 1
            return
            
        st.session_state['processed_hashes'].add(img_hash)
        
        main_category, subcategory, confidence, token_usage, image_size = ai_model.predict(img)
        logger.info(f"AI Model prediction for {filename}: {main_category} - {subcategory} (Confidence: {confidence})")
        
        image_data = image_to_base64(img)
        db.save_image(filename, image_data, main_category, subcategory, user_id, float(confidence), token_usage, image_size)
        
        display_image = img.copy()
        display_image.thumbnail((300, 300))
        
        if main_category == 'Uncategorized':
            st.image(display_image, caption=f"{filename}: Uncategorized (Confidence: {confidence:.2f})", use_column_width=True)
        else:
            st.image(display_image, caption=f"{filename}: {main_category} - {subcategory} (Confidence: {confidence:.2f})", use_column_width=True)
            
    except Exception as e:
        logger.error(f"Error processing image {filename}: {str(e)}")
        st.error(f"Error processing image {filename}: {str(e)}")

def process_zip_file(filename, file_data, user_id):
    """Process a zip file containing images"""
    try:
        with zipfile.ZipFile(io.BytesIO(file_data)) as z:
            for filename in z.namelist():
                if filename.lower().endswith(('.png', '.jpg', '.jpeg')) and not filename.startswith('__MACOSX/'):
                    with z.open(filename) as file:
                        process_single_image(filename, file.read(), user_id)
    except Exception as e:
        logger.error(f"Error processing zip file {filename}: {str(e)}")
        st.error(f"Error processing zip file {filename}: {str(e)}")

def login_page():
    st.header("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Login"):
            user = db.get_user_by_username(username)
            if user and bcrypt.checkpw(password.encode('utf-8'), user[2].encode('utf-8')):
                st.session_state['user'] = User(user[0], user[1], user[3])
                st.success("Logged in successfully!")
                st.rerun()
            else:
                st.error("Invalid username or password")
    
    with col2:
        if st.button("Register"):
            if username and password:
                existing_user = db.get_user_by_username(username)
                if existing_user:
                    st.error("Username already exists")
                else:
                    user_count = len(db.get_all_users())
                    role = 'admin' if user_count == 0 else 'user'
                    user_id = db.create_user(username, password, role)
                    st.session_state['user'] = User(user_id, username, role)
                    st.success("Registered successfully!")
                    st.rerun()
            else:
                st.error("Please enter both username and password")

def upload_page():
    st.header("Upload Car Images")
    
    # Reset duplicates_count at the beginning of the function
    st.session_state['duplicates_count'] = 0
    
    # Display warning message if there were duplicate images skipped in the previous upload
    if 'duplicates_count' in st.session_state and st.session_state['duplicates_count'] > 0:
        st.warning(f"Skipped {st.session_state['duplicates_count']} duplicate image(s) in the previous upload.")
    
    uploaded_files = st.file_uploader("Choose images or zip files to upload", type=["jpg", "jpeg", "png", "zip"], accept_multiple_files=True)
    
    if uploaded_files:
        progress_text = st.empty()
        progress_bar = st.progress(0)
        total_files = len(uploaded_files)
        
        for i, uploaded_file in enumerate(uploaded_files):
            try:
                file_size = len(uploaded_file.getvalue())
                total_chunks = math.ceil(file_size / CHUNK_SIZE)
                
                progress_text.text(f"Processing file {i+1}/{total_files}: {uploaded_file.name}")
                
                # Process file in chunks
                uploaded_file.seek(0)
                for chunk_number in range(1, total_chunks + 1):
                    chunk = uploaded_file.read(CHUNK_SIZE)
                    is_complete = process_chunk(chunk, uploaded_file.name, total_chunks, chunk_number, st.session_state['user'].id)
                    
                    # Update progress
                    chunk_progress = (chunk_number / total_chunks)
                    total_progress = ((i + chunk_progress) / total_files)
                    progress_bar.progress(total_progress)
                    
                    if is_complete:
                        logger.info(f"Completed processing {uploaded_file.name}")
                
            except Exception as e:
                logger.error(f"Error processing file {uploaded_file.name}: {str(e)}")
                st.error(f"Error processing file {uploaded_file.name}: {str(e)}")
                
        progress_text.text("Upload complete!")
        progress_bar.progress(1.0)
        st.success(f"Successfully processed {total_files} files!")

def review_page():
    st.header("Review and Correct Categorizations")
    
    images = db.get_all_images()
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
                    for idx, category in enumerate(ai_model.model.main_categories + ['Uncategorized']):
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
                        subcategories = ai_model.model.subcategories[selected_category]
                        for idx, subcategory in enumerate(subcategories):
                            with cols_subcategories[idx % 3]:
                                if st.button(subcategory, key=f"{button_key}_{subcategory}"):
                                    db.update_categorization(image['id'], selected_category, subcategory)
                                    ai_model.learn_from_manual_categorization(Image.open(io.BytesIO(base64.b64decode(image['image_data']))), selected_category, subcategory)
                                    st.session_state[button_key]["state"] = "main"
                                    st.rerun()
                    else:
                        if st.button("Confirm Uncategorized", key=f"{button_key}_uncategorized"):
                            db.update_categorization(image['id'], 'Uncategorized', 'Uncategorized')
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
    
    zip_buffer.seek(0)
    
    st.download_button(
        label="Download All Images (Organized by Category)",
        data=zip_buffer,
        file_name="all_car_images.zip",
        mime="application/zip",
        key="download_all_images_button"
    )

def statistics_page():
    st.header("AI Performance Analytics Dashboard")
    
    stats = db.get_statistics()
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
    st.subheader("Token Usage Over Time")
    if token_stats['usage_over_time']:
        token_usage_df = pd.DataFrame(token_stats['usage_over_time'])
        fig = px.line(token_usage_df, x='date', y='tokens', 
                     title='Daily Token Usage',
                     labels={'tokens': 'Tokens Used', 'date': 'Date'})
        st.plotly_chart(fig)

        # Images Processed Over Time
        fig = px.line(token_usage_df, x='date', y='images',
                     title='Daily Images Processed',
                     labels={'images': 'Images Processed', 'date': 'Date'})
        st.plotly_chart(fig)

        # Average Token Usage per Image Over Time
        token_usage_df['avg_tokens_per_image'] = token_usage_df['tokens'] / token_usage_df['images']
        fig = px.line(token_usage_df, x='date', y='avg_tokens_per_image',
                     title='Average Tokens per Image Over Time',
                     labels={'avg_tokens_per_image': 'Avg. Tokens/Image', 'date': 'Date'})
        st.plotly_chart(fig)
    else:
        st.info("No token usage data available yet. Upload some images to see the statistics.")
    
    # Original Statistics
    st.subheader("Category Distribution")
    category_df = pd.DataFrame(stats['category_distribution'])
    fig = px.pie(category_df, values='count', names='category', title='Category Distribution')
    st.plotly_chart(fig)
    
    st.subheader("Accuracy Over Time")
    accuracy_df = pd.DataFrame(stats['accuracy_over_time'])
    fig = px.line(accuracy_df, x='date', y='accuracy', title='AI Model Accuracy Over Time')
    st.plotly_chart(fig)
    
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
    st.plotly_chart(fig)
    
    st.subheader("Top Misclassifications")
    misclassifications = stats['top_misclassifications']
    misclass_df = pd.DataFrame(misclassifications)
    st.table(misclass_df)
    
    st.subheader("Confidence Distribution")
    confidence_df = pd.DataFrame(stats['confidence_distribution'])
    fig = px.histogram(confidence_df, x='confidence', nbins=20, title='Distribution of AI Confidence Scores')
    st.plotly_chart(fig)

def user_management_page():
    st.header("User Management")
    
    users = db.get_all_users()
    for user in users:
        st.write(f"Username: {user['username']}, Role: {user['role']}")
        if user['role'] == 'user':
            if st.button(f"Promote {user['username']} to Admin"):
                db.update_user_role(user['id'], 'admin')
                st.success(f"{user['username']} promoted to Admin")
                st.rerun()

def main():
    st.set_page_config(page_title="AI-powered Car Image Categorization", layout="wide")
    
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
