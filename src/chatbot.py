# chatbot.py
# from pandasai import SmartDataframe
# from pandasai.llm.openai import OpenAI
import openai
import matplotlib.pyplot as plt
from langchain_openai import ChatOpenAI
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from langchain.agents.agent_types import AgentType
import logging
from .config import OPENAI_API_KEY
import os

class Chatbot:
    def __init__(self, df, model="gpt-4o-mini", max_tokens=200):
        """Initialize chatbot with advanced configuration"""
        os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
        self.df = df
        self.llm = ChatOpenAI(
            #api_token=OPENAI_API_KEY,
            model=model,
            temperature=0,
            max_tokens=max_tokens
        )


        # self.sdf = SmartDataframe(
        #     df,
        #     config={
        #         "llm": self.llm,
        #         "save_logs": False,
        #         "verbose": False,
        #         "enable_cache": True,
        #         "enable_debugging": False,
        #         "custom_prompts": {
        #             "generate_response": """You're a data analyst. Here's some context about the database:
        #                                     If asked about an answer for a measure in a specific year, all the relevant data is in the columns named Answer_in_(year).
        #                                     If asked about STRI scores in a specific year, all the relevant data is in the columns named STRI_in_(year).
        #                                     Answer this query: {query}
        #                                 """
        #         }
        #     }
        # )

        prefix = """You're a data analyst working on a pandas df. Here's some context about the database:
                    If asked about an answer for a measure in a specific year, all the relevant data is in the columns named Answer_in_(year).
                    If asked about STRI scores in a specific year, all the relevant data is in the columns named STRI_in_(year).
                    If asked about the STRI score of a country in a specific sector, it's the sum of the STRI scores of ALL measures of that sector and for that country in the latest year.
                    If asked about the general STRI score of a country, it refers to the mean of stri scores per sector in the latest year for that specific country.
                    When comparing countries, unless specified otherwise, you compare general STRI scores calculated as previously stated.
                    If asked about sources, list all the relevant links in "Source" columns.
                    All the questions about specific measures are in the column 'Measure'.
                    Answer this query: {query}
                 """

        self.agent = create_pandas_dataframe_agent(
            self.llm,
            self.df,
            agent_type=AgentType.OPENAI_FUNCTIONS,
            prefix = prefix,
            # suffix = "Always return a JSON directory that can be parsed into a dataframe containing the requested information.",
            verbose=True,
            allow_dangerous_code=True
        )

        self.logger = logging.getLogger(__name__)
        #openai.api_key = OPENAI_API_KEY

    def ask(self, query):
        """Process query with enhanced error handling and visualization support"""
        try:
            # Process query with visualization capability
            #response = self.sdf.chat(query)
            response = self.agent.invoke(query)
            # # Extract visualization if generated
            # plot = None
            # if self.sdf is not None:
            #     fig = self.sdf
            #     if fig:
            #         buf = io.BytesIO()
            #         fig.savefig(buf, format='png', bbox_inches='tight')
            #         plt.close(fig)
            #         buf.seek(0)
            #         plot = buf

            # Generate natural language explanation

            gpt_prompt = f"""
                            You are a data analysis expert. 
                            To give you some context, this is the query given by the user: {query}.
                            The STRI score goes from 0 to 1. The lower the STRI score is, the less restrictive the country is.
                            High STRI scores imply high levels of restrictions.
                            Speak like a true diva when answering.
                            This is the response : {response}
                        """
            # Context about the database to be added - meeting with Fred

            gpt_response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": gpt_prompt},
                    {"role": "user", "content": gpt_prompt}
                ]
            ).choices[0].message.content

            return gpt_response

        except Exception as e:
            self.logger.error(f"Query failed: {str(e)}")
            return f"⚠️ Analysis error: {str(e)}", None

    def log_feedback(self, query, score):
        """Store user feedback for model improvement"""
        # Implementation for feedback logging
        pass