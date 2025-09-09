class WorkSpace():
    def __init__(self):
        self.bts = {}
        self.cell = {}

        self.xml_tree = None
        self.match_tail = None
        self.mo_class = None
        self.prompt = None
        self.final_file = None

    def set(self, key, val):
        self.bts[key] = val

    def get(self, key):
        return self.bts.get(key)

    def __str__(self):
        return (
            f"[Workspace]\n"
            f"- BTS Vars: {self.bts}\n"
            f"- match_tail: {self.match_tail}\n"
            f"- mo_class: {self.mo_class}\n"
            f"- prompt: {self.prompt}\n"
            f"- xml_tree: {'ok' if self.xml_tree is not None else 'nok'}"
        )