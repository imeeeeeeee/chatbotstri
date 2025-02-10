import pandas as pd
from pandasai import SmartDataframe
from langchain_ollama import OllamaLLM

#Loading the model
llm = OllamaLLM(model="llama3.2", temperature=0)
fields = ["MeasureID", "Country"]
#Loading the dataset
path = "V:\\STRI\\NOBACKUP\\stri_calculation_data\\stri_regdb_2024.dta"
df = pd.read_stata(path, columns=fields)
print(df.head(3))
# df = pd.DataFrame({
#     "country": ["United States", "United Kingdom", "France", "Germany", "Italy", "Spain", "Canada", "Australia", "Japan", "China"],
#     "sales": [5000, 3200, 2900, 4100, 2300, 2100, 2500, 2600, 4500, 7000]
# })


#Creating the smart df

sdf = SmartDataframe(df, config={"llm": llm})
sdf.chat('')
