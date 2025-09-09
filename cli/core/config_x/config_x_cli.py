from cli.settings import is_debug
from cli.common.base_cli import BaseCLI
from cli.core.config.config_manager import ConfigManager
from cli.core.config_x.autoComm_cli import AutoComm
from cli.core.config_x.migrate_cli import Migrate
from cli.core.config_x.relocate_cli import Relocate

class ConfigXCLI(BaseCLI):
    def __init__(self):
        if is_debug:
            print("configXCli 진입")
        super().__init__()
        self.config = ConfigManager()

    def do_auto_comm(self, args):
        """auto-commission 모드 진입"""
        if is_debug:
            self.poutput("[디버그] config-x/auto-comm 진입")

        cli = AutoComm(config=self.config)
        cli.prompt = "config-x/auto-comm > "
        cli.cmdloop()

    def do_relocate(self, args):
        """relocate 모드 진입"""
        if is_debug:
            self.poutput("[디버그] config2/relocate 진입")

        cli = Relocate(config=self.config)
        cli.prompt = "config2/relocate > "
        cli.cmdloop()
    
    def do_migrate(self, args):
        """migrate 모드 진입"""
        if is_debug:
            self.poutput("[디버그] config2/migrate 진입")

        cli = Migrate(config=self.config)
        cli.prompt = "config2/migrate > "
        cli.cmdloop()

    def onecmd_plus_hooks(self, line, *args, **kwargs):
        ## autocomm-run-script로 왔을시 원본 입력값을 유지 시켜주기 위함
        result = super().onecmd_plus_hooks(line, *args, **kwargs)

        try:
            original = getattr(self, "_original_line", line)
        except:
            original = line

        if original.strip().lower() == "exit":
            return True
        return result

    def do_exit(self, arg):
        """현재 루프를 나갑니다."""
        return True
    
    def get_help_topics(self):
        allowed = {"exit", "auto_comm", "migrate", "relocate"}
        return [
            (cmd, help_text)
            for cmd, help_text in super().get_help_topics()
            if cmd in allowed
        ]

    def get_names(self):
        return [
            n for n in super().get_names()
            if n.startswith("do_exit") or n.startswith("do_auto_comm") or n.startswith("do_migrate") or n.startswith("do_relocate")
        ]

