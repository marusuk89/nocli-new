from cli.common.base_cli import BaseCLI
from cli.common.mixins.setup_commands import SetupCommandMixin

class ConfigStp(BaseCLI, SetupCommandMixin):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.prompt = "config/init-stp > "

    def onecmd_plus_hooks(self, line, *args, **kwargs):
        result = super().onecmd_plus_hooks(line, *args, **kwargs)
        if line.strip().lower() == "exit":
            return True
        return result

    def do_exit(self, arg):
        """현재 루프를 나갑니다."""
        return True
    
    def get_help_topics(self):
        allowed = {
            "dest_bts",
            "dest_bts_ip",
            "check_ping",
            "update_sw_ver",
            "check_soam",
            "check_ssh",
            "exit",
        }
        return [
            (cmd, help_text)
            for cmd, help_text in super().get_help_topics()
            if cmd in allowed
        ]

    
    def get_names(self):
        allowed_prefixes = {
            "do_dest_bts",
            "do_dest_bts_ip",
            "do_check_ping",
            "do_update_sw_ver",
            "do_check_soam",
            "do_check_ssh",
            "do_exit",
        }
        return [n for n in super().get_names() if n in allowed_prefixes]
