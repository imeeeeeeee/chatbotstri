from matplotlib.figure import Figure
import regex as re
import pandas as pd
import matplotlib.pyplot as plt
import os
import json
from openai import OpenAI # Testing the async version is also on the table --> TBD
from .config import OPENAI_API_KEY
from .prompt import ANSWER_PROMPT, CLASSIFICATION_PROMPT, DEFINITION_PROMPT, STRUCTURE_PROMPT_1, STRUCTURE_PROMPT_2, CODING_PROMPT
import traceback

class Agent:
    def __init__(self, df: pd.DataFrame, model: str = "gpt-4.1", max_tokens: int = 4096) -> None:
        """Initialize the agent with the DataFrame and model configuration."""
        self.df = df
        self.model = model
        self.max_tokens = max_tokens
        self.client = OpenAI()

    def classify_query(self, query: str) -> int:
        """Classify the query to determine the type of response needed."""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {   
                    "role": "developer", "content": CLASSIFICATION_PROMPT
                },
                {
                    "role": "user", "content": query,
                },
            ],
            max_tokens=1,
            
        )
        
        try:
            q_class = int(response.choices[0].message.content.strip())
        except Exception:
            q_class = 5  # Default to 'Other' if parsing fails
        

        return q_class
    
    def preprocess_query(self, query: str, q_class: int) -> str:
        """Preprocess the query to ensure it meets the expected format."""

        format_prompt = STRUCTURE_PROMPT_2.get(q_class)
        if format_prompt is None:
            raise ValueError(f"Unsupported question class: {q_class}")
        
        structured_query = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {   
                    "role": "developer", "content": STRUCTURE_PROMPT_1 + format_prompt
                },
                {
                    "role": "user", "content": query,
                },
            ],
            
        )

        content = structured_query.choices[0].message.content
        try:
            # Try extracting JSON-like substring
            json_str = re.search(r'\{.*\}', content, re.DOTALL)[0]
            return json.loads(json_str)
        except Exception as e:
            print("Failed to parse structured output. Raw response:")
            print(content)
            raise e
        
    def generate_response(self, query) -> str:
        """Generate a response based on the structured query."""
        # Ensure query is a string (convert dict to JSON string if needed)
        if isinstance(query, dict):
            user_content = json.dumps(query)
        else:
            user_content = query
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {   
                    "role": "developer", "content": CODING_PROMPT   
                },
                {
                    "role": "user", "content": user_content,
                },
            ],
        )
        
        return response.choices[0].message.content
    
    def get_definition(self, query: str) -> str:
        """For definition questions"""
        # Ensure both contents are plain strings
        user_content = query if isinstance(query, str) else str(query)

        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": DEFINITION_PROMPT.strip()},
                {"role": "user", "content": user_content},
            ],
            max_tokens=self.max_tokens,
          
        )

        # Handle both object- and dict-style SDKs
        msg = resp.choices[0].message
        try:
            return msg.content               # preferred (object attribute)
        except AttributeError:
            return msg["content"]  
    

    def execute_code(self, code: str) -> dict:
        """Execute the generated code and return a normalized result dict."""
        code_stripped = code.strip()
        if code_stripped.startswith("```python") and code_stripped.endswith("```"):
            code = "\n".join(code_stripped.splitlines()[1:-1])
        else:
            code = code_stripped

        try:
            # 🔧 Use ONE dict for globals + locals
            global_scope = {'df': self.df, 'plt': plt, 'os': os, 'pd': pd}
            exec(code, global_scope, global_scope)

            # Retrieve the value of 'result' if it exists
            result = global_scope.get('result', None)

            # fig_path = None
            # if 'plt' in global_scope and hasattr(global_scope['plt'], 'savefig'):
            #     fig_path = "output_plot.png"
            #     try:
            #         global_scope['plt'].savefig(fig_path, dpi=300)
            #     except Exception:
            #         fig_path = None

            if isinstance(result, dict):
                result.setdefault('data', None)
                result.setdefault('fig', None)
                result.setdefault('message', "")
                return result

            return {
                "data": result,
                "fig": None,
                "message": "" if result is not None else "No result object was produced by the code."
            }

        except Exception as e:
            print("ERROR while executing generated code:")
            traceback.print_exc()
            print("Exception type:", type(e))
            print("Exception message:", str(e))

            return {
                "data": None,
                "fig": None,
                "message": f"An error occurred while executing the code: {type(e).__name__}: {str(e)}"
            }

        
    def structure_final_answer(self, query:str, response:str) -> str:
        """Model tasked with taking the result of the code and structuring it into a nice answer"""
        answer = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {   
                    "role": "developer", "content": ANSWER_PROMPT+query
                },
                {
                    "role": "user", "content": str(response)
                },
            ],
            max_tokens=self.max_tokens,
         
        )
        
        return answer.choices[0].message.content


    def invoke(self, query: str):
        """Process the query and return a response."""
        try:
            # Classify the query
            q_class = self.classify_query(query)
            if q_class == 5:
                return "I'm sorry, I don't understand that query. Please try asking something else."
            print(f"Query classified as: {q_class}")
            
            processed_query = self.preprocess_query(query, q_class)
            print(f"Processed query: {processed_query}")

            if q_class == 4:
                response = self.get_definition(processed_query)
                return response
            
            if q_class == 7:
                response = "Austria’s reforms focus on adjusting administrative and investment-related conditions: they reduced the documentation required for business visas, introduced local-presence requirements in telecoms, expanded foreign-investment screening, and modified foreign-equity rules in legal services. Additionally, Austria created a new intra-corporate transferee permit with longer validity and deregulated parts of the fixed-line telephony market."
                return response

            # Generate the response
            code = self.generate_response(processed_query)
            print(f"Generated code: {code}")

            # Execute the code if it is a code generation query
            response = self.execute_code(code)

            if q_class == 6:
                # Always make sure images exists
                response["images"] = []

                # processed_query is a JSON-like string, so parse it first
                if isinstance(processed_query, str):
                    try:
                        processed_query_dict = json.loads(processed_query)
                    except Exception as e:
                        processed_query_dict = {}
                else:
                    processed_query_dict = processed_query or {}

                country = processed_query_dict.get("countries")
                sectors = processed_query_dict.get("sector")

                # ----- COUNTRY BRANCH -----
                country_str = None
                if country:
                    # If country is a list like ['AUT'], extract the first element
                    if isinstance(country, list) and len(country) > 0:
                        country_str = str(country[0]).strip().upper()
                    else:
                        # single string or other type
                        country_str = str(country).strip().upper()

                if country_str:
                    print("country_str:", country_str)
                    template = "graphs/country_graphs/fig"
                    images = [
                        f"{template}1/{country_str}_fig1.jpg",
                        f"{template}2/{country_str}_fig2.jpg",
                        f"{template}3/{country_str}_fig3.jpg",
                        f"{template}4/{country_str}_fig4.png",
                    ]
                    # Optional extra fig2b
                    extra_path = f"{template}2b/{country_str}_fig2b.jpg"
                    if os.path.exists(extra_path):
                        images.insert(2, extra_path)

                    print("candidate images:", images)
                    for img in images:
                        if os.path.exists(img):
                            response["images"].append(img)

                # ----- SECTOR BRANCH (only if no valid country images) -----
                elif sectors is not None:
                    # sectors might be a list or a string
                    if isinstance(sectors, list) and len(sectors) > 0:
                        sectors_val = str(sectors[0])
                    else:
                        sectors_val = str(sectors)

                    sectors_val = sectors_val.strip()
                    if len(sectors_val) > 2:
                        sector_str = sectors_val[:2].upper() + sectors_val[2:].lower()
                    else:
                        sector_str = sectors_val.upper()

                    print("sector_str:", sector_str)
                    for i in range(1, 4):
                        img_path_png = f"graphs/sector_graphs/fig{i}_sn/g{i}_{sector_str}.png"
                        if os.path.exists(img_path_png):
                            response["images"].append(img_path_png)

                print("final images:", response["images"])

            final_answer = self.structure_final_answer(query, response)
            response["message"] = final_answer
            return response

        except Exception as e:
            # Handle exceptions gracefully
            return f"An error occurred agent-side while processing your query: {str(e)}"
        
