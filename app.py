# app.py
import streamlit as st
import pandas as pd
from src.chatbot import Chatbot
from src.data_loader import load_data
from src.config import DATA_PATH, DIGITAL_STRI_PATH

# Configure page settings
st.set_page_config(
    page_title="STRI Database Analytics",
    page_icon="🤖",
    layout="wide"
)

def initialize_session():
    """Initialize session state variables"""
    if "chatbot" not in st.session_state:
        st.session_state.chatbot = None
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "data_loaded" not in st.session_state:
        st.session_state.data_loaded = False

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

def main():
    initialize_session()
    st.title("STRI Database Analytics Assistant")
    st.markdown("""
    **💬 Interact** with the AI assistant to analyze your data.
    **📈 Visualize** trends through natural language queries.
    """)

    # Sidebar configurations
    with st.sidebar:
        st.header("Configuration")
        sample_size = st.slider("Data Sample Size (%)", 1, 100, 15)
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
        df = cached_load(DATA_PATH, sample_size)
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
    if prompt := st.chat_input("Ask about the data (e.g., trends, correlations)"):
        with st.chat_message("user"):
            st.markdown(prompt)
        
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.spinner("🔍 Analyzing..."):
            try:
                response = st.session_state.chatbot.ask(prompt)
                
                with st.chat_message("assistant"):
                    st.markdown(response)
                    # if plot:
                    #     st.image(plot, use_column_width=True)
                    
                    # Feedback buttons
                    cols = st.columns(8)
                    with cols[0]:
                        if st.button("👍", help="Good response"):
                            st.session_state.chatbot.log_feedback(prompt, 1)
                    with cols[1]:
                        if st.button("👎", help="Improve response"):
                            st.session_state.chatbot.log_feedback(prompt, -1)
                
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response,
                    #"plot": plot
                })

            except Exception as e:
                st.error(f"⚠️ Processing error: {str(e)}")

if __name__ == "__main__":
    main()