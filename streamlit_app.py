import time # Add this at the very top with your imports
import streamlit as st
from streamlit_gsheets import GSheetsConnection
from datetime import date, timedelta, datetime  # Added datetime here
import pandas as pd

st.warning("⚠️ YOU ARE IN THE DEVELOPMENT ENVIRONMENT")
# 1. Initialize Session State (at the very top)
st.set_page_config(page_title="Plant Garden", page_icon="🪴")
if 'water_expanded' not in st.session_state:
    st.session_state.water_expanded = False


conn = st.connection("gsheets", type=GSheetsConnection)

# 1. Check if we already have the data in memory (Session State)
if 'df' not in st.session_state:
    try:
        # If not in memory, fetch it from Google once
        st.session_state.df = conn.read(ttl=0) 
    except Exception as e:
        # If Google fails, show the error and stop
        st.error("🚦 Whoa, slow down lady! Not even Google works that fast. Please refresh in 1 minute.")
        st.stop()

# 2. Always set 'df' to the version in memory for the rest of the script
df = st.session_state.df


# Force types immediately after loading
df['Last Watered Date'] = df['Last Watered Date'].astype(str)
df['Frequency'] = pd.to_numeric(df['Frequency'], errors='coerce').fillna(7)

# Ensure columns exist
for col in ['Frequency', 'Snooze Date', 'Last Watered Date', 'Plant Name', 'Dismissed Gap']:
    if col not in df.columns:
        df[col] = ""

total_plants = len(df) if not df.empty else 0
today = date.today()
today_str = today.strftime("%m/%d/%Y")

# 2. Header
st.title("🪴 My Plant Garden")
st.markdown(f"### Total Plants: **{total_plants}**")

def needs_water(row):
    try:
        today = datetime.now().date()
        
        # 1. Check Snooze Date first
        snooze_val = row.get('Snooze Date')
        if pd.notna(snooze_val) and snooze_val != "":
            snooze_dt = pd.to_datetime(snooze_val, errors='coerce').date()
            if pd.notna(snooze_dt) and snooze_dt > today:
                return False  # Hide if snoozed for the future
        
        # 2. Check Watering Frequency
        last_val = row.get('Last Watered Date')
        last_dt = pd.to_datetime(last_val, errors='coerce').date()
        
        if pd.isna(last_dt):
            return True # Needs water if never watered
            
        frequency = int(row['Frequency'])
        days_since = (today - last_dt).days
        
        return days_since >= frequency
    except:
        return True

#needs_action_df = df[df.apply(needs_water, axis=1
needs_action_df = df[df.apply(needs_water, axis=1)].sort_values(by='Plant Name')                           
count_label = f"({len(needs_action_df)})" if not needs_action_df.empty else ""

