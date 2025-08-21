# chatbot.py
import logging
from .config import OPENAI_API_KEY
import os
from .agent import Agent

class Chatbot:
    def __init__(self, df, model, max_tokens):
        """Initialize chatbot with advanced configuration"""
        os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
        self.df = df
        self.agent = Agent(df, model, max_tokens)

        self.logger = logging.getLogger(__name__)

    def ask(self, query):
        """Process query with enhanced error handling and visualization support"""
        try:
            # Process query with visualization capability
            response, plot = self.agent.invoke(query)
            return response, plot

        except Exception as e:
            self.logger.error(f"Query failed: {str(e)}")
            return f"⚠️ Analysis error: {str(e)}", None
