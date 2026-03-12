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

# 1. Fetch raw data
raw_data = get_client().table("plants").select("*").eq("user_id", st.session_state.user.id).execute().data
total_plants = len(raw_data)
df = pd.DataFrame(raw_data)

# 2. ADD THESE TO DISPLAY
st.markdown(f"### Total Plants: **{total_plants}**")

if not df.empty:
    st.dataframe(df)
else:
    st.write("Your garden is empty!")

# Helper: Fetch Data
def load_data():
    plants = get_client().table("plants").select("*").eq("user_id", st.session_state.user.id).execute().data
    return pd.DataFrame(plants)

df = load_data()

def load_data():
    today = str(date.today())
    # Fetch all plants for the user
    res = get_client().table("plants").select("*").eq("user_id", st.session_state.user.id).execute().data
    all_plants = pd.DataFrame(res)
    
    if all_plants.empty:
        return all_plants

    # Filter out plants snoozed for the future
    # We use .fillna('') to handle rows where snooze_until is NULL
    is_not_snoozed = (all_plants['snooze_until'].isna()) | (all_plants['snooze_until'] <= today)
    return all_plants[is_not_snoozed]

df = load_data()

# 4. Watering Logic
with st.expander("🚿 Plants to Water", expanded=True):
    if not df.empty:
        for idx, row in df.iterrows():
            # Balanced columns for Name, Water, and Snooze
            cols = st.columns([2, 1, 1])
            
            cols[0].write(f"**{row['name']}**")
            
            # WATER BUTTON
            if cols[1].button("💧 Water", key=f"w_{row['id']}"):
                get_client().table("plants").update({
                    "last_watered": str(date.today()),
                    "snooze_until": None  # Reset snooze when watered
                }).eq("id", row['id']).execute()
                
                get_client().table("plant_logs").insert({
                    "plant_id": row['id'], 
                    "user_id": st.session_state.user.id
                }).execute()
                st.rerun()
            
            # SNOOZE BUTTON (Hides plant for 2 days)
            if cols[2].button("😴 Snooze", key=f"s_{row['id']}"):
                snooze_date = str(date.today() + timedelta(days=2))
                get_client().table("plants").update({
                    "snooze_until": snooze_date
                }).eq("id", row['id']).execute()
                st.toast(f"{row['name']} snoozed until {snooze_date}")
                st.rerun()
    else:
        st.write("All caught up! No plants need water right now.")

# 5. Add Plant
with st.expander("➕ Add Plant"):
    with st.form("add"):
        name = st.text_input("Name")
        freq = st.number_input("Frequency", value=7)
        if st.form_submit_button("Save"):
            get_client().table("plants").insert({"name": name, "frequency": freq, "user_id": st.session_state.user.id}).execute()
            st.rerun()

# 6. Cemetery
with st.expander("💀 Plant Cemetery"):
    if not df.empty:
        selection = st.selectbox("Select to remove:", df['name'])
        if st.button("Confirm Removal"):
            target = df[df['name'] == selection].iloc[0]
            get_client().table("plants").delete().eq("id", target['id']).execute()
            st.rerun()
