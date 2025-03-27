from agents import Agent
from agents.planning_agent import PlanningAgent

agents = [
    Agent("Agent"),
    PlanningAgent("Planning Agent")
]

def get_agents():
    return [str(agent) for agent in agents]

def get_agent(agent_name: str):
    for agent in agents:
        if str(agent) == agent_name:
            return agent
    return None

