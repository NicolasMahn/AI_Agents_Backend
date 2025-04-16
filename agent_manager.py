import shutil

import config
from agents import Agent
from agents.planning_agent import PlanningAgent
from agents.reviewing_agent import ReviewingAgent
from agents.reviewing_planning_agent import ReviewingPlanningAgent

agents = [
    Agent("Agent"),
    ReviewingAgent("Review Agent"),
    PlanningAgent("Planning Agent"),
    ReviewingPlanningAgent("Reviewing Planning Agent"),
]

def get_agents():
    return [str(agent) for agent in agents]

def get_agent(agent_name: str):
    for agent in agents:
        if str(agent) == agent_name:
            return agent
    return None

def replace_agent(agent_obj, agent_name: str):
    for agent in agents:
        if str(agent) == agent_name:
            agents.remove(agent)
            break
    agents.append(agent_obj)

def get_available_models():
    models = list(config.max_tokens.keys())
    models.remove("text-embedding-ada-002")
    models.remove("default")
    return models

def set_model(model):
    if model in config.max_tokens.keys():
        config.selected_model = model
        config.max_tokens["default"] = config.max_tokens[config.selected_model]
        config.max_context_tokens = config.max_tokens[config.selected_model] - 10000 - config.max_prompt_tokens #minus 10000 for instructions + safety buffer
        if model in config.MODEL_OWNER["google"]:
            config.max_chat_tokens = 20 * config.max_generic_content_length
        else:
            config.max_chat_tokens = 4 * config.max_generic_content_length
        return True
    return False

def get_model():
    return config.selected_model

def agent_reset(agent_name: str):
    agent = get_agent(agent_name)
    if agent:
        type_ = type(agent)
        shutil.rmtree(agent.agent_dir, ignore_errors=True)
        del agent
        agent = type_(agent_name)
        replace_agent(agent, agent_name)
        return True
    return False
