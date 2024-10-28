# Update the import section to include compress_image
from image_utils import image_to_base64, compress_image

def process_single_image(filename, file_data, user_id):
    try:
        img = Image.open(io.BytesIO(file_data))
        
        # Compress image before processing
        img = compress_image(img)
        
        img_hash = calculate_image_hash(img)
        
        # Initialize processed_hashes in session state if not exists
        if 'processed_hashes' not in st.session_state:
            st.session_state['processed_hashes'] = set()
            # Get existing hashes from database
            with db.conn.cursor() as cur:
                cur.execute('SELECT DISTINCT image_hash FROM images')
                existing_hashes = cur.fetchall()
                st.session_state['processed_hashes'].update([h[0] for h in existing_hashes if h[0]])
        
        # Check for duplicates with improved handling
        if img_hash in st.session_state['processed_hashes']:
            if 'duplicates_count' not in st.session_state:
                st.session_state['duplicates_count'] = 0
            st.session_state['duplicates_count'] += 1
            
            if 'duplicate_filenames' not in st.session_state:
                st.session_state['duplicate_filenames'] = []
            st.session_state['duplicate_filenames'].append(filename)
            
            st.warning(f"Skipped duplicate image: {filename}")  # Add immediate feedback
            logger.info(f"Duplicate image detected: {filename}")
            return
        
        st.session_state['processed_hashes'].add(img_hash)
        
        main_category, subcategory, confidence, token_usage, image_size = ai_model.predict(img)
        logger.info(f"AI Model prediction for {filename}: {main_category} - {subcategory} (Confidence: {confidence})")
        
        image_data = image_to_base64(img)
        db.save_image(filename, image_data, main_category, subcategory, user_id, float(confidence), token_usage, image_size, img_hash)
        
        display_image = img.copy()
        display_image.thumbnail((300, 300))
        
        if main_category == 'Uncategorized':
            st.image(display_image, caption=f"{filename}: Uncategorized (Confidence: {confidence:.2f})", use_column_width=True)
        else:
            st.image(display_image, caption=f"{filename}: {main_category} - {subcategory} (Confidence: {confidence:.2f})", use_column_width=True)
            
    except Exception as e:
        logger.error(f"Error processing image {filename}: {str(e)}")
        st.error(f"Error processing image {filename}: {str(e)}")
