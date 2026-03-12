import streamlit as st
import pandas as pd
from datetime import date, timedelta
from supabase import create_client

# --- 1. CONFIG & AUTH ---
st.set_page_config(page_title="Plant Garden", page_icon="🪴")

def get_client():
    if "supabase" not in st.session_state:
        st.session_state.supabase = create_client(st.secrets["url"], st.secrets["key"])
    return st.session_state.supabase

if "user" not in st.session_state:
    st.session_state.user = None

# (Authentication block here... see previous responses for full login code)

# --- 2. DATA LOADING ---
def load_data():
    today = date.today()
    # Fetch plants
    p_res = get_client().table("plants").select("*").eq("user_id", st.session_state.user.id).execute()
    df_plants = pd.DataFrame(p_res.data)
    
    if df_plants.empty:
        return df_plants

    # Fetch latest logs for each plant to get last_watered and snooze_date
    l_res = get_client().table("plant_logs").select("*").eq("user_id", st.session_state.user.id).order("last_watered", desc=True).execute()
    df_logs = pd.DataFrame(l_res.data)

    if not df_logs.empty:
        # Get only the latest log per plant
        latest_logs = df_logs.drop_duplicates(subset=["plant_id"])
        # Merge log info into plants dataframe
        df_plants = df_plants.merge(latest_logs[['plant_id', 'last_watered', 'snooze_date']], 
                                    left_on='id', right_on='plant_id', how='left')
    else:
        df_plants['last_watered'] = None
        df_plants['snooze_date'] = None

    # Filter out snoozed plants
    df_plants['snooze_date'] = pd.to_datetime(df_plants['snooze_date']).dt.date
    is_not_snoozed = (df_plants['snooze_date'].isna()) | (df_plants['snooze_date'] <= today)
    
    return df_plants[is_not_snoozed]

df = load_data()

# --- 3. DASHBOARD ---
st.title("🪴 My Plant Garden")
st.markdown(f"### Total Plants: **{len(df)}**")

with st.expander("🚿 Plants to Water", expanded=True):
    if not df.empty:
        for idx, row in df.iterrows():
            cols = st.columns([2, 1, 1])
            cols[0].write(f"**{row['name']}**")
            
            # WATER BUTTON
            if cols[1].button("💧 Water", key=f"w_{row['id']}"):
                # Insert new log entry as per your schema
                get_client().table("plant_logs").insert({
                    "plant_id": row['id'],
                    "user_id": st.session_state.user.id,
                    "last_watered": str(date.today()),
                    "snooze_date": None
                }).execute()
                st.rerun()
            
            # SNOOZE BUTTON
            if cols[2].button("😴 Snooze", key=f"s_{row['id']}"):
                snooze_val = str(date.today() + timedelta(days=2))
                get_client().table("plant_logs").insert({
                    "plant_id": row['id'],
                    "user_id": st.session_state.user.id,
                    "snooze_date": snooze_val
                }).execute()
                st.rerun()
    else:
        st.write("All plants are watered or snoozed!")

# --- 4. ADD PLANT ---
with st.expander("➕ Add Plant"):
    with st.form("add"):
        name = st.text_input("Name")
        freq = st.number_input("Frequency (days)", value=7)
        acq_date = st.date_input("Acquisition Date", value=date.today())
        if st.form_submit_button("Save"):
            get_client().table("plants").insert({
                "name": name, 
                "frequency": freq, 
                "acquisition_date": str(acq_date),
                "user_id": st.session_state.user.id
            }).execute()
            st.rerun()
