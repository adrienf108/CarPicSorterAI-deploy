[Previous content of main.py up to line 225...]

        st.success(f"Successfully uploaded and processed {total_files} images!")
        if duplicates_count > 0:
            st.info(f"Skipped {duplicates_count} duplicate image(s) during this upload.")
            
        # Display token usage statistics
        if 'total_tokens' in st.session_state and 'processed_images' in st.session_state:
            total_tokens = st.session_state['total_tokens']
            processed_images = st.session_state['processed_images']
            avg_tokens = total_tokens / processed_images if processed_images > 0 else 0
            
            st.write("---")
            st.subheader("Token Usage Statistics")
            st.write(f"Total tokens used: {total_tokens:,}")
            st.write(f"Images processed: {processed_images}")
            st.write(f"Average tokens per image: {avg_tokens:,.1f}")
            
            # Reset counters for next batch
            st.session_state['total_tokens'] = 0
            st.session_state['processed_images'] = 0

[Rest of main.py content remains the same...]
