import streamlit as st
import pandas as pd
from PIL import Image
import io
import base64
from database import Database
from ai_model import AIModel
from image_utils import resize_image, image_to_base64

# Initialize database and AI model
db = Database()
ai_model = AIModel()

def main():
    st.title("AI-powered Car Image Categorization")

    # Sidebar for navigation
    page = st.sidebar.selectbox("Choose a page", ["Upload", "Review", "Statistics"])

    if page == "Upload":
        upload_page()
    elif page == "Review":
        review_page()
    else:
        statistics_page()

def upload_page():
    st.header("Upload Car Images")
    uploaded_files = st.file_uploader("Choose images to upload", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

    if uploaded_files:
        for file in uploaded_files:
            image = Image.open(file)
            
            # Predict category and subcategory using full image
            category, subcategory = ai_model.predict(image)
            
            # Resize image for display purposes only
            display_image = resize_image(image, size=(300, 300))
            image_data = image_to_base64(display_image)
            
            # Save to database
            db.save_image(file.name, image_data, category, subcategory)
            
            st.image(display_image, caption=f"{file.name}: {category} - {subcategory}", use_column_width=True)

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
                new_category = st.text_input("New Category", key=f"cat_{idx}")
                new_subcategory = st.text_input("New Subcategory", key=f"subcat_{idx}")
                if st.form_submit_button("Correct"):
                    db.update_categorization(image['id'], new_category, new_subcategory)
                    st.success("Categorization updated!")

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
