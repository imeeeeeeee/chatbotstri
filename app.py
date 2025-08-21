# app.py
import os
from pathlib import Path
from venv import logger

import certifi
import streamlit as st
import pandas as pd
from src.chatbot import Chatbot
from src.data_loader import load_data
from src.config import DATA_PATH, DIGITAL_STRI_PATH, NEW_DATA_PATH, FEEDBACK_FILE
from datetime import datetime
import json
import openai
from streamlit_gsheets import GSheetsConnection

os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

# Configure page settings
st.set_page_config(
    page_title="STRI Database Analytics",
    page_icon="🤖",
    layout="wide"
)

# User inputs for authentication
authenticator = st.text_input("Enter the authentication password", type="password")

# Set your desired password here
AUTH_PASSWORD = st.secrets["password"]

if authenticator != AUTH_PASSWORD:
    st.warning("Please enter the correct password to access the app.")
    st.stop()

api_key = st.secrets["openai_api_key"]

# Set the API key
openai.api_key = api_key

def initialize_session():
    """Initialize session state variables"""
    if "chatbot" not in st.session_state:
        st.session_state.chatbot = None
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "data_loaded" not in st.session_state:
        st.session_state.data_loaded = False
    if "rating" not in st.session_state:
        st.session_state.rating = None
    if "prompt" not in st.session_state:
        st.session_state.prompt = ""
    if "response" not in st.session_state:
        st.session_state.response = ""

def show_data_overview(df):
    """Display comprehensive data overview"""
    with st.expander("📊 Dataset Overview"):
        tab1, tab2, tab3 = st.tabs(["Preview", "Statistics", "Data Types"])
        
        with tab1:
            st.dataframe(df, use_container_width=True)
        
        with tab2:
            st.write("Summary Statistics")
            st.dataframe(df.describe(include='all'), use_container_width=True)
        
        with tab3:
            st.write("Data Types and Missing Values")
            dtype_df = pd.DataFrame({
                'Column': df.columns,
                'Type': df.dtypes,
                'Missing Values': df.isna().sum()
            })
            st.dataframe(dtype_df, use_container_width=True)

conn = st.connection("gsheets", type=GSheetsConnection)
existing_data = conn.read(worksheet="Sheet1", usecols=list(range(4)), ttl=5)

def log_feedback(query, model_response, score):
    """Store user feedback in JSONL format with timestamp, query, response, and score."""
    try:
        feedback_entry = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "response": model_response,
            "score": score
        }
        
        # Append the new feedback entry
        new_data = pd.DataFrame([feedback_entry])
        updated_data = pd.concat([existing_data, new_data], ignore_index=True)
        
        # Update the worksheet with the combined data
        conn.update(worksheet="feedback", data=updated_data)
        st.success("Feedback logged successfully!")

    except Exception as e:
        logger.error(f"Failed to log feedback: {str(e)}")

def main():
    initialize_session()
    st.title("ASTRID: STRI Database Analytics Assistant")
    st.markdown("""
    **💬 Interact** with the AI assistant to analyze your data.
    **📈 Visualize** trends through natural language queries.
    """)

    # Sidebar configurations
    with st.sidebar:
        st.header("Configuration")
        sample_size = st.slider("Data Sample Size (%)", 1, 100, 100)
        max_tokens = st.slider("Response Length", 50, 500, 200)
        model_version = st.selectbox(
            "AI Model Version",
            ["gpt-4o-mini", "gpt-3.5-turbo"],
            index=0
        )

    # Data loading with caching
    @st.cache_data(show_spinner="Loading dataset...")
    def cached_load(path, sample):
        return load_data(path, sample/100)

    try:
        df = cached_load(NEW_DATA_PATH, sample_size)
        st.session_state.data_loaded = True
    except Exception as e:
        st.error(f"🚨 Data loading failed: {str(e)}")
        return

    if st.session_state.data_loaded:
        st.success(f"✅ Successfully loaded {len(df):,} records")
        show_data_overview(df)

    # Initialize chatbot once
    if st.session_state.data_loaded and not st.session_state.chatbot:
        with st.spinner("🧠 Initializing AI analyst..."):
            try:
                st.session_state.chatbot = Chatbot(
                    df=df,
                    model=model_version,
                    max_tokens=max_tokens
                )
            except Exception as e:
                st.error(f"🤖 Chatbot initialization failed: {str(e)}")
                return

    # Chat interface
    st.divider()
    st.subheader("Analysis Conversation")
    
    # Display chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "plot" in msg and msg["plot"]:
                st.image(msg["plot"], use_column_width=True)

    # Handle user input
    if prompt := st.chat_input("Hello, I'm Astrid, how can I help you?"):
        with st.chat_message("user"):
            st.markdown(prompt)
            st.session_state.prompt = prompt
        
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.spinner("🔍 Analyzing..."):
            try:
                response = st.session_state.chatbot.ask(prompt)
                st.session_state.response = response
                with st.chat_message("assistant"):
                    st.markdown(response)
                    # Display plot if available
                    plot_path = Path("output_plot.png")
                    if plot_path.exists():
                    # Read the image into memory
                        img_bytes = plot_path.read_bytes()
                        st.image(img_bytes, width=800)

                    # Delete the file immediately after displaying
                    try:
                        plot_path.unlink()
                    except Exception as e:
                        st.warning(f"⚠️ Could not delete {plot_path.name}: {e}")
                    # Rating and feedback section
                    if response:  # Only show if there's a response to rate
                        st.write("---")  # Visual separator
                        st.markdown("**Help us improve!** Rate this response:")
                        
                    try:
                        with st.form("feedback_form"):
                            cols = st.columns(8)
                            with cols[0]:
                                st.form_submit_button("1 ⭐", on_click=lambda: log_feedback(st.session_state.prompt, model_response=st.session_state.response, score=1))
                            with cols[1]:
                                st.form_submit_button("2 ⭐", on_click=lambda: log_feedback(st.session_state.prompt, model_response=st.session_state.response, score=2))
                            with cols[2]:
                                st.form_submit_button("3 ⭐", on_click=lambda: log_feedback(st.session_state.prompt, model_response=st.session_state.response, score=3))
                            with cols[3]:
                                st.form_submit_button("4 ⭐", on_click=lambda: log_feedback(st.session_state.prompt, model_response=st.session_state.response, score=4))
                            with cols[4]:
                                st.form_submit_button("5 ⭐", on_click=lambda: log_feedback(st.session_state.prompt, model_response=st.session_state.response, score=5))
                    except Exception as e:
                        st.error(f"Failed to log feedback: {str(e)}")


                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response,
                    #"plot": plot
                })

            except Exception as e:
                st.error(f"⚠️ Processing error: {str(e)}")

if __name__ == "__main__":
    main()
