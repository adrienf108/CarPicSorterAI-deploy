import streamlit as st
import os
from PIL import Image
import io
import zipfile
import hashlib
import base64
from database import Database
from ai_model import AIModel
from image_utils import resize_image, image_to_base64
import bcrypt

# Initialize the database and AI model
db = Database()
ai_model = AIModel()

# Set page config
st.set_page_config(page_title="Car Image Categorizer", layout="wide")

# Session state initialization
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'user_role' not in st.session_state:
    st.session_state.user_role = None
if 'total_tokens' not in st.session_state:
    st.session_state.total_tokens = 0
if 'processed_images' not in st.session_state:
    st.session_state.processed_images = 0

def calculate_image_hash(image):
    """Calculate a hash of the image content for duplicate detection"""
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format=image.format if image.format else 'PNG')
    return hashlib.md5(img_byte_arr.getvalue()).hexdigest()

def handle_login():
    st.title("Login")
    username = st.text_input("Username", key="login_username")
    password = st.text_input("Password", type="password", key="login_password")
    
    if st.button("Login", key="login_button"):
        user = db.get_user_by_username(username)
        if user and bcrypt.checkpw(password.encode('utf-8'), user[2].encode('utf-8')):
            st.session_state.authenticated = True
            st.session_state.user_id = user[0]
            st.session_state.user_role = user[3]
            st.success("Logged in successfully!")
            st.rerun()
        else:
            st.error("Invalid username or password")

def handle_registration():
    st.title("Register")
    username = st.text_input("Username", key="register_username")
    password = st.text_input("Password", type="password", key="register_password")
    
    if st.button("Register", key="register_button"):
        try:
            user_id = db.create_user(username, password)
            if user_id:
                st.success("Registration successful! Please login.")
            else:
                st.error("Registration failed")
        except Exception as e:
            st.error(f"Registration failed: {str(e)}")

def handle_user_management():
    if st.session_state.user_role == 'admin':
        st.title("User Management")
        users = db.get_all_users()
        
        for user in users:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"Username: {user['username']} (Current role: {user['role']})")
            with col2:
                if user['role'] == 'user':
                    if st.button(f"Promote to Admin", key=f"promote_{user['id']}"):
                        db.update_user_role(user['id'], 'admin')
                        st.success(f"Promoted {user['username']} to admin")
                        st.rerun()

def process_uploaded_file(uploaded_file, user_id):
    try:
        # Read the image
        image_bytes = uploaded_file.read()
        image = Image.open(io.BytesIO(image_bytes))
        
        # Calculate image hash
        image_hash = calculate_image_hash(image)
        
        # Check for duplicates in the database
        with db.conn.cursor() as cur:
            cur.execute("SELECT filename FROM images WHERE image_data LIKE %s", (f"%{image_hash}%",))
            if cur.fetchone():
                return True  # Duplicate found
        
        # Process the image
        resized_image = resize_image(image)
        main_category, subcategory, confidence = ai_model.predict(resized_image)
        
        # Save to database with hash
        image_data = f"{image_hash}:{image_to_base64(resized_image)}"
        db.save_image(uploaded_file.name, image_data, main_category, subcategory, user_id, confidence)
        
        return False  # Not a duplicate
    except Exception as e:
        st.error(f"Error processing {uploaded_file.name}: {str(e)}")
        return False

def handle_upload():
    st.title("Upload Car Images")
    uploaded_files = st.file_uploader("Choose image files", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True, key="image_uploader")
    uploaded_zip = st.file_uploader("Or upload a ZIP file containing images", type=['zip'], key="zip_uploader")
    
    if uploaded_files or uploaded_zip:
        total_files = 0
        duplicates_count = 0
        
        if uploaded_zip:
            with zipfile.ZipFile(uploaded_zip) as z:
                for filename in z.namelist():
                    if filename.startswith('__MACOSX/') or filename.startswith('.'):
                        continue
                    if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                        with z.open(filename) as file:
                            image_data = file.read()
                            image_file = type('UploadedFile', (), {'name': filename, 'read': lambda: image_data})
                            if process_uploaded_file(image_file, st.session_state.user_id):
                                duplicates_count += 1
                            total_files += 1
        
        if uploaded_files:
            for uploaded_file in uploaded_files:
                if process_uploaded_file(uploaded_file, st.session_state.user_id):
                    duplicates_count += 1
                total_files += 1
        
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

