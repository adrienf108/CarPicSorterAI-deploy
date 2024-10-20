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
import bcrypt

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
            upload_progress = (i + 0.5) / total_files
            progress_bar.progress(upload_progress)
            status_text.text(f"Uploading and processing {i+1}/{total_files} images")

            main_category, subcategory, confidence = ai_model.predict(image)

            display_image = resize_image(image, size=(300, 300))
            image_data = image_to_base64(display_image)

            db.save_image(filename, image_data, main_category, subcategory, st.session_state['user'].id, float(confidence))

            if main_category == 'Uncategorized':
                st.image(display_image, caption=f"{filename}: Uncategorized (Confidence: {confidence:.2f})", use_column_width=True)
            else:
                st.image(display_image, caption=f"{filename}: {main_category} - {subcategory} (Confidence: {confidence:.2f})", use_column_width=True)

            process_progress = (i + 1) / total_files
            progress_bar.progress(process_progress)
            status_text.text(f"Processed {i+1}/{total_files} images")

        st.success(f"Successfully uploaded and processed {total_files} images!")

def review_page():
    st.header("Review and Correct Categorizations")
    
    images = db.get_all_images()
    
    if not images:
        st.warning("No images to review.")
        return

    # Use session state to keep track of the current image index
    if 'current_image_index' not in st.session_state:
        st.session_state['current_image_index'] = 0

    current_image = images[st.session_state['current_image_index']]

    # Display current image
    st.image(base64.b64decode(current_image['image_data']), use_column_width=True)
    st.write(f"Current: {current_image['category']} - {current_image['subcategory']}")

    # Button-based category selection
    st.write("Select Main Category:")
    cols = st.columns(len(ai_model.model.main_categories) + 1)  # +1 for 'Uncategorized'
    for i, category in enumerate(ai_model.model.main_categories + ['Uncategorized']):
        if cols[i].button(category, key=f"main_{category}"):
            if category != 'Uncategorized':
                st.session_state['selected_main_category'] = category
                st.rerun()
            else:
                db.update_categorization(current_image['id'], 'Uncategorized', 'Uncategorized')
                ai_model.learn_from_manual_categorization(Image.open(io.BytesIO(base64.b64decode(current_image['image_data']))), 'Uncategorized', 'Uncategorized')
                move_to_next_image()

    # Show subcategories if a main category is selected
    if 'selected_main_category' in st.session_state:
        st.write(f"Select Subcategory for {st.session_state['selected_main_category']}:")
        subcategories = ai_model.model.subcategories[st.session_state['selected_main_category']]
        subcategory_cols = st.columns(len(subcategories))
        for i, subcategory in enumerate(subcategories):
            if subcategory_cols[i].button(subcategory, key=f"sub_{subcategory}"):
                db.update_categorization(current_image['id'], st.session_state['selected_main_category'], subcategory)
                ai_model.learn_from_manual_categorization(Image.open(io.BytesIO(base64.b64decode(current_image['image_data']))), st.session_state['selected_main_category'], subcategory)
                move_to_next_image()

    # Navigation buttons
    col1, col2 = st.columns(2)
    if col1.button("Previous Image"):
        if st.session_state['current_image_index'] > 0:
            st.session_state['current_image_index'] -= 1
            if 'selected_main_category' in st.session_state:
                del st.session_state['selected_main_category']
            st.rerun()
        else:
            st.warning("This is the first image.")

    if col2.button("Next Image"):
        if st.session_state['current_image_index'] < len(images) - 1:
            move_to_next_image()
        else:
            st.warning("This is the last image.")

def move_to_next_image():
    if st.session_state['current_image_index'] < len(db.get_all_images()) - 1:
        st.session_state['current_image_index'] += 1
        if 'selected_main_category' in st.session_state:
            del st.session_state['selected_main_category']
        st.rerun()
    else:
        st.success("All images have been reviewed!")

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
    confusion_matrix = stats['confusion_matrix']
    fig = px.imshow(confusion_matrix, 
                    labels=dict(x="Predicted Category", y="True Category", color="Count"),
                    x=ai_model.model.main_categories,
                    y=ai_model.model.main_categories)
    fig.update_layout(title='Confusion Matrix')
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
