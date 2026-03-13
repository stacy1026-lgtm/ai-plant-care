from streamlit.testing.v1 import AppTest

def test_app_functionality():
    # Load the app
    at = AppTest.from_file("streamlit_app.py").run()
    
    # --- 1. Test "View Full Collection" ---
    # Expand and check interaction
    view_collection = at.expander(label="📋 View Full Collection")
    view_collection.expand().run()
    
    # Check for selectbox
    assert view_collection.selectbox(label="Select the plant to water:")
    
    # Simulate watering logic
    view_collection.selectbox[0].select("Hoya Verticillata Black Margin").run()
    view_collection.button(label="💧 Water Now").click().run()
    
    # Verify the action triggered a success or rerun
    assert at.rerun_count > 0

    # --- 2. Test "Plant Cemetery" ---
    cemetery = at.expander(label="💀 Plant Cemetery (Remove a Plant)")
    cemetery.expand().run()
    assert cemetery.selectbox(label="Select the plant that didn't make it:")

    # --- 3. Test "Smart Frequency Analysis" ---
    analysis = at.expander(label="📊 Smart Frequency Analysis")
    analysis.expand().run()
    
    # If suggestions exist, check for the accept button
    # Using key-based lookup for reliability
    if len(analysis.button) > 0:
        analysis.button(key="up_1").click().run()
        assert at.rerun_count > 0
