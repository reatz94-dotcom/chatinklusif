import streamlit as st
import google.generativeai as genai

# Setup API
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-3-flash-preview') # Sesuai gambar 2 kamu

st.title("🤖 Chatbot Guru Inklusi (UDL)")
prompt = st.chat_input("Tanyakan strategi UDL...")

if prompt:
    with st.chat_message("user"):
        st.write(prompt)
    
    response = model.generate_content(prompt)
    
    with st.chat_message("assistant"):
        st.write(response.text)
