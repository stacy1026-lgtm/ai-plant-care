import streamlit as st
import pandas as pd
from supabase import create_client
import time
import pytz
from datetime import date, timedelta, datetime
import pandas as pd

st.set_page_config(page_title="Plant Garden", page_icon="🪴", layout="wide")

# Add this block for the custom icon and 'standalone' mobile view
st.markdown("""
    <link rel="apple-touch-icon" href="https://raw.githubusercontent.com/stacy1026-lgtm/ai-plant-care/main/app_icon_180x180.png">
    
    <meta name="apple-mobile-web-app-capable" content="yes">
    
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    
    <link rel="icon" type="image/png" href="https://raw.githubusercontent.com/stacy1026-lgtm/ai-plant-care/main/app_icon_180x180.png">
""", unsafe_allow_html=True)



# 1. Calculate both times
local_tz = pytz.timezone('US/Eastern') 
#Uncomment the line below and the display to show and test date and times
#test_time = datetime(2026, 3, 6, 1, 0, tzinfo=local_tz)
now_local = datetime.now(local_tz)
#Uncomment the line below and the display to show and test date and times
#now_local = test_time
today_local = now_local.date()
now_server = datetime.now() # Server defaults to UTC

# 2. Display in two clean columns
#col_time1, col_time2 = st.columns(2)

#with col_time1:
#    st.metric("🏠 Your Local Time", today_local.strftime("%I:%M %p"))
#    st.caption(now_local.strftime("%A, %b %d"))

#with col_time2:
#    st.metric("☁️ Server Time (UTC)", now_server.strftime("%I:%M %p"))
#    st.caption(now_server.strftime("%A, %b %d"))

#st.divider()

# --- 1. CONFIG & INITIALIZATION ---
st.set_page_config(page_title="Plant Garden", page_icon="🪴")

@st.cache_resource
def get_client():
    return create_client(st.secrets["url"], st.secrets["key"])

supabase = get_client()

# --- 2. SILENT AUTHENTICATION ---
if "user" not in st.session_state:
    try:
        # Perform the login behind the scenes
        res = supabase.auth.sign_in_with_password({
            "email": st.secrets["MY_USER_EMAIL"], 
            "password": st.secrets["MY_USER_PASSWORD"]
        })
        st.session_state.user = res.user
        # Link the session token to the client so RLS works
        supabase.postgrest.auth(res.session.access_token)
    except Exception as e:
        st.error(f"Silent login failed: {e}")
        st.stop()

user = st.session_state.user

# --- 3. DATA LOADING LOGIC ---
def load_data():
    client = supabase
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
total_count = supabase.table("plants").select("*", count="exact").execute().count
st.markdown(f"### Total Plants: **{total_count}**")

# --- 5. PLANT ACTIONS ---
res = supabase.from_("plants_due_for_water").select("*").execute()
df_due = pd.DataFrame(res.data)
total_due = len(df_due)

with st.expander(f"🚿 Plants to Water ({total_due})", expanded=True):
    if not df_due.empty:
        for _, row in df_due.iterrows():
            with st.container(border=True):
                # Plant Info Header
                st.markdown(f"### {row['name']}")
                st.caption(f"📅 Acquired: {row['acquisition_date']} | 🔄 Every {row.get('frequency')} days")
                st.markdown(f"Last watered: **{row.get('last_watered') or 'Never'}**")
                
                # Full-width Button Row
                # We use two columns here so the buttons sit side-by-side, 
                # but they will each fill 50% of the screen width.
                btn_col1, btn_col2 = st.columns(2)
                
                with btn_col1:
                    if st.button(f"💧 Water", key=f"w_{row['id']}", use_container_width=True):
                        supabase.table("plant_logs").insert({
                            "plant_id": row['id'],
                            "last_watered": str(today_local),
                        }).execute()
                        
                        supabase.table("plants").update({
                            "snooze_date": None
                        }).eq("id", row['id']).execute()
                        
                        st.toast(f"Watered {row['name']}!")
                        st.rerun()

                with btn_col2:
                    if st.button(f"😴 Snooze", key=f"s_{row['id']}", use_container_width=True):
                        snooze_until = str(today_local + timedelta(days=2))
                        supabase.table("plants").update({
                            "snooze_date": snooze_until
                        }).eq("id", int(row['id'])).execute()
                        
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
                    "user_id": st.session_state.user.id
                }).execute()
                
                st.success(f"Added {new_name}!")
                st.rerun() # The trigger runs now; the UI refreshes immediately
            else:
                st.warning("Please enter a plant name.")

