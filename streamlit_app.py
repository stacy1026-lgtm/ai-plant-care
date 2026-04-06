import streamlit as st
import pandas as pd
from supabase import create_client
import pytz
from datetime import date, timedelta, datetime

# --- 1. CONFIG & INITIALIZATION ---
st.set_page_config(page_title="Plant Garden", page_icon="🪴")

# Define timezone once
local_tz = pytz.timezone('US/Eastern') 
now_local = datetime.now(local_tz)
today_local = now_local.date()

@st.cache_resource
def get_client():
    return create_client(
        st.secrets["url"], 
        st.secrets["key"]
    )

supabase = get_client()

# --- 2. SILENT AUTHENTICATION ---
# This replaces the entire Login/Sign-up tab UI
def perform_silent_login():
    if "user" not in st.session_state or st.session_state.user is None:
        try:
            res = supabase.auth.sign_in_with_password({
                "email": st.secrets["MY_USER_EMAIL"], 
                "password": st.secrets["MY_USER_PASSWORD"]
            })
            st.session_state.user = res.user
            # Crucial: Link the session to the client
            supabase.postgrest.auth(res.session.access_token)
        except Exception as e:
            st.error(f"Silent login failed: {e}")
            st.stop()

perform_silent_login()
user = st.session_state.user

# --- 3. DATA LOADING LOGIC ---
def load_data():
    # Fetch from the view (Ensure view has user_id for RLS)
    res = supabase.from_("plant_status_view").select("*").execute()
    df = pd.DataFrame(res.data)
    
    if df.empty:
        return df

    df['snooze_date'] = pd.to_datetime(df['snooze_date'], errors='coerce')
    today = pd.Timestamp(date.today())
    is_not_snoozed = (df['snooze_date'].isna()) | (df['snooze_date'] <= today)
    return df[is_not_snoozed]

# Execute data load
df_current = load_data()

# --- 4. DASHBOARD UI ---
st.title("🪴 My Plant Garden")

# Correctly scoped total count
total_res = supabase.table("plants").select("*", count="exact").execute()
st.markdown(f"### Total Plants: **{total_res.count}**")

# --- 5. PLANT ACTIONS (DUE FOR WATERING) ---
res_due = supabase.from_("plants_due_for_water").select("*").execute()
df_due = pd.DataFrame(res_due.data)

with st.expander(f"🚿 Plants to Water ({len(df_due)})", expanded=True):
    if not df_due.empty:
        for _, row in df_due.iterrows():
            with st.container(border=True):
                cols = st.columns([2, 0.6, 0.6], vertical_alignment="center")
                with cols[0]:
                    st.markdown(f"**{row['name']}**")
                    st.caption(f"Last watered: {row.get('last_watered') or 'Never'}")
                
                with cols[1]:
                    if st.button("💧", key=f"w_{row['id']}"):
                        supabase.table("plant_logs").insert({
                            "plant_id": row['id'],
                            "last_watered": str(today_local),
                        }).execute()
                        supabase.table("plants").update({"snooze_date": None}).eq("id", row['id']).execute()
                        st.toast(f"Watered {row['name']}!")
                        st.rerun()

                with cols[2]:
                    if st.button("😴", key=f"s_{row['id']}"):
                        snooze_until = str(today_local + timedelta(days=2))
                        supabase.table("plants").update({"snooze_date": snooze_until}).eq("id", row['id']).execute()
                        st.rerun()
    else:
        st.info("No plants need attention right now.")

# --- 6. ADD NEW PLANT ---
with st.expander("➕ Add a New Plant"):
    with st.form("add_plant_form", clear_on_submit=True):
        new_name = st.text_input("Plant Name")
        new_freq = st.number_input("Watering Frequency (Days)", min_value=1, value=7)
        acq_date = st.date_input("Acquisition Date", value=today_local)
        
        if st.form_submit_button("Add to Collection"):
            if new_name:
                supabase.table("plants").insert({
                    "name": new_name,
                    "frequency": int(new_freq),
                    "acquisition_date": str(acq_date),
                    "user_id": user.id
                }).execute()
                st.success(f"Added {new_name}!")
                st.rerun()

# --- 7. VIEW COLLECTION & ANALYSIS ---
with st.expander("📋 View Full Collection"):
    res_all = supabase.from_("plant_status_view").select("*").execute()
    df_all = pd.DataFrame(res_all.data)
    if not df_all.empty:
        st.dataframe(df_all[['name', 'frequency', 'last_watered']], use_container_width=True, hide_index=True)

with st.expander("📊 Smart Frequency Analysis"):
    st.write("Analysis logic goes here...")
