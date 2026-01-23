needs_action_df = df[mask]

# 4. LOOP
    if not needs_action_df.empty:
        for index, row in needs_action_df.iterrows():
           # cols = st.columns([2, 1, 1])
            cols = st.columns([1, 1, 1], gap="small")
   if not needs_action_df.empty:
    for index, row in needs_action_df.iterrows():
        # Using st.container with border=True for a card look
        with st.container(border=True):
            # Higher ratio (12:1:1) forces buttons closer together
            cols = st.columns([12, 1, 1], gap="small")
            
with cols[0]:
st.write(f"🪴 **{row['Plant Name']}**")
            
with cols[1]:
                if st.button("💧", key=f"w_{index}"):
                if st.button("💧", key=f"w_{index}", help="Mark as Watered"):
df.at[index, 'Last Watered Date'] = today_str
conn.update(data=df)
st.cache_data.clear()
st.rerun()
                    
with cols[2]:
                if st.button("😴", key=f"s_{index}"):
                if st.button("😴", key=f"s_{index}", help="Snooze for Today"):
df.at[index, 'Snooze Date'] = today_str
conn.update(data=df)
st.cache_data.clear()
st.rerun()
    else:
        st.success("All plants are watered or snoozed! ✨")
else:
    st.success("All plants are watered or snoozed! ✨")
