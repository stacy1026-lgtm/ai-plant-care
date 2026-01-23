import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date

# Set page config for mobile-friendly view
st.set_page_config(page_title="Plant Care", layout="centered")

st.title("🪴 Plant Care Tracker")

# 1. Establish connection and read data
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl=0)

# 2. Setup date and cleaning
today_str = date.today().strftime("%d/%m/%Y")

if not df.empty:
    # Ensure columns are strings and stripped of spaces
    df['Last Watered Date'] = df['Last Watered Date'].astype(str).str.strip()
    df['Snooze Date'] = df.get('Snooze Date', pd.Series([""] * len(df))).astype(str).str.strip()

    # 3. Filter: Only show plants NOT watered or snoozed TODAY
    mask = (df['Last Watered Date'] != today_str) & (df['Snooze Date'] != today_str)
    needs_action_df = df[mask]

    st.subheader("🚿 Action Required")

    if not needs_action_df.empty:
        for index, row in needs_action_df.iterrows():
            # Container for the 'card' look
            with st.container(border=True):
                # Tight ratios and extra-small gap for mobile one-line display
                cols = st.columns([2, 0.6, 0.6], gap="small", vertical_alignment="center")
                
                with cols[0]:
                    st.markdown(f"**{row['Plant Name']}**")
                
                with cols[1]:
                    if st.button("💧", key=f"w_{index}", help="Watered"):
                        df.at[index, 'Last Watered Date'] = today_str
                        conn.update(data=df)
                        st.cache_data.clear()
                        st.rerun()
                        
                with cols[2]:
                    if st.button("😴", key=f"s_{index}", help="Snooze"):
                        df.at[index, 'Snooze Date'] = today_str
                        conn.update(data=df)
                        st.cache_data.clear()
                        st.rerun()
    else:
        st.success("All plants are watered or snoozed! ✨")

# Optional: Add a section to view all plants/
