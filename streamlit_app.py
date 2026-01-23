import streamlit as st
from streamlit_gsheets import GSheetsConnection
from datetime import date
import pandas as pd

# 1. Establish connection and read data
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl=0)

# Calculate total count
total_plants = len(df) if not df.empty else 0

# 2. Updated Title
st.title(f"🪴 My Plant Garden")
st.markdown(f"### You have **{total_plants}** total plants in your collection")

# 1. Connection to Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read()

# 2. Form to Add a New Plant
with st.expander("➕ Add a New Plant"):
    with st.form("new_plant_form", clear_on_submit=True):
        new_name = st.text_input("Plant Name")
        new_acq = st.date_input("Acquisition Date", format="MM/DD/YYYY")
        new_water = st.date_input("Last Watered Date", format="MM/DD/YYYY")
        
        if st.form_submit_button("Add to Collection"):
            if new_name:
                new_row = pd.DataFrame([{
                    "Plant Name": new_name, 
                    "Acquisition Date": new_acq.strftime("%m/%d/%Y"), 
                    "Last Watered Date": new_water.strftime("%m/%d/%Y")
                }])
                df = pd.concat([df, new_row], ignore_index=True)
                conn.update(data=df)
                st.success(f"Added {new_name}!")
                st.rerun()
            else:
                st.error("Please enter a name.")

st.divider()
        
st.subheader("🚿 Plants to Water")

today_str = date.today().strftime("%m/%d/%Y")

# 1. READ (ttl=0 ensures we don't see old data)
df = conn.read(ttl=0)

if not df.empty:
    # 2. SANITIZE (Prevents format mismatches)
    df['Last Watered Date'] = df['Last Watered Date'].astype(str).str.strip()
    df['Snooze Date'] = df.get('Snooze Date', pd.Series([""] * len(df))).astype(str).str.strip()

    # 3. FILTER
    mask = (df['Last Watered Date'] != today_str) & (df['Snooze Date'] != today_str)
    needs_action_df = df[mask]

    # 4. LOOP
# 1. Determine if 24 hours have passed
# Ensure you have a 'Last AI Update' cell or a way to track time. 
# For simplicity, we'll use Streamlit's cache with a 24h TTL.

@st.cache_data(ttl=86400) # 86400 seconds = 24 hours
def get_ai_advice(plant_list):
    prompt = f"Given these plants: {plant_list}, give a 1-sentence tip on watering them today."
    # Replace this with your actual AI call logic
    response = st.write("Generating fresh AI advice...") 
    return "Keep the soil moist but not soggy for your tropicals today!"

# 2. Display Advice
if not needs_action_df.empty:
    plant_names = ", ".join(needs_action_df['Plant Name'].tolist())
    advice = get_ai_advice(plant_names)
    
    with st.chat_message("assistant"):
        st.write(advice)
        
if not needs_action_df.empty:
    for index, row in needs_action_df.iterrows():
        with st.container(border=True):
            # Back to one row: [Name, Button 1, Button 2]
            cols = st.columns([2, 0.6, 0.6], gap="small", vertical_alignment="center")
            
            with cols[0]:
                st.markdown(f"🪴 **{row['Plant Name']}**")
            
            with cols[1]:
                if st.button("💧", key=f"w_{index}"):
                    df.at[index, 'Last Watered Date'] = today_str
                    conn.update(data=df)
                    st.cache_data.clear()
                    st.rerun()
                    
            with cols[2]:
                if st.button("😴", key=f"s_{index}"):
                    df.at[index, 'Snooze Date'] = today_str
                    conn.update(data=df)
                    st.cache_data.clear()
                    st.rerun()
                    st.cache_data.clear()
                    st.rerun()
else:
    st.success("All plants are watered or snoozed! ✨")
