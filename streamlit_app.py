import streamlit as st
import pandas as pd
from datetime import date, timedelta
from supabase import create_client

# --- 1. CONFIG & INITIALIZATION ---
st.set_page_config(page_title="Plant Garden", page_icon="🪴")

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
    st.stop()

# --- 3. DATA LOADING LOGIC ---
def load_data():
    today = date.today()
    client = get_client()
    uid = st.session_state.user.id

    # Fetch plants table
    p_res = client.table("plants").select("*").eq("user_id", uid).execute()
    df_plants = pd.DataFrame(p_res.data)
    
    if df_plants.empty:
        return df_plants

    # Fetch logs table for history
    try:
        l_res = client.table("plant_logs").select("*").eq("user_id", uid).execute()
        df_logs = pd.DataFrame(l_res.data)
        
        if not df_logs.empty:
            # Sort locally to avoid API ordering errors
            df_logs = df_logs.sort_values("last_watered", ascending=False)
            # Keep only the most recent entry for each plant
            latest_logs = df_logs.drop_duplicates(subset=["plant_id"])
            
            # Merge logs into the plants list
            df_plants = df_plants.merge(
                latest_logs[['plant_id', 'last_watered', 'snooze_date']], 
                left_on='id', 
                right_on='plant_id', 
                how='left'
            )
        else:
            df_plants['last_watered'] = None
            df_plants['snooze_date'] = None
    except:
        df_plants['last_watered'] = None
        df_plants['snooze_date'] = None

    # Filter out snoozed plants
    if 'snooze_date' in df_plants.columns:
            # Convert to datetime, coercing errors to NaT (Not a Time)
            df_plants['snooze_date'] = pd.to_datetime(df_plants['snooze_date'], errors='coerce')
            
            # Now compare date.today() (casted to timestamp) against the column
            today = pd.Timestamp(date.today())
            
            # Mask: keep if NaT (not snoozed) OR date is in the past
            is_not_snoozed = (df_plants['snooze_date'].isna()) | (df_plants['snooze_date'] <= today)
            df_plants = df_plants[is_not_snoozed]
        
    return df_plants

# Execute data load
df = load_data()

# --- 4. DASHBOARD UI ---
st.title("🪴 My Plant Garden")
st.markdown(f"### Total Plants: **{len(df)}**")

if st.sidebar.button("Logout"):
    st.session_state.user = None
    st.rerun()

# --- 5. PLANT ACTIONS ---
with st.expander("🚿 Plants to Water", expanded=True):
    if not df.empty:
        for _, row in df.iterrows():
            with st.container(border=True):
                cols = st.columns([2, 0.6, 0.6], vertical_alignment="center")
                
                with cols[0]:
                    st.markdown(f"**{row['name']}**")
                    st.caption(f"Last watered: {row.get('last_watered') or 'Never'}")
                
                with cols[1]:
                    if st.button("💧", key=f"w_{row['id']}"):
                        get_client().table("plant_logs").insert({
                            "plant_id": row['id'],
                            "user_id": st.session_state.user.id,
                            "last_watered": str(date.today()),
                            "snooze_date": None
                        }).execute()
                        st.toast(f"Watered {row['name']}!")
                        st.rerun()

                with cols[2]:
                    if st.button("😴", key=f"s_{row['id']}"):
                        snooze_until = str(date.today() + timedelta(days=2))
                        get_client().table("plant_logs").insert({
                            "plant_id": row['id'],
                            "user_id": st.session_state.user.id,
                            "snooze_date": snooze_until
                        }).execute()
                        st.rerun()
    else:
        st.info("No plants need attention right now.")

# --- 6. ADD NEW PLANT ---
with st.expander("➕ Add a New Plant"):
    with st.form("add_plant_form", clear_on_submit=True):
        new_name = st.text_input("Plant Name")
        new_freq = st.number_input("Watering Frequency (Days)", min_value=1, value=7)
        # Using exact spelling from your schema: 'acquisition_date'
        acq_date = st.date_input("Acquisition Date", value=date.today())
        
        if st.form_submit_button("Add to Collection"):
            if new_name:
                get_client().table("plants").insert({
                    "name": new_name,
                    "frequency": int(new_freq),
                    "acquisition_date": str(acq_date),
                    "user_id": st.session_state.user.id
                }).execute()
                st.rerun()

