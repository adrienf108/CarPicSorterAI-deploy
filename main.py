import streamlit as st
import pandas as pd
from PIL import Image
import io
import base64
from database import Database
from ai_model import AIModel
from image_utils import resize_image, image_to_base64
from auth import init_auth, register_user, create_admin_user, authenticate_user, logout, get_current_user_role, login_required, admin_required

# Initialize database and AI model
db = Database()
ai_model = AIModel()

# Initialize authentication
init_auth()

def main():
    st.title("AI-powered Car Image Categorization")

    # Sidebar for navigation and authentication
    st.sidebar.title("Navigation")
    
    if st.session_state.user:
        st.sidebar.write(f"Logged in as: {st.session_state.user['role']}")
        if st.sidebar.button("Logout"):
            logout()
            st.rerun()
    else:
        st.sidebar.write("Not logged in")
        
    pages = ["Login", "Register", "Upload", "Review", "Statistics"]
    if st.session_state.user and st.session_state.user['role'] == 'admin':
        pages.append("Create Admin")
    
    page = st.sidebar.selectbox("Choose a page", pages)

    if page == "Login":
        login_page()
    elif page == "Register":
        register_page()
    elif page == "Upload":
        upload_page()
    elif page == "Review":
        review_page()
    elif page == "Statistics":
        statistics_page()
    elif page == "Create Admin":
        admin_create_page()

def login_page():
    st.header("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if authenticate_user(username, password):
            st.success("Logged in successfully!")
            st.rerun()
        else:
            st.error("Invalid username or password")

def register_page():
    st.header("Register")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Register"):
        result = register_user(username, password)
        if result:
            st.success("Registered successfully! Please log in.")
        else:
            st.error("Registration failed. Username may already exist.")

@admin_required
def admin_create_page():
    st.header("Create Admin User")
    username = st.text_input("Admin Username")
    password = st.text_input("Admin Password", type="password")
    if st.button("Create Admin"):
        if create_admin_user(username, password, st.session_state.user['id']):
            st.success("Admin user created successfully!")
        else:
            st.error("Failed to create admin user.")

@login_required
def upload_page():
    st.header("Upload Car Images")
    uploaded_files = st.file_uploader("Choose images to upload", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

    if uploaded_files:
        for file in uploaded_files:
            image = Image.open(file)
            
            # Predict category and subcategory using full image
            main_category, subcategory, confidence = ai_model.predict(image)
            
            # Resize image for display purposes only
            display_image = resize_image(image, size=(300, 300))
            image_data = image_to_base64(display_image)
            
            # Save to database
            db.save_image(file.name, image_data, main_category, subcategory)
            
            if main_category == 'Uncategorized':
                st.image(display_image, caption=f"{file.name}: Uncategorized (Confidence: {confidence:.2f})", use_column_width=True)
            else:
                st.image(display_image, caption=f"{file.name}: {main_category} - {subcategory} (Confidence: {confidence:.2f})", use_column_width=True)

@login_required
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

@admin_required
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

if __name__ == "__main__":
    main()
