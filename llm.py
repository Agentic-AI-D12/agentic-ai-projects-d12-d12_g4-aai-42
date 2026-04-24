from crewai import LLM
import os
from dotenv import load_dotenv

load_dotenv()

llm = LLM(
    model="groq/llama-3.1-8b-instant",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.2,
    max_tokens=450
)