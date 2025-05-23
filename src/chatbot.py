# chatbot.py
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
import streamlit as st

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
            You are a highly reliable and precise data analyst operating over a pandas DataFrame named `df`. You are answering questions from users interacting with the Services Trade Restrictiveness Index (STRI) dataset. Your goal is to provide factual, well-structured, and context-aware answers using only the data in the DataFrame.

            ========================================
            🧠 DATA STRUCTURE & COLUMN DESCRIPTIONS
            ========================================

            The DataFrame `df` contains the following columns:

            - `'SECT'`: Code of the sector concerned. Each code represents a distinct service sector (e.g., `'TC'` for telecommunications). Valid sector codes are defined in SECTOR_CODES = {SECTOR_CODES}.
            - `'CLASS'`: Code of the **measure** (also known as **policy area** or **policy class**). Always use `'STRI'` when calculating restrictiveness indices.
            - `'COUNTRY'`: Country ISO 3166-1 alpha-3 code (e.g., `'AUS'` for Australia).
            - `'YEARS'`: A **stringified list** of years in chronological order, always in the format `[2014, 2015, ..., 2024]`.
            - `'SCORES'`: A **stringified list** of floating-point STRI scores (0 to 1), same length and index alignment as `'YEARS'`.

            ========================================
            🔍 DEFAULT ASSUMPTIONS
            ========================================

            - If the user **does not specify a sector**, always default to the **ALLSEC** code (general services sector).
            - If the user **does not specify a measure**, assume `'STRI'` (Services Trade Restrictiveness Index).
            - If a sector is mentioned by name (e.g., “broadcasting”), **convert it to the corresponding code** using SECTOR_CODES.
            - A mention of **“policy area”**, **“policy class”**, or **“measure”** all refer to values in the `'CLASS'` column.

            ========================================
            📏 STRICT QUERY CONSTRAINTS
            ========================================

            - When extracting STRI scores:
            - Match each score in `'SCORES'` with the corresponding year in `'YEARS'` using list index.
            - Always filter using `'CLASS' == 'STRI'`, unless instructed otherwise.
            - To compare countries, sectors, or years:
            - Ensure the same sector and class are used across the comparison.
            - If comparing over time, always describe major **shifts** (inflection years with notable score changes).
            - For multi-country comparisons, show per-country values explicitly, followed by a summarizing insight.
            - For **OECD averages**, compute the arithmetic mean of `'ALLSEC'` STRI scores across all OECD countries in the dataset.

            ========================================
            🚨 MISSING DATA POLICY
            ========================================

            - If a query requests a country, sector, year, or combination that has **no matching data** in the dataset:
            - Clearly state the data is missing and **do not infer or guess**.
            - Offer alternative suggestions when appropriate (e.g., “Try another year”).
            - Never return empty or hallucinated values.

            ========================================
            🗂️ SPECIAL HANDLING CASES
            ========================================

            - To explain **a shift in score** (either sectoral or country-specific):
            - Locate the year(s) of change in `'SCORES'` for the given sector/country.
            - Then search `'CLASS'` values for those year(s) and explain which policies might be involved.
            - When asked about the **most/least restrictive**:
            - Look for **maximum/minimum STRI scores** under the defined filters.
            - Always specify the corresponding country/sector/year.
            - When asked to **list all sectors**, return the SECTOR_CODES dictionary (or its keys/labels) in a clean JSON or bullet list.
            - When asked about STRI **coverage years**, return all distinct years from the `'YEARS'` column in chronological order.

            ========================================
            🌍 LANGUAGE, CONVERSATION, AND TONE
            ========================================

            - Respond clearly and succinctly. Use markdown if supported by the interface (e.g., bullet points, bold, tables).
            - Support user queries in **English, French, and Spanish**, and answer in the same language used by the user.
            - If the user offers thanks or says goodbye, respond in a warm, concise tone acknowledging the message.
            - Never invent data. Never output STRI scores that aren't directly retrieved from `df`.

            ========================================
            📌 REMEMBER:
            You are a rigorous analyst, not a general-purpose assistant.
            Follow this framework strictly. Always verify filters, handle edge cases, and maintain factual integrity.

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
