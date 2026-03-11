import streamlit as st
import pandas as pd
from datetime import date
from supabase import create_client

# 1. DEFINE FUNCTION FIRST
def get_client():
    if "supabase" not in st.session_state:
        st.session_state.supabase = create_client(st.secrets["url"], st.secrets["key"])
    return st.session_state.supabase

# 2. INITIALIZE SESSION STATE
if "user" not in st.session_state:
    st.session_state.user = None

# 3. AUTHENTICATION UI
if st.session_state.user is None:
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    with tab1:
        with st.form("login"):
            email = st.text_input("Email")
            pw = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                try:
                    res = get_client().auth.sign_in_with_password({"email": email, "password": pw})
                    st.session_state.user = res.user
                    get_client().auth.set_session(res.session.access_token, res.session.refresh_token)
                    st.rerun()
                except Exception as e:
                    st.error(f"Login failed: {e}")
    st.stop() # Stop here if not logged in

# 4. DASHBOARD (Only runs if logged in)
st.title("🪴 My Plant Garden")
if st.button("Logout"):
    st.session_state.user = None
    st.rerun()

# Fetch and display data
def load_data():
    data = get_client().table("plants").select("*").eq("user_id", st.session_state.user.id).execute().data
    return pd.DataFrame(data)

df = load_data()
st.write(df)
