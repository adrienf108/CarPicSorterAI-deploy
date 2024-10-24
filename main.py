import streamlit as st
from streamlit.runtime.scriptrunner import RerunException
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from PIL import Image
import io
import base64
import zipfile
from database import Database
from ai_model import AIModel
from image_utils import image_to_base64
import bcrypt
import hashlib
import numpy as np
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database
db = Database()

def statistics_page():
    st.header("AI Performance Analytics Dashboard")
    try:
        logger.info("Fetching statistics from database...")
        stats = db.get_statistics()
        logger.info(f"Retrieved statistics: {len(stats) if stats else 0} metrics")
        
        # Add null checks before accessing token_stats
        token_stats = stats.get('token_usage', {})
        if not token_stats:
            logger.warning("No token usage statistics available")
            token_stats = {
                'total_tokens': 0,
                'avg_tokens_per_image': 0,
                'usage_over_time': []
            }
        
        # Performance Metrics
        st.subheader("Performance Metrics")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Images", stats.get('total_images', 0))
        with col2:
            st.metric("Overall Accuracy", f"{stats.get('accuracy', 0):.2f}%")
        with col3:
            st.metric("Total Tokens Used", f"{token_stats.get('total_tokens', 0):,}")
        with col4:
            st.metric("Avg. Tokens/Image", f"{token_stats.get('avg_tokens_per_image', 0):.1f}")
        
        # Token Usage Over Time
        st.subheader("Token Usage Over Time")
        usage_over_time = token_stats.get('usage_over_time', [])
        if usage_over_time:
            try:
                token_usage_df = pd.DataFrame(usage_over_time)
                fig = px.line(token_usage_df, x='date', y='tokens', 
                            title='Daily Token Usage',
                            labels={'tokens': 'Tokens Used', 'date': 'Date'})
                st.plotly_chart(fig)

                # Images Processed Over Time
                fig = px.line(token_usage_df, x='date', y='images',
                            title='Daily Images Processed',
                            labels={'images': 'Images Processed', 'date': 'Date'})
                st.plotly_chart(fig)

                # Average Token Usage per Image Over Time
                if 'tokens' in token_usage_df and 'images' in token_usage_df:
                    token_usage_df['avg_tokens_per_image'] = token_usage_df['tokens'] / token_usage_df.where(token_usage_df['images'] != 0, 1)['images']
                    fig = px.line(token_usage_df, x='date', y='avg_tokens_per_image',
                                title='Average Tokens per Image Over Time',
                                labels={'avg_tokens_per_image': 'Avg. Tokens/Image', 'date': 'Date'})
                    st.plotly_chart(fig)
            except Exception as e:
                logger.error(f"Error creating token usage charts: {str(e)}")
                st.warning("Error creating token usage charts. Some data may be missing or invalid.")
        else:
            st.info("No token usage data available yet. Upload some images to see the statistics.")
        
        # Category Distribution
        st.subheader("Category Distribution")
        try:
            category_distribution = stats.get('category_distribution', [])
            if category_distribution:
                category_df = pd.DataFrame(category_distribution)
                fig = px.pie(category_df, values='count', names='category', title='Category Distribution')
                st.plotly_chart(fig)
            else:
                st.info("No category distribution data available.")
        except Exception as e:
            logger.error(f"Error creating category distribution chart: {str(e)}")
            st.warning("Error creating category distribution chart.")
        
        # Accuracy Over Time
        st.subheader("Accuracy Over Time")
        try:
            accuracy_over_time = stats.get('accuracy_over_time', [])
            if accuracy_over_time:
                accuracy_df = pd.DataFrame(accuracy_over_time)
                fig = px.line(accuracy_df, x='date', y='accuracy', title='AI Model Accuracy Over Time')
                st.plotly_chart(fig)
            else:
                st.info("No accuracy data available yet.")
        except Exception as e:
            logger.error(f"Error creating accuracy chart: {str(e)}")
            st.warning("Error creating accuracy chart.")
        
        # Confusion Matrix
        st.subheader("Confusion Matrix")
        try:
            confusion_matrix = np.array(stats.get('confusion_matrix', []))
            categories = stats.get('confusion_categories', [])
            
            if len(confusion_matrix) > 0 and len(categories) > 0:
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
                st.plotly_chart(fig)
            else:
                st.info("No confusion matrix data available yet.")
        except Exception as e:
            logger.error(f"Error creating confusion matrix: {str(e)}")
            st.warning("Error creating confusion matrix.")
        
        # Top Misclassifications
        st.subheader("Top Misclassifications")
        try:
            misclassifications = stats.get('top_misclassifications', [])
            if misclassifications:
                misclass_df = pd.DataFrame(misclassifications)
                st.table(misclass_df)
            else:
                st.info("No misclassification data available yet.")
        except Exception as e:
            logger.error(f"Error displaying misclassifications: {str(e)}")
            st.warning("Error displaying misclassifications.")
        
        # Confidence Distribution
        st.subheader("Confidence Distribution")
        try:
            confidence_distribution = stats.get('confidence_distribution', [])
            if confidence_distribution:
                confidence_df = pd.DataFrame(confidence_distribution)
                fig = px.histogram(confidence_df, x='confidence', nbins=20, title='Distribution of AI Confidence Scores')
                st.plotly_chart(fig)
            else:
                st.info("No confidence distribution data available yet.")
        except Exception as e:
            logger.error(f"Error creating confidence distribution chart: {str(e)}")
            st.warning("Error creating confidence distribution chart.")
            
    except Exception as e:
        logger.error(f"Error loading statistics page: {str(e)}")
        st.error("An error occurred while loading statistics. Please try again later.")
        return

if __name__ == "__main__":
    st.set_page_config(page_title="AI-powered Car Image Categorization", layout="wide")
    statistics_page()
