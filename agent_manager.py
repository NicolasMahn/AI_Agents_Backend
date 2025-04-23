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
    models = list(config.llm_names.keys())
    return models

def set_model(model_name):
    if model_name in config.llm_names.keys():
        model = config.llm_names[model_name]
        config.selected_model = model
        config.max_tokens["default"] = config.max_tokens[config.selected_model]
        config.max_context_tokens = config.max_tokens[config.selected_model] - config.max_instructions_size - config.max_prompt_tokens
        if 999999 < config.max_tokens[config.selected_model]:
            config.max_chat_tokens = 20 * config.max_generic_content_length
        else:
            config.max_chat_tokens = 4 * config.max_generic_content_length
        return True
    return False

def get_model():
    return next((k for k, v in config.llm_names.items() if v == config.selected_model), None)

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
