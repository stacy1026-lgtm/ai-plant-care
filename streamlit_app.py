import streamlit as st
from streamlit_gsheets import GSheetsConnection
from datetime import date, timedelta, datetime  # Added datetime here
import pandas as pd
from datetime import timedelta

st.warning("⚠️ YOU ARE IN THE DEVELEPMENT ENVIRONMENT")
# 1. Initialize Session State (at the very top)
if 'water_expanded' not in st.session_state:
    st.session_state.water_expanded = False

st.set_page_config(page_title="Plant Garden", page_icon="🪴")
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl=0)

# Ensure columns exist
for col in ['Frequency', 'Snooze Date', 'Last Watered Date', 'Plant Name', 'Dismissed Gap']:
    if col not in df.columns:
        df[col] = ""

total_plants = len(df) if not df.empty else 0
today = date.today()
today_str = today.strftime("%m/%d/%Y")

def needs_water(row):
    try:
        last_watered = pd.to_datetime(row['Last Watered Date']).date()
        freq = int(row['Frequency'])
        days_since = (datetime.now().date() - last_watered).days
        return days_since >= freq
    except:
        return True

# 2. Header
st.title("🪴 My Plant Garden")
st.markdown(f"### Total Plants: **{total_plants}**")

# 3. Add New Plant
with st.expander("➕ Add a New Plant"):
    with st.form("new_plant_form", clear_on_submit=True):
        new_name = st.text_input("Plant Name")
        new_freq = st.number_input("Watering Frequency (Days)", min_value=1, value=7)
        new_acq = st.date_input("Acquisition Date", format="MM/DD/YYYY")
        new_water = st.date_input("Last Watered Date", format="MM/DD/YYYY")
        
        if st.form_submit_button("Add to Collection"):
            if new_name:
                new_row = pd.DataFrame([{
                    "Plant Name": new_name, 
                    "Frequency": int(new_freq),
                    "Acquisition Date": new_acq.strftime("%m/%d/%Y"), 
                    "Last Watered Date": new_water.strftime("%m/%d/%Y"),
                    "Snooze Date": "",
                    "Dismissed Gap": 0  # <--- Defaults to 0 in the database
                }])
                df = pd.concat([df, new_row], ignore_index=True)
                conn.update(data=df)
                st.rerun()
                
# 3.5 Delete / RIP Plant
with st.expander("🥀 Plant Cemetery (Remove a Plant)"):
    if not df.empty:
        df_delete = df.copy()
        df_delete['Display'] = df_delete['Plant Name'] + " (Acquired: " + df_delete['Acquisition Date'].astype(str) + ")"
        
        selected_label = st.selectbox(
            "Select the plant that didn't make it:",
            options=df_delete['Display'].tolist(),
            index=None,
            placeholder="Type plant name..."
        )
        
        if selected_label:
            idx_to_remove = df_delete[df_delete['Display'] == selected_label].index[0]
            plant_name = df_delete.at[idx_to_remove, 'Plant Name']
            
            # Additional detail for the history log
            reason = st.text_input("What happened? (e.g., Overwatered, Pests, Light)", placeholder="Optional")
            
            st.warning(f"Removing **{plant_name}** from your collection.")
            
            if st.button("Confirm Removal", type="primary"):
                # 1. Log to Graveyard tab
                try:
                    grave_df = conn.read(worksheet="Graveyard", ttl=0)
                    death_entry = pd.DataFrame([{
                        "Plant Name": plant_name,
                        "Acquired": df_delete.at[idx_to_remove, 'Acquisition Date'],
                        "RIP Date": today_str,
                        "Reason": reason
                    }])
                    updated_grave = pd.concat([grave_df, death_entry], ignore_index=True)
                    conn.update(worksheet="Graveyard", data=updated_grave)
                except:
                    st.info("Note: 'Graveyard' tab not found in Sheets, skipping the log.")

                # 2. Remove from main table
                df = df.drop(idx_to_remove)
                conn.update(data=df)
                st.success(f"{plant_name} moved to the cemetery.")
                st.rerun()
        
