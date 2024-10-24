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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

def main():
    st.set_page_config(page_title="AI-powered Car Image Categorization", layout="wide")
    st.title("AI-powered Car Image Categorization")

    # Check if user is logged in
    if 'user' not in st.session_state or not st.session_state['user']:
        login_page()
    else:
        # Sidebar for navigation
        st.sidebar.title("Navigation")
        page = st.sidebar.radio("Go to", ["Upload", "Review", "Statistics", "User Management"])

        if page == "Upload":
            upload_page()
        elif page == "Review":
            review_page()
        elif page == "Statistics":
            statistics_page()
        elif page == "User Management" and st.session_state['user'].role == 'admin':
            user_management_page()
        else:
            st.warning("You don't have permission to access this page.")

        if st.sidebar.button("Logout"):
            st.session_state['user'] = None
            st.rerun()

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
        all_images = []
        image_hashes = set()
        duplicates_count = 0

        for uploaded_file in uploaded_files:
            if uploaded_file.type == "application/zip":
                with zipfile.ZipFile(uploaded_file) as z:
                    for filename in z.namelist():
                        if filename.lower().endswith(('.png', '.jpg', '.jpeg')) and not filename.startswith('__MACOSX/'):
                            with z.open(filename) as file:
                                try:
                                    img_data = file.read()
                                    img = Image.open(io.BytesIO(img_data))
                                    img_hash = calculate_image_hash(img)
                                    if img_hash not in image_hashes:
                                        image_hashes.add(img_hash)
                                        all_images.append((filename, img))
                                    else:
                                        duplicates_count += 1
                                except Exception as e:
                                    st.warning(f"Skipped file {filename}: {str(e)}")
            else:
                img = Image.open(uploaded_file)
                img_hash = calculate_image_hash(img)
                if img_hash not in image_hashes:
                    image_hashes.add(img_hash)
                    all_images.append((uploaded_file.name, img))
                else:
                    duplicates_count += 1

        total_files = len(all_images)
        progress_bar = st.progress(0)
        status_text = st.empty()

        for i, (filename, image) in enumerate(all_images):
            upload_progress = (i + 0.5) / total_files
            progress_bar.progress(upload_progress)
            status_text.text(f"Uploading and processing {i+1}/{total_files} images")

            main_category, subcategory, confidence = ai_model.predict(image)
            logger.info(f"AI Model prediction for {filename}: {main_category} - {subcategory} (Confidence: {confidence})")

            # Save the original image without resizing
            image_data = image_to_base64(image)

            # Save to database with the predicted categories
            db.save_image(filename, image_data, main_category, subcategory, st.session_state['user'].id, float(confidence))
            logger.info(f"Saved image {filename} to database with categories: {main_category} - {subcategory}")

            # Display a resized version of the image in the UI
            display_image = image.copy()
            display_image.thumbnail((300, 300))

            if main_category == 'Uncategorized':
                st.image(display_image, caption=f"{filename}: Uncategorized (Confidence: {confidence:.2f})", use_column_width=True)
            else:
                st.image(display_image, caption=f"{filename}: {main_category} - {subcategory} (Confidence: {confidence:.2f})", use_column_width=True)

            process_progress = (i + 1) / total_files
            progress_bar.progress(process_progress)
            status_text.text(f"Processed {i+1}/{total_files} images")

        # Store the duplicates count in the session state for the next upload
        st.session_state['duplicates_count'] = duplicates_count

        st.success(f"Successfully uploaded and processed {total_files} images!")
        if duplicates_count > 0:
            st.info(f"Skipped {duplicates_count} duplicate image(s) during this upload.")

def review_page():
    st.header("Review and Correct Categorizations")
    
    images = db.get_all_images()
    logger.info(f"Retrieved {len(images)} images for review")
    
    if not images:
        st.warning("No images to review.")
        return

    # Pagination
    items_per_page = 9
    n_pages = len(images) // items_per_page + (1 if len(images) % items_per_page > 0 else 0)
    
    # Use session state to keep track of the current page
    if 'review_page_number' not in st.session_state:
        st.session_state['review_page_number'] = 0

    page_number = st.session_state['review_page_number']
    start_idx = page_number * items_per_page
    end_idx = start_idx + items_per_page
    page_images = images[start_idx:end_idx]

    # Display images in a grid
    cols = st.columns(3)
    for i, image in enumerate(page_images):
        with cols[i % 3]:
            st.image(base64.b64decode(image['image_data']), use_column_width=True)
            logger.info(f"Displaying image {image['filename']} with categories: {image['category']} - {image['subcategory']}")
            st.write(f"Current: {image['category']} - {image['subcategory']}")
            
            # Use a unique key for each set of buttons
            button_key = f"buttons_{image['id']}"
            
            if button_key not in st.session_state:
                st.session_state[button_key] = {"state": "main", "selected_category": None}
            
            if st.session_state[button_key]["state"] == "main":
                st.write("Select Main Category:")
                for category in ai_model.model.main_categories + ['Uncategorized']:
                    if st.button(category, key=f"{button_key}_{category}"):
                        st.session_state[button_key]["state"] = "sub"
                        st.session_state[button_key]["selected_category"] = category
                        st.rerun()
            
            elif st.session_state[button_key]["state"] == "sub":
                selected_category = st.session_state[button_key]["selected_category"]
                if selected_category != 'Uncategorized':
                    st.write(f"Select Subcategory for {selected_category}:")
                    for subcategory in ai_model.model.subcategories[selected_category]:
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

    # Navigation buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Previous Page", disabled=(page_number == 0)):
            st.session_state['review_page_number'] = max(0, page_number - 1)
            st.rerun()
    with col2:
        if st.button("Next Page", disabled=(page_number == n_pages - 1)):
            st.session_state['review_page_number'] = min(n_pages - 1, page_number + 1)
            st.rerun()

def statistics_page():
    st.header("AI Performance Analytics Dashboard")
    
    stats = db.get_statistics()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Images", stats['total_images'])
    with col2:
        st.metric("Overall Accuracy", f"{stats['accuracy']:.2f}%")
    with col3:
        st.metric("Unique Categories", len(stats['category_distribution']))
    
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

if __name__ == "__main__":
    main()
