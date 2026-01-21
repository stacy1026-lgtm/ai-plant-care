# 1. Setup AI with a fail-safe model picker
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# We will try these names in order of most powerful to most compatible
model_names = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']

model = None
for name in model_names:
    try:
        model = genai.GenerativeModel(name)
        # Test if this specific name works
        model.generate_content("test") 
        st.success(f"Connected using: {name}")
        break
    except Exception:
        continue

if model is None:
    st.error("Could not connect to any Gemini models. Please check your API Key.")