# Section 4: Water List
if not df.empty:
    action_df = df[df.apply(needs_water, axis=1)]
    
    with st.expander(f"🚿 Plants to Water ({len(action_df)})", expanded=True):
        if not action_df.empty:
            # Search Session State
            if "search_box" not in st.session_state:
                st.session_state.search_box = ""
            
            # 2. Create the Search UI
            s_col, c_col = st.columns([0.8, 0.2])
            
            # The "value" comes from session state
            search_query = s_col.text_input(
                "Search...", 
                value=st.session_state.search_box, 
                key="search_input_widget", # Internal key for the widget
                label_visibility="collapsed"
            )
            
            # When Clear is clicked, we reset the session state variable
            if c_col.button("Clear", use_container_width=True):
                st.session_state.search_box = "" # Reset variable
                st.rerun() # Refresh to empty the text box
            
            # 3. Update the variable with whatever is currently typed
            st.session_state.search_box = search_query
            
            # 4. Filter the list using the updated variable
            filtered_df = action_df[
                action_df['Plant Name'].str.lower().str.contains(st.session_state.search_box.lower())
            ].sort_values(by='Plant Name')

            # Display
            for index, row in filtered_df.iterrows():
                with st.container(border=True):
                    st.markdown(f"**{row['Plant Name']}**")
                    st.caption(f"Acquired: {row['Acquisition Date']}")
                    
                    if st.button("💧 Watered", key=f"w_{index}"):
                        df.at[index, 'Last Watered Date'] = datetime.now().strftime("%m/%d/%Y")
                        conn.update(data=df)
                        st.rerun()
        else:
            st.success("All plants are watered!")

    # Section 5: Full Collection
    with st.expander("📋 View Full Collection"):
        if not df.empty:
            df_view = df.copy()
            
            # 1. FIX THE DATE ERROR: Convert string to datetime objects
            df_view['Last Watered Date'] = pd.to_datetime(df_view['Last Watered Date']).dt.date
            
            # 2. CALC NEXT WATER: Now math works because both are date/number types
            df_view['Next Water'] = df_view.apply(
                lambda r: r['Last Watered Date'] + timedelta(days=int(r['Frequency']))
                if pd.notna(r['Last Watered Date']) else "Needs Date", 
                axis=1
            )
            
            # Sort and display
            st.dataframe(df_view.sort_values(by='Plant Name'), use_container_width=True)
        
# 6. Smart Frequency Analysis
    st.divider()
    with st.expander("📊 Smart Frequency Analysis", expanded=False):
        try:
            hist = conn.read(worksheet="History", ttl=0)
            if not hist.empty:
                # Ensure date conversion
                hist['Date Watered'] = pd.to_datetime(hist['Date Watered']).dt.date
                suggestions_found = False
                
                # Group by Name AND Acquisition Date to separate identical plants
                for (p_name, p_acq), p_history in hist.groupby(['Plant Name', 'Acquisition Date']):
                    p_dates = p_history['Date Watered'].sort_values()
                    
                    if len(p_dates) >= 3:
                        avg_gap = int((p_dates.diff().mean()).days)
                        
                        # Find specific plant in main df
                        match = df[(df['Plant Name'] == p_name) & (df['Acquisition Date'] == p_acq)]
                        
                        if not match.empty:
                            idx = match.index[0]
                            current_f = int(match['Frequency'].values[0])
                            # Handle dismissed gap
                            d_val = match.get('Dismissed Gap', [0]).values[0]
                            d_gap = int(d_val) if pd.notnull(d_val) else 0
                            
                            if avg_gap != current_f and avg_gap != d_gap:
                                suggestions_found = True
                                with st.container(border=True):
                                    st.write(f"### {p_name}")
                                    st.caption(f"ID: {p_acq}")
                                    st.write(f"Average: **{avg_gap} days** (Current: {current_f}d)")
                                    
                                    b_cols = st.columns([0.15, 0.15, 0.7])
                                    if b_cols[0].button("✔️", key=f"up_{idx}"):
                                        df.at[idx, 'Frequency'] = avg_gap
                                        df.at[idx, 'Dismissed Gap'] = 0 
                                        conn.update(data=df)
                                        st.rerun()
                                    if b_cols[1].button("✖️", key=f"no_{idx}"):
                                        df.at[idx, 'Dismissed Gap'] = avg_gap
                                        conn.update(data=df)
                                        st.rerun()
                
                if not suggestions_found:
                    st.write("Frequencies match your habits!")
            else:
                st.info("Log 3+ waterings per plant for insights.")
        except Exception as e:
            st.error(f"Analysis Error: {e}")

# --- LINE 220 ---
else: # This must be at the FAR LEFT (zero spaces)
    st.info("Your garden is empty.")
