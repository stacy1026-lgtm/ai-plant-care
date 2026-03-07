import time # Add this at the very top with your imports
import streamlit as st
import pytz
from streamlit_gsheets import GSheetsConnection
from datetime import date, timedelta, datetime  # Added datetime here
import pandas as pd

from supabase import create_client, Client

# Initialize connection
url = "https://eeqdkamaxghssoxxqsxi.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVlcWRrYW1heGdoc3NveHhxc3hpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI5MDU1OTksImV4cCI6MjA4ODQ4MTU5OX0.aKi31CJeb_G9fRzkzjfNAgtcehBzoy5w2CgFdjSQRQM"
supabase: Client = create_client(url, key)

# Fetch data from your table
response = supabase.table("plants").select("*").execute()

# Convert to DataFrame
df = pd.DataFrame(response.data)

# Display in Streamlit
st.subheader("My Database Table")
st.dataframe(df)

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

st.warning("⚠️ YOU ARE IN THE SUPABASE DEVELOPMENT ENVIRONMENT")
# 1. Initialize Session State (at the very top)
st.set_page_config(page_title="Supabase Plant Garden", page_icon="🪴")

import streamlit as st

# State to store login status
if "user" not in st.session_state:
    st.session_state.user = None

email = st.text_input("Email")
password = st.text_input("Password", type="password")

if st.button("Login"):
    try:
        user = supabase.auth.sign_in_with_password({"email": email, "password": password})
        st.session_state.user = user.user
        st.success("Logged in!")
    except Exception as e:
        st.error(f"Login failed: {e}")

