import xml.etree.ElementTree as ET


def execute_plan_command(command: ET, agent_system):
    steps = command.findall("step")
    agent_system.plan.set_plan([step.text for step in steps])

    return "Plan created or updated."

def execute_next_step_command(_, agent):
    if agent.extraction_failure:
        return "Extraction of a command failed. Fix it, before going to the nex step!"
    agent.plan.next_step()
    return "Now working on next step."