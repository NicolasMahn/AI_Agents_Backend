

class Plan(list):


    def __init__(self, agent):
        self.agent = agent
        super().__init__()

    def append(self, item):
        super().append(item)
        self.on_length_change()

    def extend(self, items):
        super().extend(items)
        self.on_length_change()

    def insert(self, index, item):
        super().insert(index, item)
        self.on_length_change()

    def remove(self, item):
        super().remove(item)
        self.on_length_change()

    def pop(self, index=-1):
        item = super().pop(index)
        self.on_length_change()
        return item

    def clear(self):
        super().clear()
        self.on_length_change()

    def __delitem__(self, index):
        super().__delitem__(index)
        self.on_length_change()

    def __setitem__(self, index, item):
        super().__setitem__(index, item)
        self.on_length_change()

    def __iadd__(self, other):
        super().__iadd__(other)
        self.on_length_change()
        return self

    def __imul__(self, n):
        super().__imul__(n)
        self.on_length_change()
        return self

    def __add__(self, other):
        result = super().__add__(other)
        self.on_length_change()
        return result

    def __mul__(self, n):
        result = super().__mul__(n)
        self.on_length_change()
        return result

    def __rmul__(self, n):
        result = super().__rmul__(n)
        self.on_length_change()
        return result

    def next_step(self):
        if len(self) > 0:
            return self.pop(0)
        else:
            return None

    def get_plan_as_xml_str(self):
        xml_str = "<plan>"
        for step in self:
            xml_str += f"<step>{step}</step>"
        xml_str += "</plan>"
        return xml_str

    def __str__(self):
        return self.get_plan_as_xml_str()

    def __repr__(self):
        return self.get_plan_as_xml_str()

    def on_length_change(self):
        if len(self) > 0:
            self.agent.add_context_data("Plan", self, "Plan Steps", importance=1)



