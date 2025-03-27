import xml.etree.ElementTree as ET


def execute_plan_command(command: ET, agent):
    steps = command.findall("step")
    agent.plan.clear()
    agent.plan.extend([step.text for step in steps])
    return "Plan created or updated."

def execute_next_step_command(_, agent):
    if any("plan" in command.tag for command in agent.commands):
        return "Plan and Next Step commands cannot be used together."
    agent.plan.next_step()
    return "Now working on next step."