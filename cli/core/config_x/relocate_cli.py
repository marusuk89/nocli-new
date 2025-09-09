from cli.common.base_cli import BaseCLI

class Relocate(BaseCLI):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.prompt = "config2/relocate > "

    def onecmd_plus_hooks(self, line, *args, **kwargs):
        result = super().onecmd_plus_hooks(line, *args, **kwargs)
        if line.strip().lower() == "exit":
            return True
        return result

    def do_exit(self, arg):
        """현재 루프를 나갑니다."""
        return True