# --- 7. REMOVAL (CEMETERY) ---
st.divider()
data = supabase.table("plants").select("*").eq("user_id", st.session_state.user.id).execute().data
df = pd.DataFrame(data)

if not df.empty:
    df = df.sort_values(by='name', ascending=True)
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
                    supabase.table("plant_logs").delete().eq("plant_id", int(target['id'])).execute()
                    supabase.table("plants").delete().eq("id", int(target['id'])).execute()
                    
                    st.success(f"{target['name']} removed from your collection.")
                    st.rerun()

with st.expander("📋 View Full Collection"):
    # 1. Fetch data
    res = supabase.from_("plant_status_view").select("*").execute()
    df_view = pd.DataFrame(res.data)

    if not df_view.empty:
        # Pre-process dates (handling out-of-bounds with coerce)
        df_view = df_view.sort_values(by='name', ascending=True)
        df_view['last_watered'] = pd.to_datetime(df_view['last_watered'], errors='coerce')
        df_view['snooze_date'] = pd.to_datetime(df_view['snooze_date'], errors='coerce')

        # Calculation
        due_date = df_view['last_watered'] + pd.to_timedelta(df_view['frequency'], unit='D')
        df_view['next_watered'] = due_date.combine(df_view['snooze_date'], max)
        
        # 2. Quick Update Section
        st.subheader("⚡ Quick Update")
        col1, col2 = st.columns([3, 1], vertical_alignment="bottom")
        
        with col1:
            # Now correctly using df_view
            selected_plant = st.selectbox(
                "Select the plant to water:",
                options=df_view['name'].tolist(),
                index=None,
                placeholder="Type plant name..."
            )
        
        with col2:
            if st.button("💧 Water Now", type="primary"):
                if selected_plant:
                    # Now correctly using df_view
                    target = df_view[df_view['name'] == selected_plant].iloc[0]
                    supabase.table("plant_logs").insert({
                        "plant_id": int(target['id']),
                        "last_watered": str(today_local)
                    }).execute()
                    
                    # Optional: reset snooze
                    supabase.table("plants").update({"snooze_date": None}).eq("id", int(target['id'])).execute()
                    
                    st.toast(f"Watered {selected_plant}!")
                    st.rerun()
                else:
                    st.warning("Please select a plant first.")

        # 3. Table Display
        # Format for display: drop the index, keep data
        display_df = df_view[['name', 'frequency', 'last_watered', 'next_watered']].copy()
        
        # Ensure dates are formatted for display
        display_df['last_watered'] = display_df['last_watered'].dt.date
        display_df['next_watered'] = display_df['next_watered'].dt.date

        display_df.columns = ['Plant Name', 'Frequency', 'Last Watered', 'Next Water']
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.write("No plants found.")


        
# --- VIEW FULL COLLECTION ---
with st.expander("📊 Smart Frequency Analysis", expanded=False):
    try:
        # Fetch care history from Supabase
        logs_res = supabase.table("plant_logs").select("*").execute()
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
                                        supabase.table("plants").update({
                                            "frequency": avg_gap,
                                            "dismissed_gap": 0
                                        }).eq("id", int(p_id)).execute()
                                        st.rerun()
                                        
                                with btn_cols[1]:
                                    if st.button("✖️", key=f"ignore_{p_id}"):
                                        supabase.table("plants").update({
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