def handle_review():
    st.title("Review Images")
    # Get all images from the database
    images = db.get_all_images()
    
    if not images:
        st.write("No images to review")
        return
    
    # Create a zip file for download
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        for idx, image in enumerate(images):
            # Extract image data and hash
            image_parts = image['image_data'].split(':', 1)
            if len(image_parts) == 2:
                image_hash, image_base64 = image_parts
            else:
                image_base64 = image_parts[0]
            
            # Decode base64 image
            image_data = base64.b64decode(image_base64)
            
            # Create standardized filename
            filename = f"{image['category']}_{image['subcategory']}_{idx+1}.png"
            zip_file.writestr(filename, image_data)
    
    # Download button
    st.download_button(
        label="Download All Images",
        data=zip_buffer.getvalue(),
        file_name="categorized_images.zip",
        mime="application/zip",
        key="download_all"
    )
    
    # Display images in a grid
    cols = st.columns(3)
    for idx, image in enumerate(images):
        with cols[idx % 3]:
            # Extract image data and hash
            image_parts = image['image_data'].split(':', 1)
            if len(image_parts) == 2:
                image_hash, image_base64 = image_parts
            else:
                image_base64 = image_parts[0]
            
            st.image(f"data:image/png;base64,{image_base64}", use_column_width=True)
            
            # Category selection
            main_category = st.selectbox(
                f"Main Category ({idx+1})",
                ['Uncategorized'] + ai_model.main_categories,
                index=(['Uncategorized'] + ai_model.main_categories).index(image['category']),
                key=f"main_{idx}"
            )
            
            subcategories = ai_model.subcategories.get(main_category, ['Uncategorized'])
            subcategory = st.selectbox(
                f"Subcategory ({idx+1})",
                subcategories,
                index=subcategories.index(image['subcategory']) if image['subcategory'] in subcategories else 0,
                key=f"sub_{idx}"
            )
            
            if st.button(f"Update ({idx+1})", key=f"update_{idx}"):
                db.update_categorization(image['id'], main_category, subcategory)
                st.success(f"Updated image {idx+1}")

def handle_statistics():
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
    category_data = {item['category']: item['count'] for item in stats['category_distribution']}
    st.bar_chart(category_data)
    
    # Accuracy Over Time
    st.subheader("Accuracy Over Time")
    accuracy_data = {str(item['date']): item['accuracy'] for item in stats['accuracy_over_time']}
    st.line_chart(accuracy_data)
    
    # Confusion Matrix
    st.subheader("Confusion Matrix")
    import plotly.figure_factory as ff
    fig = ff.create_annotated_heatmap(
        stats['confusion_matrix'],
        x=stats['confusion_categories'],
        y=stats['confusion_categories'],
        colorscale='Viridis'
    )
    st.plotly_chart(fig)
    
    # Top Misclassifications
    st.subheader("Top Misclassifications")
    st.table(stats['top_misclassifications'])
    
    # Confidence Distribution
    st.subheader("Confidence Distribution")
    confidence_values = [item['confidence'] for item in stats['confidence_distribution']]
    st.bar_chart(confidence_values)  # Changed from histogram_chart to bar_chart

def main():
    if not st.session_state.authenticated:
        tab1, tab2 = st.tabs(["Login", "Register"])
        with tab1:
            handle_login()
        with tab2:
            handle_registration()
    else:
        # Sidebar navigation
        page = st.sidebar.radio(
            "Navigation",
            ["Upload", "Review", "Statistics"] + (["User Management"] if st.session_state.user_role == 'admin' else []),
            key="navigation"
        )
        
        # Logout button
        if st.sidebar.button("Logout", key="logout"):
            st.session_state.authenticated = False
            st.session_state.user_id = None
            st.session_state.user_role = None
            st.rerun()
        
        # Page routing
        if page == "Upload":
            handle_upload()
        elif page == "Review":
            handle_review()
        elif page == "Statistics":
            handle_statistics()
        elif page == "User Management":
            handle_user_management()

if __name__ == "__main__":
    main()
