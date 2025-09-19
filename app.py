# app.py
import os
from venv import logger
import certifi
from matplotlib.figure import Figure
from src.agent import Agent
from src.chatbot import Chatbot
import streamlit as st
import pandas as pd
from src.data_loader import load_data
from src.config import NEW_DATA_PATH
from datetime import datetime
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
    
os.environ["OPENAI_API_KEY"] = st.secrets["openai_api_key"]

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
        max_tokens = st.slider("Response Length", 50, 500, 500)
        model_version = st.selectbox(
            "AI Model Version",
            ["gpt-4o", "gpt-4o-mini"],
            index=0
        )

    with st.expander("ℹ️ About This App", expanded=True):
        st.markdown("""
        **ASTRID: STRI Database Analytics Assistant**  
        This tool lets you interact with the STRI dataset using natural language.  
        Use Case Categories 
        Please try to classify your questions in line with the following types:
         - General Query
            Inquiries about the dataset, structure, methodology, or available coverage (countries, sectors, years).
            Example: "What does the dataset include?"
        - Score Query
            Requests for STRI or related scores for a specific country, sector, and/or year.
            Example: "What’s the STRI for Japan in legal services in 2023?"
        - Graphical Query
            Requests for visualizations (charts, plots, etc.) based on the STRI data.
            Example: "Show me the trend line for France’s STRI in telecom."
        - Comparative Query
            Comparisons between countries, sectors, or time periods.
            Example: "Compare Germany and Italy in financial services in 2022."
        - Definition Query
            Requests for definitions or explanations (terms, indicators, methods).
            Example: "What is STRI?" or "How is the restrictiveness score calculated?"
        - Summary Query
            Requests for a general overview of a country’s current STRI situation.
            Example: "Give me a summary of Australia’s STRI profile."

        Important Notes
        - We’re currently only working with the indices — the regulatory measures database will be integrated later. So for now, no questions about specific measures, please.
        - All this guidance will soon be available directly in the app via a dedicated info window for easy reference.

        """)

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
                st.session_state.chatbot = Agent(
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
                response = st.session_state.chatbot.invoke(prompt)
                st.session_state.response = response
                with st.chat_message("assistant"):
                    # Check if the response is a matplotlib figure
                    if isinstance(response, Figure):
                        st.pyplot(response)
                    else:
                        st.markdown(response)
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
