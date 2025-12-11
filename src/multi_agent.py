# multi_db_agent.py
import json
from openai import OpenAI
from .agent import Agent as QuantAgent
from .reforms_agent import ReformsAgent
from .prompt import CLASSIFICATION_PROMPT, ANSWER_PROMPT, GUARDRAIL_PROMPT

class MultiDBAgent:
    def __init__(self, df_quant, df_reforms, model: str = "gpt-4.1", max_tokens: int = 4096):
        self.client = OpenAI()
        self.model = model
        self.max_tokens = max_tokens
        self.quant_agent = QuantAgent(df_quant, model=model, max_tokens=max_tokens)
        self.reforms_agent = ReformsAgent(df_reforms, model=model, max_tokens=max_tokens)

    # --- compliance ---
    def _check_compliance(self, query: str) -> int:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "developer", "content": GUARDRAIL_PROMPT},
                {"role": "user", "content": query},
            ],
            max_tokens=1,
        )
        try:
            print("Compliance response:", resp.choices[0].message.content.strip())
            return int(resp.choices[0].message.content.strip())
        except Exception:
            return 0


    # --- classification ---

    def _classify(self, query: str) -> int:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "developer", "content": CLASSIFICATION_PROMPT},
                {"role": "user", "content": query},
            ],
            max_tokens=1,
        )
        try:
            print("Classification response:", resp.choices[0].message.content.strip())
            return int(resp.choices[0].message.content.strip())
        except Exception:
            return 5

    # --- fusion only for summaries (class 6) ---

    def _fuse_summary(self, query: str, quant_result, reforms_result) -> str:
        """
        Build a *summary-style* answer using both:
        - quantitative_result: scores, charts, tables
        - reforms_result: concrete reforms text
        """
        if isinstance(quant_result, str):
            quant_payload = {"message": quant_result}
        else:
            quant_payload = quant_result

        payload = {
            "quantitative_result": quant_payload,
            "reforms_result": reforms_result,
        }

        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "developer",
                    "content": (
                        ANSWER_PROMPT
                        + query
                        + "\n\nAdditional instruction: This is a summary request. "
                          "Use quantitative information to describe scores, levels, "
                          "and trends, and qualitative reforms information to explain "
                          "*why* things changed. Do not invent scores or reforms."
                    ),
                },
                {"role": "user", "content": json.dumps(payload, default=str)},
            ],
            max_tokens=self.max_tokens,
        )
        return resp.choices[0].message.content

    # --- main entrypoint ---

    def invoke(self, query: str):

        compliance = self._check_compliance(query)

        if compliance == 0:
            return {
                "message": (
                    "I’m sorry, but your query appears to be non-compliant with our usage policies. "
                    "Please ensure your question is related to the OECD STRI and does not contain any inappropriate content."
                ),
                "data": None,
                "fig": None,
                "images": [],
                "reforms_rows": [],
            }

        q_class = self._classify(query)

        # Not an STRI query
        if q_class == 5:
            return {
                "message": (
                    "I’m sorry, this doesn’t look like a question about the OECD STRI. "
                    "Could you rephrase your question about services trade restrictiveness?"
                ),
                "data": None,
                "fig": None,
                "images": [],
                "reforms_rows": [],
            }

        # Reforms-only queries (class 7): use only reforms DB
        if q_class == 7:
            reforms_result = self.reforms_agent.invoke(query)
            return {
                "message": reforms_result["message"],
                "data": None,
                "fig": None,
                "images": [],
                "reforms_rows": reforms_result.get("reforms_rows", []),
            }

        # Summary queries (class 6): combine both DBs
        if q_class == 6:
            quant_result = self.quant_agent.invoke(query)
            reforms_result = self.reforms_agent.invoke(query)
            final_message = self._fuse_summary(query, quant_result, reforms_result)

            out = {
                "message": final_message,
                "data": None,
                "fig": None,
                "images": [],
                "reforms_rows": reforms_result.get("reforms_rows", []),
            }
            if isinstance(quant_result, dict):
                out["data"] = quant_result.get("data")
                out["fig"] = quant_result.get("fig")
                out["images"] = quant_result.get("images", [])
            return out

        # All other STRI queries: quantitative DB only
        quant_result = self.quant_agent.invoke(query)
        if isinstance(quant_result, dict):
            quant_result.setdefault("reforms_rows", [])
            return quant_result
        else:
            return {
                "message": quant_result,
                "data": None,
                "fig": None,
                "images": [],
                "reforms_rows": [],
            }
