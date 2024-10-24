import streamlit as st
from PIL import Image
import io
import os
import zipfile

# Set page configuration
st.set_page_config(
    page_title="Car Image Categorization",
    page_icon="🚗",
    layout="wide"
)

# Add custom CSS
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stButton>button {
        width: 100%;
    }
    </style>
    """, unsafe_allow_html=True)

# Title and description
st.title("🚗 Car Image Categorization")
st.markdown("""
    Upload car images for AI-powered categorization. Our system will analyze your images
    and provide detailed information about the car make and model.
    You can upload individual images or a zip file containing multiple images.
""")

# Create upload section
st.header("Upload Images")
uploaded_file = st.file_uploader("Choose car images or a zip file...", type=["jpg", "jpeg", "png", "zip"], accept_multiple_files=True)

# Create two columns for layout
col1, col2 = st.columns(2)

if uploaded_file:
    with col1:
        st.subheader("Uploaded Images")
        
        for file in uploaded_file:
            if file.type == "application/zip":
                st.write(f"Processing zip file: {file.name}")
                with zipfile.ZipFile(file) as z:
                    for filename in z.namelist():
                        if filename.lower().endswith(('.png', '.jpg', '.jpeg')) and not filename.startswith('__MACOSX/'):
                            with z.open(filename) as image_file:
                                try:
                                    image = Image.open(io.BytesIO(image_file.read()))
                                    st.image(image, caption=f"From zip: {filename}", use_column_width=True)
                                    
                                    # Display image information
                                    st.text(f"Filename: {filename}")
                                    st.text(f"Size: {image.size}")
                                    st.text(f"Format: {image.format}")
                                except Exception as e:
                                    st.warning(f"Could not process {filename}: {str(e)}")
            else:
                try:
                    image = Image.open(file)
                    st.image(image, caption=f"Uploaded: {file.name}", use_column_width=True)
                    
                    # Display image information
                    file_details = {
                        "Filename": file.name,
                        "File size": f"{file.size / 1024:.2f} KB",
                        "File type": file.type
                    }
                    
                    for key, value in file_details.items():
                        st.text(f"{key}: {value}")
                except Exception as e:
                    st.warning(f"Could not process {file.name}: {str(e)}")

    with col2:
        st.subheader("Image Processing")
        st.info("AI analysis will be implemented in the next phase.")
        
        # Placeholder for future AI processing results
        st.markdown("### Categories")
        st.text("🔄 Waiting for AI analysis...")
        
else:
    # Display placeholder message when no image is uploaded
    with col1:
        st.info("Please upload images or a zip file to begin analysis")
