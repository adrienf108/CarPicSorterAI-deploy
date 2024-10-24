import streamlit as st
from PIL import Image
import io
import os

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
""")

# Create upload section
st.header("Upload Image")
uploaded_file = st.file_uploader("Choose a car image...", type=["jpg", "jpeg", "png"])

# Create two columns for layout
col1, col2 = st.columns(2)

if uploaded_file is not None:
    # Read and display the image
    with col1:
        st.subheader("Uploaded Image")
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Car Image", use_column_width=True)
        
        # Display image information
        file_details = {
            "Filename": uploaded_file.name,
            "File size": f"{uploaded_file.size / 1024:.2f} KB",
            "File type": uploaded_file.type
        }
        
        st.subheader("Image Details")
        for key, value in file_details.items():
            st.text(f"{key}: {value}")

    with col2:
        st.subheader("Image Processing")
        st.info("AI analysis will be implemented in the next phase.")
        
        # Placeholder for future AI processing results
        st.markdown("### Categories")
        st.text("🔄 Waiting for AI analysis...")
        
else:
    # Display placeholder message when no image is uploaded
    with col1:
        st.info("Please upload an image to begin analysis")
