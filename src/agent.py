from matplotlib.figure import Figure
import regex as re
import pandas as pd
import matplotlib.pyplot as plt
import os
import json
from openai import OpenAI # Testing the async version is also on the table --> TBD
from .config import OPENAI_API_KEY
from .prompt import ANSWER_PROMPT, CLASSIFICATION_PROMPT, DEFINITION_PROMPT, STRUCTURE_PROMPT_1, STRUCTURE_PROMPT_2, CODING_PROMPT

class Agent:
    def __init__(self, df: pd.DataFrame, model: str = "gpt-4o", max_tokens: int = 2000) -> None:
        """Initialize the agent with the DataFrame and model configuration."""
        self.df = df
        self.model = model
        self.max_tokens = max_tokens
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


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
            temperature=0
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
            temperature=0
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
            temperature=0.5
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
            temperature=0.5,
        )

        # Handle both object- and dict-style SDKs
        msg = resp.choices[0].message
        try:
            return msg.content               # preferred (object attribute)
        except AttributeError:
            return msg["content"]  
    
    def execute_code(self, code: str) -> str:
        """Execute the generated code and return the result."""
        # Remove any leading or trailing code block markers
        if code.strip().startswith("```python") and code.strip().endswith("```"):
            code = "\n".join(code.strip().splitlines()[1:-1])
        try:
            # Create a local scope for executing the code
            local_scope = {'df': self.df, 'plt': plt, 'os': os}
            exec(code, {}, local_scope)

            # Retrieve the value of a variable named 'result' if it exists
            result = local_scope.get('result', None)

            # Check if a plot was generated
            if 'plt' in local_scope and hasattr(local_scope['plt'], 'savefig'):
                local_scope['plt'].savefig("output_plot.png", dpi=300)

            if result is not None:
                return result
        except Exception as e:
            return f"An error occurred while executing the code: {str(e)}"
        
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
            temperature=0.5
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
            
            # Preprocess the query
            processed_query = self.preprocess_query(query, q_class)
            print(f"Processed query: {processed_query}")

            if q_class == 4:
                response = self.get_definition(processed_query)
                return response

            # Generate the response
            code = self.generate_response(processed_query)
            print(f"Generated code: {code}")
            # Execute the code if it is a code generation query
            response = self.execute_code(code)

            final_answer = self.structure_final_answer(query, response)
            response["message"] = final_answer
            return response
        except Exception as e:
            # Handle exceptions gracefully
            return f"An error occurred while processing your query: {str(e)}"
        




