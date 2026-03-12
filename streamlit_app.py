import streamlit as st
import pandas as pd
from datetime import date, timedelta
from supabase import create_client

# --- 1. CONFIG & INITIALIZATION ---
st.set_page_config(page_title="Plant Garden", page_icon="🪴")

# Define get_client at the very top so it's available everywhere
def get_client():
    if "supabase" not in st.session_state:
        st.session_state.supabase = create_client(
            st.secrets["url"], 
            st.secrets["key"]
        )
    return st.session_state.supabase

# --- 2. AUTHENTICATION ---
if "user" not in st.session_state:
    st.session_state.user = None

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
    with tab2:
        with st.form("signup"):
            new_email = st.text_input("New Email")
            new_pw = st.text_input("New Password", type="password")
            if st.form_submit_button("Sign Up"):
                try:
                    get_client().auth.sign_up({"email": new_email, "password": new_pw})
                    st.success("Check your email for a confirmation link!")
                except Exception as e:
                    st.error(f"Signup failed: {e}")
    st.stop() # Freeze the app here if not logged in

# --- 3. DATA LOADING ---
# If we reach here, the user is logged in
try:
    raw_data = get_client().table("plants").select("*").eq("user_id", st.session_state.user.id).execute().data
    df = pd.DataFrame(raw_data)
    total_plants = len(raw_data)
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

# --- 4. DASHBOARD UI ---
st.title("🪴 My Plant Garden")
st.markdown(f"### Total Plants: **{total_plants}**")

if st.sidebar.button("Logout"):
    st.session_state.user = None
    st.rerun()

# --- 5. WATERING & SNOOZE SECTION ---
if not df.empty:
    # Filter for active plants (not deceased)
    # Note: Ensure you have a 'status' column in Supabase with default 'active'
    df_active = df[df.get('status', 'active') != 'deceased'].sort_values('name')
    
    with st.expander("🚿 Plants to Water", expanded=True):
        for index, row in df_active.iterrows():
            with st.container(border=True):
                cols = st.columns([2, 0.6, 0.6], gap="small", vertical_alignment="center")
                
                with cols[0]:
                    st.markdown(f"**{row['name']}**")
                    st.caption(f"Last watered: {row.get('last_watered', 'Never')}")
                
                with cols[1]:
                    if st.button("💧", key=f"w_{row['id']}"):
                        today_str = str(date.today())
                        get_client().table("plants").update({
                            "last_watered": today_str,
                            "snooze_date": None
                        }).eq("id", row['id']).execute()
                        
                        # Log to History table
                        get_client().table("plant_logs").insert({
                            "plant_id": row['id'],
                            "user_id": st.session_state.user.id,
                            "date_watered": today_str
                        }).execute()
                        
                        st.toast(f"{row['name']} watered!")
                        st.rerun()

                with cols[2]:
                    if st.button("😴", key=f"s_{row['id']}"):
                        reappear = (date.today() + timedelta(days=2)).isoformat()
                        get_client().table("plants").update({"snooze_date": reappear}).eq("id", row['id']).execute()
                        st.rerun()
else:
    st.info("Your garden is empty. Add your first plant below!")

# --- 6. ADD NEW PLANT ---
with st.expander("➕ Add a New Plant"):
    with st.form("add_plant_form", clear_on_submit=True):
        new_name = st.text_input("Plant Name")
        new_freq = st.number_input("Watering Frequency (Days)", min_value=1, value=7)
        if st.form_submit_button("Add to Collection"):
            if new_name:
                get_client().table("plants").insert({
                    "name": new_name,
                    "frequency": int(new_freq),
                    "user_id": st.session_state.user.id,
                    "status": "active"
                }).execute()
                st.rerun()

# --- 7. CEMETERY ---
st.divider()
with st.expander("💀 Plant Cemetery"):
    if not df.empty:
        living_plants = df[df.get('status', 'active') != 'deceased']
        if not living_plants.empty:
            selected_rip = st.selectbox("Move to cemetery:", living_plants['name'].tolist(), index=None)
            if selected_rip and st.button("Confirm RIP", type="primary"):
                get_client().table("plants").update({"status": "deceased"}).eq("name", selected_rip).eq("user_id", st.session_state.user.id).execute()
                st.rerun()
        
        # Display deceased plants
        deceased_df = df[df.get('status') == 'deceased']
        if not deceased_df.empty:
            st.write("### Rest in Peace:")
            st.dataframe(deceased_df[['name', 'last_watered']], hide_index=True)
