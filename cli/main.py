from cli.settings import is_debug

from cli.common.base_cli import BaseCLI
from cli.core.config.config_cli import ConfigCLI
from cli.core.config_x.config_x_cli import ConfigXCLI
from cli.core.setup.setup_cli import SetupCLI

class NoCli(BaseCLI):
    def __init__(self):
        super().__init__()
        self.prompt = "# nocli > "

    def do_config(self, args):
        """Enter config mode."""
        if is_debug:
            self.poutput("Entering config mode...")

        cli = ConfigCLI()
        cli.prompt = "config > "
        cli.cmdloop()
    
    def do_config_x(self, args):
        """Enter config mode."""
        if is_debug:
            self.poutput("Entering config mode...")

        cli = ConfigXCLI()
        cli.prompt = "config-x > "
        cli.cmdloop()

    def do_setup(self, args):
        """Enter setup mode."""
        if is_debug:
            self.poutput("Entering setup mode...")

        cli = SetupCLI()
        cli.prompt = "setup > "
        cli.cmdloop()

    def get_help_topics(self):
        # help 명령 시 config, setup만 보이게
        allowed = {"config", "setup"}
        return [
            (cmd, help_text)
            for cmd, help_text in super().get_help_topics()
            if cmd in allowed
        ]

    def get_names(self):
        # 자동 완성 시도도 config/setup만 작동하게 제한 가능 (선택사항)
        return [n for n in super().get_names() if n.startswith("do_config") or n.startswith("do_setup")]

if __name__ == "__main__":
    app = NoCli()
    app.cmdloop()
