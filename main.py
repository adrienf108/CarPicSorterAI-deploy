import streamlit as st
from streamlit.runtime.scriptrunner import RerunException
import pandas as pd
import plotly.express as px
from PIL import Image
import io
import base64
import zipfile
from database import Database
from ai_model import AIModel
from image_utils import resize_image, image_to_base64
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import bcrypt
import math

# Initialize database and AI model
db = Database()
ai_model = AIModel()

# Initialize Flask-Login
login_manager = LoginManager()

class User(UserMixin):
    def __init__(self, id, username, role):
        self.id = id
        self.username = username
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    user = db.get_user_by_username(user_id)
    if user:
        return User(user[0], user[1], user[3])
    return None

def main():
    st.title("AI-powered Car Image Categorization")

    # Check if user is logged in
    if not st.session_state.get('user'):
        login_page()
    else:
        # Sidebar for navigation
        page = st.sidebar.selectbox("Choose a page", ["Upload", "Review", "Statistics", "User Management"])

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
            try:
                st.rerun()
            except RerunException:
                pass

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
                try:
                    st.rerun()
                except RerunException:
                    pass
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
                    try:
                        st.rerun()
                    except RerunException:
                        pass
            else:
                st.error("Please enter both username and password")

def upload_page():
    st.header("Upload Car Images")
    uploaded_files = st.file_uploader("Choose images or zip files to upload", type=["jpg", "jpeg", "png", "zip"], accept_multiple_files=True)

    if uploaded_files:
        all_images = []
        for uploaded_file in uploaded_files:
            if uploaded_file.type == "application/zip":
                with zipfile.ZipFile(uploaded_file) as z:
                    for filename in z.namelist():
                        if filename.lower().endswith(('.png', '.jpg', '.jpeg')) and not filename.startswith('__MACOSX/'):
                            with z.open(filename) as file:
                                try:
                                    img_data = file.read()
                                    img = Image.open(io.BytesIO(img_data))
                                    all_images.append((filename, img))
                                except Exception as e:
                                    st.warning(f"Skipped file {filename}: {str(e)}")
            else:
                all_images.append((uploaded_file.name, Image.open(uploaded_file)))

        total_files = len(all_images)
        progress_bar = st.progress(0)
        status_text = st.empty()

        for i, (filename, image) in enumerate(all_images):
            # Update progress for upload
            upload_progress = (i + 0.5) / total_files
            progress_bar.progress(upload_progress)
            status_text.text(f"Uploading and processing {i+1}/{total_files} images")

            # Predict category and subcategory using full image
            main_category, subcategory, confidence = ai_model.predict(image)

            # Resize image for display purposes only
            display_image = resize_image(image, size=(300, 300))
            image_data = image_to_base64(display_image)

            # Save to database
            db.save_image(filename, image_data, main_category, subcategory, st.session_state['user'].id, float(confidence))

            if main_category == 'Uncategorized':
                st.image(display_image, caption=f"{filename}: Uncategorized (Confidence: {confidence:.2f})", use_column_width=True)
            else:
                st.image(display_image, caption=f"{filename}: {main_category} - {subcategory} (Confidence: {confidence:.2f})", use_column_width=True)

            # Update progress for processing
            process_progress = (i + 1) / total_files
            progress_bar.progress(process_progress)
            status_text.text(f"Processed {i+1}/{total_files} images")

        st.success(f"Successfully uploaded and processed {total_files} images!")

def review_page():
    st.header("Review and Correct Categorizations")
    
    # Get all images from the database
    images = db.get_all_images()
    
    # Pagination
    images_per_page = 12
    total_pages = math.ceil(len(images) / images_per_page)
    
    # Initialize current_page in session state if not present
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 1
    
    # Navigation buttons
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Previous Page") and st.session_state.current_page > 1:
            st.session_state.current_page -= 1
    with col2:
        st.write(f"Page {st.session_state.current_page} of {total_pages}")
    with col3:
        if st.button("Next Page") and st.session_state.current_page < total_pages:
            st.session_state.current_page += 1
    
    # Display images in a grid
    start_index = (st.session_state.current_page - 1) * images_per_page
    end_index = start_index + images_per_page
    page_images = images[start_index:end_index]
    
    # Create a grid layout
    cols = st.columns(3)
    selected_images = []
    
    for i, image in enumerate(page_images):
        with cols[i % 3]:
            st.image(base64.b64decode(image['image_data']), use_column_width=True)
            st.write(f"Current: {image['category']} - {image['subcategory']}")
            if st.checkbox(f"Select image {i+1}"):
                selected_images.append(image)
    
    # Batch categorization
    if selected_images:
        st.subheader("Batch Categorization")
        
        # Main category selection
        st.write("Select Main Category:")
        main_category = None
        main_category_cols = st.columns(3)
        for i, category in enumerate(ai_model.model.main_categories + ['Uncategorized']):
            with main_category_cols[i % 3]:
                if st.button(category, key=f"main_{category}"):
                    main_category = category
        
        # Subcategory selection
        if main_category and main_category != 'Uncategorized':
            st.write("Select Subcategory:")
            subcategory = None
            subcategory_cols = st.columns(3)
            for i, sub in enumerate(ai_model.model.subcategories[main_category]):
                with subcategory_cols[i % 3]:
                    if st.button(sub, key=f"sub_{sub}"):
                        subcategory = sub
        else:
            subcategory = 'Uncategorized'
        
        # Update button
        if main_category and subcategory:
            if st.button("Update Selected Images"):
                for image in selected_images:
                    db.update_categorization(image['id'], main_category, subcategory)
                    ai_model.learn_from_manual_categorization(Image.open(io.BytesIO(base64.b64decode(image['image_data']))), main_category, subcategory)
                st.success(f"Updated {len(selected_images)} images")
                
                # Auto-navigation: Move to the next page
                if st.session_state.current_page < total_pages:
                    st.session_state.current_page += 1
                else:
                    st.session_state.current_page = 1
                
                st.rerun()

def statistics_page():
    st.header("AI Performance Analytics Dashboard")
    
    # Get statistics from the database
    stats = db.get_statistics()
    
    # Display overall statistics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Images", stats['total_images'])
    with col2:
        st.metric("Overall Accuracy", f"{stats['accuracy']:.2f}%")
    with col3:
        st.metric("Unique Categories", len(stats['category_distribution']))
    
    # Display category distribution
    st.subheader("Category Distribution")
    category_df = pd.DataFrame(stats['category_distribution'])
    fig = px.pie(category_df, values='count', names='category', title='Category Distribution')
    st.plotly_chart(fig)
    
    # Display accuracy over time
    st.subheader("Accuracy Over Time")
    accuracy_df = pd.DataFrame(stats['accuracy_over_time'])
    fig = px.line(accuracy_df, x='date', y='accuracy', title='AI Model Accuracy Over Time')
    st.plotly_chart(fig)
    
    # Display confusion matrix
    st.subheader("Confusion Matrix")
    confusion_matrix = stats['confusion_matrix']
    fig = px.imshow(confusion_matrix, 
                    labels=dict(x="Predicted Category", y="True Category", color="Count"),
                    x=ai_model.model.main_categories,
                    y=ai_model.model.main_categories)
    fig.update_layout(title='Confusion Matrix')
    st.plotly_chart(fig)
    
    # Display top misclassifications
    st.subheader("Top Misclassifications")
    misclassifications = stats['top_misclassifications']
    misclass_df = pd.DataFrame(misclassifications)
    st.table(misclass_df)
    
    # Display confidence distribution
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
                try:
                    st.rerun()
                except RerunException:
                    pass

if __name__ == "__main__":
    main()