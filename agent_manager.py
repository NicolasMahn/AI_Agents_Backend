import shutil

import config
from agent_systems.llm_wrapper_system import LLMWrapperSystem
from agent_systems.planning_agent_system import PlanningAgentSystem
from agent_systems.reviewing_agent_system import ReviewingAgentSystem, ReviewingAgentSystemWithLesserCritic
from agent_systems.reviewing_planning_agent_system import ReviewingPlanningAgentSystem
from agent_systems.simple_agent_system import SimpleAgentSystem
from agents.planning_agent import PlanningAgent

agent_systems = [
    LLMWrapperSystem(),
    SimpleAgentSystem(),
    ReviewingAgentSystem(),
    ReviewingAgentSystemWithLesserCritic(),
    ReviewingPlanningAgentSystem(),
    ReviewingAgentSystemWithLesserCritic(),
    PlanningAgentSystem(),
]

def get_agents():
    return [str(agent) for agent in agent_systems]

def get_agent(agent_system_name: str):
    for agent_system in agent_systems:
        if str(agent_system) == agent_system_name:
            return agent_system
    return None

def get_agent_description(agent_name: str):
    for agent in agent_systems:
        if str(agent) == agent_name:
            return agent.description
    return None

def replace_agent(agent_obj, agent_name: str):
    for agent in agent_systems:
        if str(agent) == agent_name:
            agent_systems.remove(agent)
            break
    agent_systems.append(agent_obj)

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

def agent_reset(agent_system_name: str):
    agent_system = get_agent(agent_system_name)
    print(agent_system)
    if agent_system:
        shutil.rmtree(agent_system.agent_system_dir, ignore_errors=True)
        agent_system.reset()
        return True
    return False
