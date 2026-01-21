# 1. Setup AI with the specific stable path
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# We use 'gemini-1.5-flash' but without the 'models/' prefix 
# as the library often adds it automatically.
try:
    model = genai.GenerativeModel('gemini-1.5-flash')
    # This tiny test confirms the connection immediately
    model.generate_content("test")
    st.success("AI is Online! ✅")
except Exception as e:
    st.error(f"Connection Error: {e}")
    # Fallback to the older stable version if Flash fails
    model = genai.GenerativeModel('gemini-pro')
