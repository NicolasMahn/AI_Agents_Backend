

class Plan:

    def __init__(self, agent):
        self.agent = agent
        self.current_step = 0
        self.plan = []

    def set_plan(self, plan):
        self.plan = plan
        self.current_step = 0
        self.agent.add_context_data("Plan", self, "Plan Steps", importance=1, always_display=True)

    def next_step(self):
        self.current_step += 1
        self.agent.add_context_data("Plan", self, "Plan Steps", importance=1, always_display=True)

    def get_plan_as_xml_str(self):
        xml_str = "<plan>"
        for i, step in enumerate(self.plan):
            if i == self.current_step:
                xml_str += f"<step current_step=\"true\">{step}</step>"
            else:
                xml_str += f"<step>{step}</step>"
        xml_str += "</plan>"

        return xml_str

    def __str__(self):
        return self.get_plan_as_xml_str()

    def __repr__(self):
        return self.get_plan_as_xml_str()

    def __len__(self):
        return len(self.plan)

    def __getitem__(self, index):
        return self.plan[index]

    def __setitem__(self, index, value):
        self.plan[index] = value
        self.agent.add_context_data("Plan", self, "Plan Steps", importance=1, always_display=True)

    def __delitem__(self, index):
        del self.plan[index]
        self.agent.add_context_data("Plan", self, "Plan Steps", importance=1, always_display=True)

    def is_done(self):
        return self.current_step >= len(self.plan)

    def get_current_step(self):
        if self.current_step < len(self.plan):
            return self.plan[self.current_step]
        else:
            return None

    def get_current_step_index(self):
        return self.current_step

