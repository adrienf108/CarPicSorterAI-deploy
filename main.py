import streamlit as st
from streamlit.runtime.scriptrunner import RerunException
import pandas as pd
from PIL import Image
import io
import base64
from database import Database
from ai_model import AIModel
from image_utils import resize_image, image_to_base64
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import bcrypt

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
    uploaded_files = st.file_uploader("Choose images to upload", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

    if uploaded_files:
        total_files = len(uploaded_files)
        progress_bar = st.progress(0)
        status_text = st.empty()

        for i, file in enumerate(uploaded_files):
            # Update progress for upload
            upload_progress = (i + 0.5) / total_files
            progress_bar.progress(upload_progress)
            status_text.text(f"Uploading and processing {i+1}/{total_files} images")

            image = Image.open(file)
            
            # Predict category and subcategory using full image
            main_category, subcategory, confidence = ai_model.predict(image)
            
            # Resize image for display purposes only
            display_image = resize_image(image, size=(300, 300))
            image_data = image_to_base64(display_image)
            
            # Save to database
            db.save_image(file.name, image_data, main_category, subcategory, st.session_state['user'].id)
            
            if main_category == 'Uncategorized':
                st.image(display_image, caption=f"{file.name}: Uncategorized (Confidence: {confidence:.2f})", use_column_width=True)
            else:
                st.image(display_image, caption=f"{file.name}: {main_category} - {subcategory} (Confidence: {confidence:.2f})", use_column_width=True)
            
            # Update progress for processing
            process_progress = (i + 1) / total_files
            progress_bar.progress(process_progress)
            status_text.text(f"Processed {i+1}/{total_files} images")

        st.success(f"Successfully uploaded and processed {total_files} images!")

def review_page():
    st.header("Review and Correct Categorizations")
    
    # Get all images from the database
    images = db.get_all_images()
    
    # Display images in a grid
    cols = st.columns(3)
    for idx, image in enumerate(images):
        with cols[idx % 3]:
            st.image(base64.b64decode(image['image_data']), use_column_width=True)
            st.write(f"Current: {image['category']} - {image['subcategory']}")
            
            # Correction form
            with st.form(f"correct_form_{idx}"):
                new_category = st.selectbox("New Category", ai_model.model.main_categories + ['Uncategorized'], key=f"cat_{idx}")
                if new_category != 'Uncategorized':
                    new_subcategory = st.selectbox("New Subcategory", ai_model.model.subcategories[new_category], key=f"subcat_{idx}")
                else:
                    new_subcategory = 'Uncategorized'
                if st.form_submit_button("Correct"):
                    db.update_categorization(image['id'], new_category, new_subcategory)
                    # Learn from manual categorization
                    ai_model.learn_from_manual_categorization(Image.open(io.BytesIO(base64.b64decode(image['image_data']))), new_category, new_subcategory)
                    st.success("Categorization updated and model updated!")
            
            # Download button
            if st.button(f"Download Image {idx}"):
                st.download_button(
                    label="Download Image",
                    data=base64.b64decode(image['image_data']),
                    file_name=image['filename'],
                    mime="image/png"
                )

def statistics_page():
    st.header("Categorization Statistics")
    
    # Get statistics from the database
    stats = db.get_statistics()
    
    # Display statistics
    st.write(f"Total images: {stats['total_images']}")
    st.write(f"Accuracy: {stats['accuracy']:.2f}%")
    
    # Display category distribution
    st.subheader("Category Distribution")
    category_df = pd.DataFrame(stats['category_distribution'])
    st.bar_chart(category_df.set_index('category'))

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
