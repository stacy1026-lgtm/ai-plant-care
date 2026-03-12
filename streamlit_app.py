import streamlit as st
import pandas as pd
from datetime import date, timedelta

# --- 1. Data Fetching ---
raw_data = get_client().table("plants").select("*").eq("user_id", st.session_state.user.id).execute().data
total_plants = len(raw_data)
df = pd.DataFrame(raw_data)

# --- 2. Header ---
st.markdown(f"### Total Plants: **{total_plants}**")

# --- 3. Action Loop (Water & Snooze) ---
if not df.empty:
    # We sort by name for a clean UI
    df_active = df[df['status'] != 'deceased'].sort_values('name')
    
    for index, row in df_active.iterrows():
        with st.container(border=True):
            cols = st.columns([2, 0.6, 0.6], gap="small", vertical_alignment="center")
            
            with cols[0]:
                st.markdown(f"**{row['name']}**")
                st.caption(f"Last watered: {row['last_watered'] or 'Never'}")
            
            with cols[1]:
                # WATER BUTTON
                if st.button("💧", key=f"w_{row['id']}"):
                    today_str = str(date.today())
                    # Update Main Table
                    get_client().table("plants").update({
                        "last_watered": today_str,
                        "snooze_date": None
                    }).eq("id", row['id']).execute()
                    
                    # Log to History Table
                    get_client().table("plant_logs").insert({
                        "plant_id": row['id'],
                        "user_id": st.session_state.user.id,
                        "date_watered": today_str
                    }).execute()
                    
                    st.toast(f"{row['name']} watered! 🌊")
                    st.rerun()

            with cols[2]:
                # SNOOZE BUTTON
                if st.button("😴", key=f"s_{row['id']}"):
                    reappear = (date.today() + timedelta(days=2)).isoformat()
                    get_client().table("plants").update({
                        "snooze_date": reappear
                    }).eq("id", row['id']).execute()
                    st.rerun()

# --- 4. Plant Cemetery ---
st.divider()
with st.expander("💀 Plant Cemetery"):
    if not df.empty:
        # Filter for the dropdown
        living_plants = df[df['status'] != 'deceased']
        
        selected_plant = st.selectbox(
            "Select a plant to move to the cemetery:",
            options=living_plants['name'].tolist(),
            index=None,
            placeholder="Choose a plant..."
        )
        
        if selected_plant:
            if st.button("Confirm RIP", type="primary"):
                get_client().table("plants").update({
                    "status": "deceased"
                }).eq("name", selected_plant).eq("user_id", st.session_state.user.id).execute()
                st.success(f"{selected_plant} has been moved to the cemetery. 🥀")
                st.rerun()
