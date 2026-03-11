import streamlit as st
from supabase import create_client, Client

# Initialize connection
url = "https://eeqdkamaxghssoxxqsxi.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVlcWRrYW1heGdoc3NveHhxc3hpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI5MDU1OTksImV4cCI6MjA4ODQ4MTU5OX0.aKi31CJeb_G9fRzkzjfNAgtcehBzoy5w2CgFdjSQRQM"


# Ensure client exists
if "supabase" not in st.session_state:
    st.session_state.supabase = create_client(url, key)

# Helper for the authenticated client
def get_client():
    return st.session_state.supabase

# Authentication Logic
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
                st.session_state.supabase.auth.set_session(res.session.access_token, res.session.refresh_token)
                st.rerun()
    with tab2:
        with st.form("signup"):
            email = st.text_input("New Email")
            pw = st.text_input("New Password", type="password")
            if st.form_submit_button("Sign Up"):
                get_client().auth.sign_up({"email": email, "password": pw})
                st.success("Check email!")
else:
    # Dashboard Logic
    st.write(f"Logged in: {st.session_state.user.email}")
    if st.button("Logout"):
        st.session_state.user = None
        st.rerun()

    with st.form("add_plant"):
        name = st.text_input("Plant Name")
        freq = st.number_input("Frequency", value=7)
        if st.form_submit_button("Add"):
            data = {"name": name, "frequency": freq, "user_id": st.session_state.user.id}
            # This now uses the authenticated client
            get_client().table("plants").insert(data).execute()
            st.rerun()

    # Display
    plants = get_client().table("plants").select("*").eq("user_id", st.session_state.user.id).execute()
    st.write(plants.data)
