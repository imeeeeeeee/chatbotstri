# reforms_agent.py
import json
import regex as re
import pandas as pd
from openai import OpenAI
from .prompt import STRUCTURE_PROMPT_1, STRUCTURE_PROMPT_2
from .config import OPENAI_API_KEY

class ReformsAgent:
    def __init__(self, df_reforms: pd.DataFrame, model: str = "gpt-4.1", max_tokens: int = 2048):
        self.df = df_reforms
        self.model = model
        self.max_tokens = max_tokens
        self.client = OpenAI(api_key=OPENAI_API_KEY)

    def _structure_reforms_query(self, query: str) -> dict:
        """Use your STRUCTURE_PROMPT_2[7] to extract countries, sectors, years."""
        format_prompt = STRUCTURE_PROMPT_2[7]

        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "developer", "content": STRUCTURE_PROMPT_1 + format_prompt},
                {"role": "user", "content": query},
            ],
        )
        content = resp.choices[0].message.content
        json_str = re.search(r"\{.*\}", content, re.DOTALL)[0]
        return json.loads(json_str)

    def _filter_reforms(self, structured: dict) -> pd.DataFrame:
        df = self.df.copy()
        print("DF sample:")
        print(df[["country", "sector", "year"]].head())

        print("Unique years in df:", sorted(df["year"].unique()))
        print("Unique country codes in df:", sorted(df["country"].unique())[:10])
        print("Unique sectors in df:", sorted(df["sector"].unique())[:10])


        # normalise columns once
        df["country"] = df["country"].astype(str).str.strip()
        df["sector"]  = df["sector"].astype(str).str.strip()
        df["year"]    = df["year"].astype(str).str.strip()

        m = pd.Series(True, index=df.index)

        countries = [str(c).strip() for c in (structured.get("countries") or [])]
        sectors   = [str(s).strip() for s in (structured.get("sectors") or [])]
        years     = [str(y).strip() for y in (structured.get("years") or [])]

        print("Filtering reforms for:", countries, sectors, years)

        if countries:
            m &= df["country"].isin(countries)

        if years:
            m &= df["year"].isin(years)

        if sectors:
            # If sectors are specified but don't match, send all results for the country and year regardless of the sector
            sector_match = df["sector"].isin(sectors)
            if not sector_match.any():
                print("No matching sectors found. Ignoring sector filter.")
            else:
                m &= sector_match


        print(f"Filtered reforms: {m.sum()} rows match criteria.")
        return df.loc[m].copy()


    def _summarise_reforms(self, query: str, rows: list[dict]) -> str:
        """Turn a list of (country, year, sector, reform_text) entries into a narrative."""
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an STRI policy analyst. You receive a user question "
                        "and a JSON list of reforms (country, year, sector, reform_text). "
                        "Summarise the key reforms that answer the question. "
                        "Do not invent reforms beyond the list; if information is missing, say so."
                        "If no sectors are mentioned in the reforms, provide a general summary."
                        "If no countries are mentioned, provide a general summary for that sector across all countries in the latest year, if it exists."
                    ),
                },
                {
                    "role": "user",
                    "content": f"User question:\n{query}\n\nReforms data:\n{json.dumps(rows, ensure_ascii=False)}",
                },
            ],
            max_tokens=self.max_tokens,
        )
        return resp.choices[0].message.content

    def invoke(self, query: str) -> dict:
        structured = self._structure_reforms_query(query)
        df_filtered = self._filter_reforms(structured)

        if df_filtered.empty:
            return {
                "reforms_rows": [],
                "message": "No recorded reforms match this query in the reforms database.",
            }

        rows = df_filtered.to_dict(orient="records")
        narrative = self._summarise_reforms(query, rows)

        return {
            "reforms_rows": rows,
            "message": narrative,
        }

