[Previous content up to line 342 remains unchanged...]

def review_page():
    """Handle image review and categorization."""
    st.header("Review and Correct Categorizations")
    
    images = get_cached_images()
    logger.info(f"Retrieved {len(images)} images for review")
    
    if not images:
        st.warning("No images to review.")
        return

    cols = st.columns(3)
    for i, image in enumerate(images):
        with cols[i % 3]:
            with st.container():
                st.image(base64.b64decode(image['image_data']), use_column_width=True)
                logger.info(f"Displaying image {image['filename']} with categories: {image['category']} - {image['subcategory']}")
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
                                    get_ai_model().learn_from_manual_categorization(
                                        Image.open(io.BytesIO(base64.b64decode(image['image_data']))),
                                        selected_category,
                                        subcategory
                                    )
                                    st.session_state[button_key]["state"] = "main"
                                    st.rerun()
                    else:
                        if st.button("Confirm Uncategorized", key=f"{button_key}_uncategorized"):
                            get_db().update_categorization(image['id'], 'Uncategorized', 'Uncategorized')
                            st.session_state[button_key]["state"] = "main"
                            st.rerun()
                    
                    if st.button("Back", key=f"{button_key}_back"):
                        st.session_state[button_key]["state"] = "main"
                        st.rerun()

    st.write("---")
    st.subheader("Download All Images")
    
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        file_counter = 1
        
        sorted_images = sorted(images, key=lambda x: (
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
    
    zip_buffer.seek(0)
    
    st.download_button(
        label="Download All Images (Organized by Category)",
        data=zip_buffer,
        file_name="all_car_images.zip",
        mime="application/zip",
        key="download_all_images_button"
    )

def statistics_page():
    """Display AI performance analytics dashboard."""
    st.header("AI Performance Analytics Dashboard")
    
    stats = get_cached_statistics()
    token_stats = stats['token_usage']
    
    # Performance Metrics
    st.subheader("Performance Metrics")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Images", stats['total_images'])
    with col2:
        st.metric("Overall Accuracy", f"{stats['accuracy']:.2f}%")
    with col3:
        st.metric("Total Tokens Used", f"{token_stats['total_tokens']:,}")
    with col4:
        st.metric("Avg. Tokens/Image", f"{token_stats['avg_tokens_per_image']:.1f}")
    
    # Token Usage Over Time
    if token_stats['usage_over_time']:
        token_usage_df = pd.DataFrame(token_stats['usage_over_time'])
        
        # Daily Token Usage
        fig = px.line(token_usage_df, x='date', y='tokens',
                     title='Daily Token Usage',
                     labels={'tokens': 'Tokens Used', 'date': 'Date'})
        st.plotly_chart(fig, use_container_width=True)
        
        # Images Processed Over Time
        fig = px.line(token_usage_df, x='date', y='images',
                     title='Daily Images Processed',
                     labels={'images': 'Images Processed', 'date': 'Date'})
        st.plotly_chart(fig, use_container_width=True)
        
        # Average Token Usage per Image Over Time
        token_usage_df['avg_tokens_per_image'] = token_usage_df['tokens'] / token_usage_df['images']
        fig = px.line(token_usage_df, x='date', y='avg_tokens_per_image',
                     title='Average Tokens per Image Over Time',
                     labels={'avg_tokens_per_image': 'Avg. Tokens/Image', 'date': 'Date'})
        st.plotly_chart(fig, use_container_width=True)
        
        # Clear dataframes to free memory
        del token_usage_df
        gc.collect()
    else:
        st.info("No token usage data available yet. Upload some images to see the statistics.")
    
    # Category Distribution
    st.subheader("Category Distribution")
    category_df = pd.DataFrame(stats['category_distribution'])
    fig = px.pie(category_df, values='count', names='category',
                 title='Category Distribution')
    st.plotly_chart(fig, use_container_width=True)
    del category_df
    gc.collect()
    
    # Accuracy Over Time
    st.subheader("Accuracy Over Time")
    accuracy_df = pd.DataFrame(stats['accuracy_over_time'])
    fig = px.line(accuracy_df, x='date', y='accuracy',
                  title='AI Model Accuracy Over Time')
    st.plotly_chart(fig, use_container_width=True)
    del accuracy_df
    gc.collect()
    
    # Confusion Matrix
    st.subheader("Confusion Matrix")
    confusion_matrix = np.array(stats['confusion_matrix'])
    categories = stats['confusion_categories']
    
    fig = go.Figure(data=go.Heatmap(
        z=confusion_matrix,
        x=categories,
        y=categories,
        hoverongaps=False,
        colorscale='Viridis'
    ))
    fig.update_layout(
        title='Confusion Matrix',
        xaxis_title='Predicted Category',
        yaxis_title='True Category'
    )
    st.plotly_chart(fig, use_container_width=True)
    del confusion_matrix
    gc.collect()
    
    # Top Misclassifications
    st.subheader("Top Misclassifications")
    misclass_df = pd.DataFrame(stats['top_misclassifications'])
    st.table(misclass_df)
    del misclass_df
    gc.collect()
    
    # Confidence Distribution
    st.subheader("Confidence Distribution")
    confidence_df = pd.DataFrame(stats['confidence_distribution'])
    fig = px.histogram(confidence_df, x='confidence', nbins=20,
                      title='Distribution of AI Confidence Scores')
    st.plotly_chart(fig, use_container_width=True)
    del confidence_df
    gc.collect()

def login_page():
    """Handle user login and registration."""
    st.header("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Login"):
            user = get_db().get_user_by_username(username)
            if user and bcrypt.checkpw(password.encode('utf-8'), user[2].encode('utf-8')):
                st.session_state['user'] = User(user[0], user[1], user[3])
                st.success("Logged in successfully!")
                st.rerun()
            else:
                st.error("Invalid username or password")
    
    with col2:
        if st.button("Register"):
            if username and password:
                existing_user = get_db().get_user_by_username(username)
                if existing_user:
                    st.error("Username already exists")
                else:
                    user_count = len(get_db().get_all_users())
                    role = 'admin' if user_count == 0 else 'user'
                    user_id = get_db().create_user(username, password, role)
                    st.session_state['user'] = User(user_id, username, role)
                    st.success("Registered successfully!")
                    st.rerun()
            else:
                st.error("Please enter both username and password")

def user_management_page():
    """Handle user management for administrators."""
    st.header("User Management")
    
    users = get_db().get_all_users()
    for user in users:
        st.write(f"Username: {user['username']}, Role: {user['role']}")
        if user['role'] == 'user':
            if st.button(f"Promote {user['username']} to Admin"):
                get_db().update_user_role(user['id'], 'admin')
                st.success(f"{user['username']} promoted to Admin")
                st.rerun()

def main():
    """Main application entry point."""
    # Clean up any old temporary files and force garbage collection
    cleanup_temp_files()
    gc.collect()
    
    # Initialize session state for page navigation if not exists
    if 'page' not in st.session_state:
        st.session_state['page'] = 'Upload'

    # Check if user is logged in
    if 'user' not in st.session_state or not st.session_state['user']:
        login_page()
    else:
        st.title("AI-powered Car Image Categorization")
        
        # Sidebar for navigation
        st.sidebar.title("Navigation")
        pages = ["Upload", "Review", "Statistics"]
        if st.session_state['user'].role == 'admin':
            pages.append("User Management")
        
        selected_page = st.sidebar.selectbox("Go to", pages, index=pages.index(st.session_state['page']))
        
        # Update session state when page changes
        if selected_page != st.session_state['page']:
            st.session_state['page'] = selected_page
            st.rerun()

        # Display the selected page
        if st.session_state['page'] == "Upload":
            upload_page()
        elif st.session_state['page'] == "Review":
            review_page()
        elif st.session_state['page'] == "Statistics":
            statistics_page()
        elif st.session_state['page'] == "User Management" and st.session_state['user'].role == 'admin':
            user_management_page()
        else:
            st.warning("You don't have permission to access this page.")

        if st.sidebar.button("Logout"):
            st.session_state['user'] = None
            st.session_state['page'] = 'Upload'
            st.rerun()

if __name__ == "__main__":
    main()
