import streamlit as st
from PIL import Image
import io

def main():
    # Set page configuration
    st.set_page_config(
        page_title="Car Image Classifier",
        page_icon="🚗",
        layout="wide"
    )

    # Main title and description
    st.title("🚗 Car Image Classifier")
    st.markdown("""
    Upload car images for AI-powered classification and manual review.
    This tool helps you automatically categorize different types of cars.
    """)

    # Sidebar for controls
    with st.sidebar:
        st.header("Controls")
        st.info("Upload an image to get started")

    # File uploader
    uploaded_file = st.file_uploader(
        "Choose a car image...",
        type=["jpg", "jpeg", "png"],
        help="Supported formats: JPG, JPEG, PNG"
    )

    # Create two columns for layout
    col1, col2 = st.columns(2)

    if uploaded_file is not None:
        try:
            # Read and display the uploaded image
            image = Image.open(uploaded_file)
            
            with col1:
                st.subheader("Uploaded Image")
                st.image(image, use_column_width=True)
                
                # Display image details
                file_details = {
                    "Filename": uploaded_file.name,
                    "File size": f"{uploaded_file.size / 1024:.2f} KB",
                    "Image dimensions": f"{image.size[0]}x{image.size[1]} pixels"
                }
                st.write("### Image Details")
                for key, value in file_details.items():
                    st.write(f"**{key}:** {value}")

            with col2:
                st.subheader("Classification Results")
                st.info("AI classification will be implemented in the next phase")
                
                # Placeholder for future AI classification results
                with st.expander("Classification Details", expanded=True):
                    st.write("Waiting for AI model integration...")
                
                # Manual review section
                st.subheader("Manual Review")
                review_status = st.selectbox(
                    "Review Status",
                    ["Pending Review", "Approved", "Rejected"]
                )
                review_notes = st.text_area("Review Notes")
                
                if st.button("Submit Review"):
                    st.success("Review submitted successfully!")
                    
        except Exception as e:
            st.error(f"Error processing image: {str(e)}")
    else:
        # Display placeholder when no image is uploaded
        with col1:
            st.info("Please upload an image to begin")

if __name__ == "__main__":
    main()
