import streamlit as st
import sys
import os

# Simple test app to verify Streamlit works
st.title("🧪 Streamlit Test App")

st.success("✅ Streamlit is working!")

st.subheader("System Information")
st.write(f"Python version: {sys.version}")
st.write(f"Current directory: {os.getcwd()}")
st.write(f"Files in directory: {os.listdir('.')}")

st.subheader("Required Modules Test")
modules_to_test = [
    'pandas', 'numpy', 'plotly', 'requests', 
    'alpaca_trade_api', 'yfinance', 'pandas_ta'
]

for module in modules_to_test:
    try:
        __import__(module)
        st.success(f"✅ {module} - OK")
    except ImportError as e:
        st.error(f"❌ {module} - Missing: {e}")

if st.button("Test API Connection"):
    try:
        from alpaca_trade_api.rest import REST
        
        # Test with your credentials
        api_key = "AK2V88RDO5MYCFOE8FJH"
        secret_key = "gmCM49z9z3VlmTnoF7vsn9wliXZz6SE6NHCs5d5I"
        
        client = REST(
            key_id=api_key,
            secret_key=secret_key,
            base_url="https://api.alpaca.markets"
        )
        
        account = client.get_account()
        st.success(f"✅ Alpaca API Connected! Account: {account.id}")
        
    except Exception as e:
        st.error(f"❌ API Connection Failed: {e}")