with st.expander(f"🚿 Plants to Water {count_label}", expanded=st.session_state.water_expanded):
    if not needs_action_df.empty:
        for index, row in needs_action_df.iterrows():
            with st.container(border=True):
                cols = st.columns([2, 0.6, 0.6], gap="small", vertical_alignment="center")
                with cols[0]:
                    st.markdown(f"**{row['Plant Name']}** — {row['Acquisition Date']}")
                    st.markdown(f"Last Watered on {row['Last Watered Date']}")
                    st.caption(f"Due every {row['Frequency']} days")
                with cols[1]:
                    if st.button("💧", key=f"w_{index}"):
                        st.session_state.water_expanded = True
                        
                        # 1. Update the local Dataframe
                        st.session_state.df.at[index, 'Last Watered Date'] = today_str
                        st.session_state.df.at[index, 'Snooze Date'] = "" 
                        
                        try:
                            # 2. Update Main Sheet
                            conn.update(data=st.session_state.df)
                            
                            # 3. Log to History
                            time.sleep(2) # Breath for the API
                            history_df = conn.read(worksheet="History", ttl="0")
                            new_log = pd.DataFrame([{
                                "Plant Name": row['Plant Name'], 
                                "Date Watered": today_str, 
                                "Acquisition Date": row['Acquisition Date']
                            }])
                            conn.update(worksheet="History", data=pd.concat([history_df, new_log], ignore_index=True))
                            
                            # 4. Success Toast
                            st.toast(f"Success! {row['Plant Name']} has been watered. 🌊", icon="🪴")
                            
                            time.sleep(0.5) # Let them see the toast for a split second
                            st.rerun()
                            
                        except Exception as e:
                            st.error("🚦 Whoa, slow down lady! Not even Google works that fast. Please refresh in 1 minute.")
        
                with cols[2]:
                    if st.button("😴", key=f"s_{index}"):
                        st.session_state.water_expanded = True
                        reappear_date = (today + timedelta(days=2)).strftime("%m/%d/%Y")
                        st.session_state.df.at[index, 'Snooze Date'] = reappear_date
                        try:
                            # 2. Push to Google using the session state data
                            conn.update(data=st.session_state.df)            
                            # 3. Give the API a tiny 'breath' before the rerun
                            time.sleep(0.5) 
                            st.rerun()
                        except Exception as e:
                            # 3. If Google is busy, we still rerun so the plant vanishes locally
                            st.rerun()            
        except Exception as e:
            # If Google blocks us, the change is still in local memory!
            # We rerun anyway so the user sees the plant disappear.
            st.warning("🚦 Google is busy, but I've saved your snooze locally.")
            time.sleep(1)
            st.rerun()
    else:
        st.success("All plants are watered! ✨")

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
with st.expander("💀 Plant Cemetery (Remove a Plant)"):
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
        
# 4. Processing & Display
if not df.empty:
    # Safely convert dates
    df['Last Watered Date'] = pd.to_datetime(df['Last Watered Date'], errors='coerce').dt.date
    df['Frequency'] = pd.to_numeric(df['Frequency'], errors='coerce').fillna(7).astype(int)
    df['Unique Label'] = df['Plant Name'] + " (" + df['Acquisition Date'].astype(str) + ")"

    # Section 5: Full Collection
    st.divider()
    with st.expander("📋 View Full Collection"):
        if not df.empty:
            # Alphabetical list for the dropdown
            all_plants = df.sort_values(by='Plant Name')
            
            # 1. Manual Update UI
            st.write("### ⚡ Quick Update")
            col1, col2 = st.columns([0.7, 0.3])
            
            # Dropdown to select ANY plant
            selected_plant_label = col1.selectbox(
                "Select a plant to mark as watered:",
                options=all_plants.apply(lambda r: f"{r['Plant Name']} ({r['Acquisition Date']})", axis=1)
            )
            
            if col2.button("💧 Water Now", use_container_width=True):
                # Find the actual index in the original dataframe
                p_name = selected_plant_label.split(" (")[0]
                p_acq = selected_plant_label.split(" (")[1].replace(")", "")
                
                idx = df[(df['Plant Name'] == p_name) & (df['Acquisition Date'] == p_acq)].index[0]
                
                # Update and Log
                df.at[idx, 'Last Watered Date'] = datetime.now().strftime("%m/%d/%Y")
                conn.update(data=df)
                
                # Log to History
                history_df = conn.read(worksheet="History", ttl=0)
                new_log = pd.DataFrame([{"Plant Name": p_name, "Acquisition Date": p_acq, "Date Watered": today_str}])
                conn.update(worksheet="History", data=pd.concat([history_df, new_log], ignore_index=True))
                
                st.success(f"Updated {p_name}!")
                st.rerun()
    
        df_view = df.copy().sort_values(by='Plant Name')
        #df_view = df.copy()
        df_view['Next Water'] = df_view.apply(
            lambda r: r['Last Watered Date'] + timedelta(days=r['Frequency']) 
            if pd.notna(r['Last Watered Date']) else "Needs Date", axis=1
        )
        st.dataframe(df_view[['Plant Name', 'Frequency', 'Last Watered Date', 'Next Water']], 
                     use_container_width=True, hide_index=True)
# 6. Smart Frequency Analysis

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
