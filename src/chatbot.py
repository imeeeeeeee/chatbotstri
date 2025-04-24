# chatbot.py
from pandasai import SmartDataframe
from pandasai.llm.openai import OpenAI
import openai
import matplotlib.pyplot as plt
from langchain_openai import ChatOpenAI
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from langchain.agents.agent_types import AgentType
import logging
from .config import OPENAI_API_KEY, SECTOR_CODES, FEEDBACK_FILE
import os
import json
from datetime import datetime

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

        prefix = f"""
        You are an expert data analyst interacting with a pandas DataFrame named `df`. 

        DATAFRAME STRUCTURE & USAGE CONTEXT:
        1. **Column Definitions:**
            - `'SECT'`: Sector code for the measure. Valid codes are listed explicitly in SECTOR_CODES = {SECTOR_CODES}.
            - `'CLASS'`: Type of measure. Use `'STRI'` specifically for Services Trade Restrictiveness Index queries.
            - `'COUNTRY'`: Country ISO3 code (e.g., `'AUS'` for Australia).
            - `'YEARS'`: A string representation of a list of years, always ordered chronologically: `[2014, 2015, ..., 2024]`.
            - `'SCORES'`: A string representation of a list of corresponding float scores (range 0-1), matching exactly with the `'YEARS'` list by index.

        2. **Important Constraints:**
            - Scores must be retrieved using matching indices from the `'YEARS'` and `'SCORES'` lists.

        3. **Default Behavior:**
            - If the user's query does **not specify a sector**, default to the `'ALLSECT'` sector.
            - If asked to compare countries, you compare their STRI scores.
            - When asked about a specific countries general score, always look in the 'ALLSECT' sector and 'STRI' class.
            - If asked about measures or policy areas, they're equivalent to the 'CLASS' column.
            - If asked about a specific sector, always look in the 'SECT' column and 'STRI' class.
            - If asked about a specific country, always look in the 'COUNTRY' column and 'STRI' class.
            - When a sector is explicitly mentioned, always validate and use its correct sector code from SECTOR_CODES = {SECTOR_CODES}.
            - Sectoral shifts are oscillations in STRI scores over time, indicating changes in trade restrictions, when asked always provide the years of major changes.
            - OECD average is the mean of all the ALLSECT STRI scores for the OECD countries in the dataset.
            - If asked about the reason for a shift in the score of a sector, look at the changes in the CLASS column for that sector and the years of the shift.
            - If asked about the reason for a change in the score of a country, look at the changes in the CLASS column for that country and the years of the shift.
            - If asked about the reason for a change in the score of a country in a sector, look at the changes in the CLASS column for that country and sector and the years of the shift.

        Always strictly adhere to these instructions and examples for accurate, safe, and robust interactions with the DataFrame.
        """

        suffix = """        
            ⚠️ FORMAT REQUIREMENTS ⚠️
            - Always return your answer as a JSON object:

            - Your Python code must be a one-liner string:
            - Escape newlines as `\\n`
            - Escape quotes `"` as `\\\"`
            - NEVER return raw multiline code blocks
            - NEVER return truncated code — finish all function calls and parentheses
        """


        self.agent = create_pandas_dataframe_agent(
            self.llm,
            self.df,
            agent_type=AgentType.OPENAI_FUNCTIONS,
            prefix = prefix,
            suffix=suffix,
            verbose=True,
            allow_dangerous_code=True,
        )

        self.logger = logging.getLogger(__name__)
        #openai.api_key = OPENAI_API_KEY

    def ask(self, query):
        """Process query with enhanced error handling and visualization support"""
        try:
            # Process query with visualization capability
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
            You are an expert data analyst providing clear, insightful interpretations of quantitative outputs from a Pandas DataFrame named `df`, which contains Services Trade Restrictiveness Index (STRI) data.

            CONTEXT:
            - The user has submitted the following query: {query}
            - You are provided with a raw Python dictionary named `result`, derived from STRI data.
            - STRI scores range from 0 to 1:
                - A **lower score** indicates **fewer trade restrictions**.
                - A **higher score** indicates **more restrictive policies** in the services sector.
            - If asked to list all the sectors, pull them from {SECTOR_CODES}.

            DATAFRAME STRUCTURE:
            - Each entry in the DataFrame refers to a specific COUNTRY, SECTOR, and YEAR.
            - The 'SCORES' column contains a list of yearly STRI scores aligned with the 'YEARS' list.

            OBJECTIVE:
            - Explain clearly what the result means in human language.
            - If the STRI score is high or low, interpret the level of restriction accordingly.
            - Be precise and avoid speculation—only base your explanation on the data in the result.
            """
            gpt_response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": gpt_prompt},
                    {"role": "user", "content": f"Explain these insights: {response}"}
                ]
            ).choices[0].message.content

            return gpt_response


        except Exception as e:
            self.logger.error(f"Query failed: {str(e)}")
            return f"⚠️ Analysis error: {str(e)}", None