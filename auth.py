import streamlit as st
from database import Database
import bcrypt

db = Database()

def init_auth():
    if 'user' not in st.session_state:
        st.session_state.user = None

def register_user(username, password, role):
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    return db.create_user(username, hashed_password.decode('utf-8'), role)

def authenticate_user(username, password):
    user_data = db.get_user_by_username(username)
    if user_data and bcrypt.checkpw(password.encode('utf-8'), user_data['password'].encode('utf-8')):
        st.session_state.user = {
            'id': user_data['id'],
            'username': user_data['username'],
            'role': user_data['role']
        }
        return True
    return False

def logout():
    st.session_state.user = None

def get_current_user_role():
    return st.session_state.user['role'] if st.session_state.user else None

def login_required(func):
    def wrapper(*args, **kwargs):
        if st.session_state.user is None:
            st.warning("You need to be logged in to access this page.")
            st.stop()
        return func(*args, **kwargs)
    return wrapper
