import shlex
from cli.common.execution_helper import ExecutionHelper
from cli.core.config.config_manager import ConfigManager


class InitStp(ExecutionHelper):

    def __init__(self):
        super().__init__()
        self.config = ConfigManager()
        self.prompt = ["setup/init-stp > "]

    def do_dest_bts(self, arg):
        """
        BTS 작업을 시작합니다.
        사용법: tgt-bts <BTS_ID>
        """
        tokens = shlex.split(arg.strip())
        if len(tokens) != 1:
            self.perror("사용법: dest-bts <BTS_ID>")
            return

        bts_id = tokens[0]
        self.config.set("dest_bts", bts_id)
        super().do_dest_bts(bts_id)

    def do_dest_bts_ip(self, arg):
        """
        BTS 작업을 시작합니다.
        사용법: tgt-bts <BTS_ID>
        """
        tokens = shlex.split(arg.strip())
        if len(tokens) != 1:
            self.perror("사용법: dest-bts-ip <BTS_IP>")
            return

        bts_ip = tokens[0]
        self.config.set("dest_bts", bts_ip)
        super().do_dest_bts_ip(bts_ip)

    def do_check_ping(self, arg):
        """
        BTS 작업을 시작합니다.
        사용법: check-ping <BTS_ID>
        """
        tokens = shlex.split(arg.strip())
        if len(tokens) != 1:
            self.perror("사용법: check-ping <BTS_ID>")
            return

        bts_id = tokens[0]
        super().do_check_ping(bts_id)

