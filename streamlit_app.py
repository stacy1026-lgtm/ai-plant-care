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
    client = get_client()
    uid = st.session_state.user.id

    # Fetch the pre-calculated view
    # Note: Ensure the view includes user_id if you need to filter by it
    res = client.from_("plant_status_view").select("*").execute()
    df = pd.DataFrame(res.data)
    
    if df.empty:
        return df

    # Convert dates for the filtering logic
    df['snooze_date'] = pd.to_datetime(df['snooze_date'], errors='coerce')
    
    # Filter out snoozed plants (keep if NaT or date in past)
    today = pd.Timestamp(date.today())
    is_not_snoozed = (df['snooze_date'].isna()) | (df['snooze_date'] <= today)
    
    return df[is_not_snoozed]

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
                        # 1. Add care entry to logs (Remove user_id from here)
                        get_client().table("plant_logs").insert({
                            "plant_id": row['id'],
                            "last_watered": str(date.today()),
                        }).execute()
                        
                        # 2. Clear any existing snooze on the plant itself
                        get_client().table("plants").update({
                            "snooze_date": None
                        }).eq("id", row['id']).execute()
                        
                        st.toast(f"Watered {row['name']}!")
                        st.rerun()

                with cols[2]:
                    if st.button("😴", key=f"s_{row['id']}"):
                        snooze_until = str(date.today() + timedelta(days=2))
                        # Update the 'plants' table directly for the specific plant ID
                        get_client().table("plants").update({
                            "snooze_date": snooze_until
                        }).eq("id", row['id']).execute()
                        
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
data = get_client().table("plants").select("*").eq("user_id", st.session_state.user.id).execute().data
df = pd.DataFrame(data)
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

with st.expander("📋 View Full Collection"):
    # 1. Fetch data
    data = get_client().table("plants").select("*").eq("user_id", st.session_state.user.id).execute().data
    df = pd.DataFrame(data)

    if not df.empty:
        # 2. Quick Update Section
        st.subheader("⚡ Quick Update")
        col1, col2 = st.columns([3, 1], vertical_alignment="bottom")
        
        # Use the name directly for the dropdown
        with col1:
            selected_plant = st.selectbox(
                "Select the plant to water:",
                options=df['name'].tolist(),
                index=None,
                placeholder="Type plant name..."
            )
        
        with col2:
            if st.button("💧 Water Now", type="primary"):
                if selected_plant:
                    # Find the row for the selected plant name
                    target = df[df['name'] == selected_plant].iloc[0]
                    get_client().table("plant_logs").insert({
                        "plant_id": int(target['id']),  # Force Python int
                        "id": str(st.session_state.id), # Force as string
                        "last_watered": str(date.today())
                    }).execute()
                    st.toast(f"Watered {selected_plant}!")
                    st.rerun()
                else:
                    st.warning("Please select a plant first.")

        # 3. Table Display
        st.table(df[['name', 'frequency']])
    else:
        st.write("No plants found.")            
# --- VIEW FULL COLLECTION ---
with st.expander("📊 Smart Frequency Analysis", expanded=False):
    try:
        # Fetch care history from Supabase
        logs_res = get_client().table("plant_logs").select("*").execute()
        hist = pd.DataFrame(logs_res.data)

        if not hist.empty and 'last_watered' in hist.columns:
            hist['last_watered'] = pd.to_datetime(hist['last_watered']).dt.date
            suggestions_found = False
            
            # Group by plant_id to analyze each individual plant's history
            for p_id, p_history in hist.groupby('plant_id'):
                p_dates = p_history['last_watered'].dropna().sort_values()
                
                # We need at least 3 waterings to establish a pattern
                if len(p_dates) >= 3:
                    avg_gap = int(p_dates.diff().mean().days)
                    
                    # Match this log data back to the main plant info
                    match = df[df['id'] == p_id]
                    
                    if not match.empty:
                        plant_row = match.iloc[0]
                        current_f = int(plant_row['frequency'])
                        
                        # Check if we've already ignored this specific average
                        d_val = plant_row.get('dismissed_gap', 0)
                        d_gap = int(d_val) if pd.notnull(d_val) else 0
                        
                        if avg_gap != current_f and avg_gap != d_gap:
                            suggestions_found = True
                            
                            # --- UI CARD START ---
                            with st.container(border=True):
                                st.subheader(plant_row['name'])
                                # Displaying Acquisition Date as the "ID" per your screenshot
                                st.caption(f"ID: {plant_row['acquisition_date']}")
                                
                                st.markdown(f"Average: **{avg_gap} days** (Current: {current_f}d)")
                                
                                # Buttons row
                                btn_cols = st.columns([1, 1, 4]) 
                                
                                with btn_cols[0]:
                                    if st.button("✔️", key=f"accept_{p_id}"):
                                        get_client().table("plants").update({
                                            "frequency": avg_gap,
                                            "dismissed_gap": 0
                                        }).eq("id", int(p_id)).execute()
                                        st.rerun()
                                        
                                with btn_cols[1]:
                                    if st.button("✖️", key=f"ignore_{p_id}"):
                                        get_client().table("plants").update({
                                            "dismissed_gap": avg_gap
                                        }).eq("id", int(p_id)).execute()
                                        st.rerun()
                            # --- UI CARD END ---
            
            if not suggestions_found:
                st.write("Frequencies match your habits!")
        else:
            st.info("Log 3+ waterings per plant for insights.")
    except Exception as e:
        st.error(f"Analysis Error: {e}")
