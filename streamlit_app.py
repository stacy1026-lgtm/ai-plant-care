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

import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
from supabase import create_client

# 1. Configuration
st.set_page_config(page_title="Plant Garden", page_icon="🪴")
URL = st.secrets["url"]
KEY = st.secrets["key"]

# 2. Auth & Client Initialization
if "supabase" not in st.session_state:
    st.session_state.supabase = create_client(URL, KEY)

def get_client():
    return st.session_state.supabase

# Authentication UI
if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    with tab1:
        with st.form("login"):
            email = st.text_input("Email")
            pw = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                res = get_client().auth.sign_in_with_password({"email": email, "password": pw})
                st.session_state.user = res.user
                get_client().auth.set_session(res.session.access_token, res.session.refresh_token)
                st.rerun()
    with tab2:
        with st.form("signup"):
            email = st.text_input("New Email")
            pw = st.text_input("New Password", type="password")
            if st.form_submit_button("Sign Up"):
                get_client().auth.sign_up({"email": email, "password": pw})
                st.success("Check your email!")
    st.stop()

# 3. Main Dashboard
st.title("🪴 My Plant Garden")
if st.sidebar.button("Logout"):
    st.session_state.user = None
    st.rerun()

# Helper: Fetch Data
def load_data():
    plants = get_client().table("plants").select("*").eq("user_id", st.session_state.user.id).execute().data
    return pd.DataFrame(plants)

df = load_data()

# 4. Watering Logic
with st.expander("🚿 Plants to Water"):
    if not df.empty:
        for idx, row in df.iterrows():
            cols = st.columns([2, 1])
            cols[0].write(f"**{row['name']}**")
            if cols[1].button("💧 Water", key=f"w_{row['id']}"):
                get_client().table("plants").update({"last_watered": str(date.today())}).eq("id", row['id']).execute()
                get_client().table("plant_logs").insert({"plant_id": row['id'], "user_id": st.session_state.user.id}).execute()
                st.rerun()

# 5. Add Plant
with st.expander("➕ Add Plant"):
    with st.form("add"):
        name = st.text_input("Name")
        freq = st.number_input("Frequency", value=7)
        if st.form_submit_button("Save"):
            get_client().table("plants").insert({"name": name, "frequency": freq, "user_id": st.session_state.user.id}).execute()
            st.rerun()

# 6. Cemetery
with st.expander("💀 Cemetery"):
    if not df.empty:
        selection = st.selectbox("Select to remove:", df['name'])
        if st.button("Confirm Removal"):
            target = df[df['name'] == selection].iloc[0]
            get_client().table("plants").delete().eq("id", target['id']).execute()
            st.rerun()
