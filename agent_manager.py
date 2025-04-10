import config
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

def get_available_models():
    models = list(config.max_tokens.keys())
    models.remove("text-embedding-ada-002")
    models.remove("default")
    return models

def set_model(model):
    if model in config.max_tokens.keys():
        config.selected_model = model
        config.max_tokens["default"] = config.max_tokens[config.selected_model]
        config.max_context_tokens = config.max_tokens[config.selected_model] - 60000  # minus a safety margin for role and other tokens
        return True
    return False
