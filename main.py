# ... previous code remains the same up to line 303 ...

@st.cache_data(ttl=300)
def get_all_images():
    """Get all images with caching (5 minutes TTL)"""
    return get_db().get_all_images()

def review_page():
    """Handle image review and categorization."""
    st.header("Review and Correct Categorizations")
    
    # Get all images with caching
    images = get_all_images()
    
    if not images:
        st.warning("No images to review.")
        return
    
    st.write(f"Showing {len(images)} images")
    
    # Display images in grid with memory optimization
    cols = st.columns(3)
    for i, image in enumerate(images):
        with cols[i % 3]:
            try:
                with st.container():
                    # Decode and display image
                    img_data = base64.b64decode(image['image_data'])
                    img = Image.open(io.BytesIO(img_data))
                    img.thumbnail((300, 300))
                    st.image(img, use_column_width=True)
                    del img
                    del img_data
                    
                    st.write(f"Current: {image['category']} - {image['subcategory']}")
                    
                    button_key = f"buttons_{image['id']}"
                    
                    if button_key not in st.session_state:
                        st.session_state[button_key] = {"state": "main", "selected_category": None}
                    
                    if st.session_state[button_key]["state"] == "main":
                        st.write("Select Main Category:")
                        cols_categories = st.columns(3)
                        for idx, category in enumerate(get_ai_model().model.main_categories + ['Uncategorized']):
                            with cols_categories[idx % 3]:
                                if st.button(category, key=f"{button_key}_{category}"):
                                    st.session_state[button_key]["state"] = "sub"
                                    st.session_state[button_key]["selected_category"] = category
                                    st.rerun()
                    
                    elif st.session_state[button_key]["state"] == "sub":
                        selected_category = st.session_state[button_key]["selected_category"]
                        if selected_category != 'Uncategorized':
                            st.write(f"Select Subcategory for {selected_category}:")
                            cols_subcategories = st.columns(3)
                            subcategories = get_ai_model().model.subcategories[selected_category]
                            for idx, subcategory in enumerate(subcategories):
                                with cols_subcategories[idx % 3]:
                                    if st.button(subcategory, key=f"{button_key}_{subcategory}"):
                                        get_db().update_categorization(image['id'], selected_category, subcategory)
                                        get_all_images.clear()
                                        st.session_state[button_key]["state"] = "main"
                                        st.rerun()
                        else:
                            if st.button("Confirm Uncategorized", key=f"{button_key}_uncategorized"):
                                get_db().update_categorization(image['id'], 'Uncategorized', 'Uncategorized')
                                get_all_images.clear()
                                st.session_state[button_key]["state"] = "main"
                                st.rerun()
                        
                        if st.button("Back", key=f"{button_key}_back"):
                            st.session_state[button_key]["state"] = "main"
                            st.rerun()
            
            except Exception as e:
                logger.error(f"Error displaying image: {str(e)}")
                st.error("Error displaying image")
            finally:
                gc.collect()
    
    # Download functionality with memory optimization
    st.write("---")
    st.subheader("Download All Images")
    
    if st.button("Prepare Download"):
        with st.spinner("Preparing zip file..."):
            zip_buffer = io.BytesIO()
            
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                file_counter = 1
                
                # Get all images from cache
                all_images = get_all_images()
                
                sorted_images = sorted(all_images, key=lambda x: (
                    CATEGORY_NUMBERS.get(x['category'], '99'),
                    SUBCATEGORY_NUMBERS.get(x['category'], {}).get(x['subcategory'], '99')
                ))
                
                for image in sorted_images:
                    cat_num = CATEGORY_NUMBERS.get(image['category'], '99')
                    subcat_num = SUBCATEGORY_NUMBERS.get(image['category'], {}).get(image['subcategory'], '99')
                    
                    _, ext = os.path.splitext(image['filename'])
                    if not ext:
                        ext = '.jpg'
                    
                    filename = f"{cat_num}{subcat_num}_{file_counter:04d}{ext}"
                    
                    img_bytes = base64.b64decode(image['image_data'])
                    zf.writestr(filename, img_bytes)
                    
                    file_counter += 1
                    gc.collect()
                
                del sorted_images
                gc.collect()
            
            zip_buffer.seek(0)
            st.download_button(
                label="Download All Images (Organized by Category)",
                data=zip_buffer,
                file_name="all_car_images.zip",
                mime="application/zip",
                key="download_all_images_button"
            )

# ... rest of the code remains the same ...
