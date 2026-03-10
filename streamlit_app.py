import streamlit as st
from supabase import create_client, Client

# 1. Setup Supabase Connection
url = "https://eeqdkamaxghssoxxqsxi.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVlcWRrYW1heGdoc3NveHhxc3hpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI5MDU1OTksImV4cCI6MjA4ODQ4MTU5OX0.aKi31CJeb_G9fRzkzjfNAgtcehBzoy5w2CgFdjSQRQM"
supabase: Client = create_client(url, key)

# Initialize session state for the user
if "user" not in st.session_state:
    st.session_state.user = None

# --- AUTHENTICATION UI ---
def auth_screen():
    st.title("Plant Tracker 🌿")
    tab1, tab2 = st.tabs(["Login", "Sign Up"])

    with tab1:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                try:
                    res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    st.session_state.user = res.user
                    st.rerun()
                except Exception as e:
                    st.error(f"Login failed: {e}")

    with tab2:
        with st.form("signup_form"):
            new_email = st.text_input("Email")
            new_password = st.text_input("Password", type="password")
            if st.form_submit_button("Create Account"):
                try:
                    # This triggers the SQL function we created earlier
                    supabase.auth.sign_up({"email": new_email, "password": new_password})
                    st.success("Signup successful! Check your email for confirmation (if enabled).")
                except Exception as e:
                    st.error(f"Signup failed: {e}")

# --- MAIN DASHBOARD UI ---
def dashboard():
    user = st.session_state.user
    st.sidebar.write(f"Logged in as: {user.email}")
    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.rerun()

    st.title("My Garden")

    # Add New Plant Form
    with st.expander("➕ Add New Plant"):
        with st.form("add_plant"):
            name = st.text_input("Plant Name")
            freq = st.number_input("Watering Frequency (days)", min_value=1, value=7)
            if st.form_submit_button("Save Plant"):
                # Always include the user.id so RLS allows the insert
                data = {"name": name, "frequency": freq, "user_id": user.id}
                supabase.table("plants").insert(data).execute()
                st.success(f"{name} added!")
                st.rerun()

    # Display User's Plants
    st.subheader("Your Plants")
    # Query is automatically filtered by RLS if enabled
    response = supabase.table("plants").select("*").eq("user_id", user.id).execute()
    
    if response.data:
        for plant in response.data:
            col1, col2 = st.columns([3, 1])
            col1.write(f"**{plant['name']}** (Every {plant['frequency']} days)")
            if col2.button("Log Water", key=plant['id']):
                # Add to plant_logs table
                log_data = {"plant_id": plant['id'], "last_watered": "now()"}
                supabase.table("plant_logs").insert(log_data).execute()
                st.toast("Watering logged!")
    else:
        st.info("No plants found. Add one above!")

# --- APP LOGIC ---
if st.session_state.user is None:
    auth_screen()
else:
    dashboard()
