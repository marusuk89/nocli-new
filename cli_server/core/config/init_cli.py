import shlex
from cli.common.execution_helper import ExecutionHelper
from cli.core.config.config_manager import ConfigManager

class InitCLI(ExecutionHelper):
    prompt = "nocli-cfg> "

    def __init__(self):
        super().__init__()
        self.config = ConfigManager()

    def do_tgt_bts(self, arg):
        """
        BTS 작업을 시작합니다.
        사용법: tgt-bts <BTS_ID>
        """
        tokens = shlex.split(arg.strip())
        if len(tokens) != 1:
            self.perror("사용법: tgt-bts <BTS_ID>")
            return

        bts_id = tokens[0]
        self._enter_or_create_mo("MRBTS", bts_id)

    def do_no_tgt_bts(self, arg):
        """
        현재 작업 중인 BTS를 초기화합니다.
        사용법: no-tgt-bts <BTS_ID>
        """
        tokens = shlex.split(arg.strip())
        if len(tokens) != 1:
            self.perror("사용법: no-tgt-bts <BTS_ID>")
            return

        bts_id = tokens[0]
        if bts_id != getattr(self, "bts_id", None):
            self.perror(f"BTS ID 불일치: 현재 작업 중인 BTS는 {self.bts_id}입니다.")
            return

        confirm = input("CONFIRM ? Yes or No [Y / n]: ")
        if confirm.strip().lower() not in ["y", "yes"]:
            self.poutput("중단됨.")
            return

        self.xml_tree = self._create_empty_xml()
        self.bts_id = None
        self.mo_class = None
        self.match_tail = None
        self.prompt = "nocli-cfg> "

        if self.is_debug:
            self.poutput(f"RESULT: OK; config workspace for bts-{bts_id} was removed.")
