import os
import streamlit as st
from database import Database
from ai_model import AIModel
import bcrypt
from PIL import Image
import io
import zipfile
from image_utils import resize_image, image_to_base64

# Limit the number of threads used by Streamlit
os.environ['STREAMLIT_SERVER_NUM_WORKERS'] = '1'
os.environ['STREAMLIT_SERVER_MAX_UPLOAD_SIZE'] = '1000'

# Initialize database and AI model
db = Database()
ai_model = AIModel()

class User:
    def __init__(self, id, username, role):
        self.id = id
        self.username = username
        self.role = role

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
    
    uploaded_files = st.file_uploader("Choose image files", accept_multiple_files=True, type=['png', 'jpg', 'jpeg'])
    
    if uploaded_files:
        for uploaded_file in uploaded_files:
            process_uploaded_file(uploaded_file)

def process_uploaded_file(uploaded_file):
    try:
        # Open the image using PIL
        image = Image.open(uploaded_file)
        
        # Resize the image
        resized_image = resize_image(image)
        
        # Convert the image to base64
        image_data = image_to_base64(resized_image)
        
        # Get AI prediction
        main_category, subcategory, confidence = ai_model.predict(resized_image)
        
        # Save image to database
        db.save_image(uploaded_file.name, image_data, main_category, subcategory, st.session_state['user'].id, confidence)
        
        st.success(f"Uploaded and processed: {uploaded_file.name}")
        st.write(f"Predicted category: {main_category} - {subcategory}")
        st.write(f"Confidence: {confidence:.2f}")
        
    except Exception as e:
        st.error(f"Error processing {uploaded_file.name}: {str(e)}")

def review_page():
    st.header("Review and Correct Categorizations")
    st.warning("Review functionality is currently disabled to reduce resource usage.")

def statistics_page():
    st.header("AI Performance Analytics Dashboard")
    st.warning("Statistics functionality is currently disabled to reduce resource usage.")

def user_management_page():
    st.header("User Management")
    st.warning("User management functionality is currently disabled to reduce resource usage.")

if __name__ == "__main__":
    main()
