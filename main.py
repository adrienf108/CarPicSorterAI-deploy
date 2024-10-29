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
from image_utils import image_to_base64, cleanup_temp_files
import bcrypt
import hashlib
import numpy as np
import logging
import os
import math
import gc
import glob
from datetime import datetime, timedelta

# Configure logging to be minimal
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

# Set chunk size to 5MB for efficient memory usage
CHUNK_SIZE = 5 * 1024 * 1024

# Constants for cleanup
CLEANUP_DAYS_THRESHOLD = 30
CLEANUP_SIZE_THRESHOLD_MB = 1000

# Initialize database and AI model (with lazy loading)
db = None
ai_model = None

def get_db():
    global db
    if db is None:
        db = Database()
    return db

def get_ai_model():
    global ai_model
    if ai_model is None:
        ai_model = AIModel()
    return ai_model

def clear_previous_session():
    """Clear all temporary files and session data from previous upload sessions"""
    try:
        # Clear ALL session state variables
        session_keys = list(st.session_state.keys())
        for key in session_keys:
            if key != 'user':  # Preserve user login
                del st.session_state[key]
        
        # Remove all temporary files
        cleanup_temp_files(max_age_minutes=0)  # Clear all temp files regardless of age
        
        # Clean up specific file patterns
        patterns_to_clean = [
            '*.partial', '*.tmp', '*.temp', '*.pyc',
            '*.log', '*.cache', '*.preview'
        ]
        
        # Clean up in both /tmp and current directory
        directories_to_clean = ['/tmp', '.']
        for directory in directories_to_clean:
            for pattern in patterns_to_clean:
                pattern_path = os.path.join(directory, pattern)
                try:
                    files = glob.glob(pattern_path)
                    for file_path in files:
                        try:
                            os.remove(file_path)
                            logger.info(f"Removed file: {file_path}")
                        except OSError as e:
                            logger.error(f"Error removing {file_path}: {e}")
                except Exception as e:
                    logger.error(f"Error processing pattern {pattern}: {e}")
        
        # Clear image cache directories
        cache_dirs = ['.streamlit/cache', '.image_cache', 'image_cache']
        for cache_dir in cache_dirs:
            if os.path.exists(cache_dir):
                try:
                    for root, dirs, files in os.walk(cache_dir, topdown=False):
                        for name in files:
                            os.remove(os.path.join(root, name))
                        for name in dirs:
                            os.rmdir(os.path.join(root, name))
                    os.rmdir(cache_dir)
                except OSError as e:
                    logger.error(f"Error cleaning cache directory {cache_dir}: {e}")
        
        # Force garbage collection
        gc.collect()
        
    except Exception as e:
        logger.error(f"Error clearing previous session: {str(e)}")

# Rest of the file remains unchanged...

if __name__ == "__main__":
    st.set_page_config(
        page_title="Car Image Analysis",
        layout="wide"
    )
    # Set server port
    st.server.port = 8080