# --- 7. REMOVAL (CEMETERY) ---
st.divider()
if not df.empty:
    with st.expander("💀 Plant Cemetery (Remove a Plant)"):
        if not df.empty:
            # Create a copy to avoid mutating the original dataframe
            df_delete = df.copy()
            
            # Combine columns using the correct database field names
            df_delete['Display'] = (
                df_delete['name'] + 
                " (Acquired: " + 
                df_delete['acquisition_date'].astype(str) + 
                ")"
            )
            
            selected_label = st.selectbox(
                "Select the plant that didn't make it:",
                options=df_delete['Display'].tolist(),
                index=None,
                placeholder="Type plant name..."
            )
            
            # Action logic
            if selected_label:
                if st.button("Confirm Removal", type="primary"):
                    # Find the specific row by the display string
                    target = df_delete[df_delete['Display'] == selected_label].iloc[0]
                    
                    # Delete from Supabase
                    get_client().table("plant_logs").delete().eq("plant_id", int(target['id'])).execute()
                    get_client().table("plants").delete().eq("id", int(target['id'])).execute()
                    
                    st.success(f"{target['name']} removed from your collection.")
                    st.rerun()
            
# --- VIEW FULL COLLECTION ---
with st.expander("📋 View Full Collection"):
    # 1. Fetch data
    data = get_client().table("plants").select("*").eq("user_id", st.session_state.user.id).execute().data
    df = pd.DataFrame(data)

    if not df.empty:
        # 2. Quick Update Section
        st.subheader("⚡ Quick Update")
        col1, col2 = st.columns([3, 1], vertical_alignment="bottom")
        
        # Create a display name for the dropdown
        df['display'] = df['name']
        
        with col1:
            selected_label = st.selectbox(
                "Select the plant to water:",
                options=df_delete['Display'].tolist(),
                index=None,
                placeholder="Type plant name..."
            )
        
        with col2:
            if st.button("💧 Water Now", type="primary"):
                target = df[df['display'] == selected_plant_name].iloc[0]
                get_client().table("plant_logs").insert({
                    "plant_id": target['id'],
                    "user_id": st.session_state.user.id,
                    "last_watered": str(date.today())
                }).execute()
                st.rerun()

        # 3. Table Display
        st.table(df[['name', 'frequency']]) # Replace with your specific columns
    else:
        st.write("No plants found.")
# --- 6. SMART FREQUENCY ANALYSIS ---
with st.expander("📊 Smart Frequency Analysis", expanded=False):
    try:
        # Fetch logs from Supabase
        logs_res = get_client().table("plant_logs").select("*").eq("user_id", st.session_state.user.id).execute()
        hist = pd.DataFrame(logs_res.data)

        if not hist.empty and 'last_watered' in hist.columns:
            hist['last_watered'] = pd.to_datetime(hist['last_watered']).dt.date
            suggestions_found = False
            
            # Group by plant_id
            for p_id, p_history in hist.groupby('plant_id'):
                p_dates = p_history['last_watered'].dropna().sort_values()
                
                if len(p_dates) >= 3:
                    avg_gap = int(p_dates.diff().mean().days)
                    
                    # Find the specific plant in our main 'df'
                    match = df[df['id'] == p_id]
                    
                    if not match.empty:
                        idx = match.index[0]
                        current_f = int(match['frequency'].values[0])
                        
                        # Handle dismissed_gap (using your schema's column name)
                        d_val = match.get('dismissed_gap', [0]).values[0]
                        d_gap = int(d_val) if pd.notnull(d_val) else 0
                        
                        if avg_gap != current_f and avg_gap != d_gap:
                            suggestions_found = True
                            with st.container(border=True):
                                st.write(f"### {match['name'].values[0]}")
                                st.write(f"Average: **{avg_gap} days** (Current: {current_f}d)")
                                
                                b_cols = st.columns([0.15, 0.15, 0.7])
                                if b_cols[0].button("✔️ Accept", key=f"up_{p_id}"):
                                    get_client().table("plants").update({
                                        "frequency": avg_gap,
                                        "dismissed_gap": 0
                                    }).eq("id", p_id).execute()
                                    st.rerun()
                                if b_cols[1].button("✖️ Ignore", key=f"no_{p_id}"):
                                    get_client().table("plants").update({
                                        "dismissed_gap": avg_gap
                                    }).eq("id", p_id).execute()
                                    st.rerun()
            
            if not suggestions_found:
                st.write("Frequencies match your habits!")
        else:
            st.info("Log 3+ waterings per plant for insights.")
    except Exception as e:
        st.error(f"Analysis Error: {e}")
