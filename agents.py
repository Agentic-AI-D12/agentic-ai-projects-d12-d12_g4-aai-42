from crewai import Agent
from llm import llm
from tools import cost_tool, resource_validator_tool, knowledge_rag_tool
import warnings
warnings.filterwarnings("ignore")
#hospital_tool = HospitalTool()
#cost_tool = CostTool()


planner = Agent(
    role="Medical Planner",
    goal="Plan treatment including hospitals and costs",
    backstory="You are a senior medical expert. You use the knowledge_rag_tool to consult verified medical guidelines from your internal knowledge base, and you use the cost_tool to estimate costs accurately while preserving the provided hospital list exactly.",
    llm=llm, 
    max_execution_time=120, 
    verbose=True,
    tools=[cost_tool, knowledge_rag_tool],
    max_rpm=3,
)
researcher = Agent(
    role="Hospital Finder",
    goal="Find hospitals",
    backstory="Medical expert",
    llm=llm,
    tools=[],
    verbose=True,
    allow_delegation=False,
    max_iter=2,
    max_rpm=3,
    max_execution_time=120
)

cost_agent = Agent(
    role="Cost Analyzer",
    goal="Estimate medical treatment costs using cost_tool",
    backstory="You calculate treatment costs using tool output only.",
    llm=llm,
    tools=[cost_tool],
    system_prompt="""
You are Cost Analyzer.

IMPORTANT RULES:
- You MUST use cost_tool
- You are NOT allowed to calculate manually
- You are NOT allowed to explain anything
- You are NOT allowed to say "requirements are met"
- You are NOT allowed to summarize
- You MUST return ONLY the tool response exactly as received
"""
,    verbose=True,
    allow_delegation=False,
    max_iter=2,
    max_rpm=3,
    max_execution_time=120
)

scheduler_agent = Agent(
    role="Treatment Scheduler",
    goal="Create a detailed week-by-week treatment execution schedule and validate resource availability at hospitals",
    backstory="You are an expert medical scheduler who creates realistic treatment timelines and validates hospital resource availability using the resource_validator_tool.",
    llm=llm,
    tools=[resource_validator_tool],
    verbose=True,
    allow_delegation=False,
    max_iter=2,
    max_rpm=3,
    max_execution_time=120
)
