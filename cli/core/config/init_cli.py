import os
import json
import shlex
import secrets
from cli.common.base_cli import BaseCLI
from cli.common.mixins.admincli_commands import AdminCliCommandMixin
from cli.common.mixins.commit_commands import CommitCommandMixin
from cli.common.mixins.set_commands import SetCommandMixin
from cli.common.mixins.setup_commands import SetupCommandMixin
from cli.common.mixins.show_commands import ShowCommandMixin
from cli.common.mixins.tool_commands import ToolCommandMixin
from cli.common.mixins.tree_commands import TreeCommandMixin
from cli.common.mixins.autocomm_commands import AutocommCommandMixin
from cli.common.util.commit_utils import load_param_dict
from cli.common.util.server_utils import load_from_server
from cli.settings import is_debug
from dotenv import load_dotenv

class InitCLI(
    AdminCliCommandMixin, CommitCommandMixin, SetCommandMixin, 
    SetupCommandMixin, ShowCommandMixin, ToolCommandMixin, TreeCommandMixin, AutocommCommandMixin, BaseCLI
    ):
    def __init__(self, allow_commit_diff, mo_version, rat_type, config, iot_lncel_id=None, mode=None):
        self.match_tail = None  # get_names에서 먼저 쓰이기 때문에 먼저 초기화
        super().__init__()

        ## settings
        self.allow_commit_diff = allow_commit_diff
        self.mo_version = mo_version ## ex : 24R2
        self.rat_type = rat_type
        self.config = config or {}
        self.mode = mode
        self.kill_dummy_flag = None
        
        self.request_id = 1 ## admin-cli(pb2)
        self.iot_lncel_id = iot_lncel_id ## init-cell macro/nbiot
        self.last_script_line = None
        load_dotenv()
        self.env_type = os.getenv("ENV_TYPE", "DEV")

        ## set_ru_type
        self.ru_type = None
        self.du_type = None ## 테스트 필요
        self.cell_type = None
        self.band_option = None 
        self.sector_3 = False

        ##xml_tree 관련
        self.mo_class = None
        self.bts_id = None
        self.xml_tree = self._create_empty_xml()
        self.ref_tree = self._create_empty_xml()
        self.cli_template_tree = self._create_empty_xml()
        self.prompt_stack = ["config"]
        self.prompt = self._build_prompt()

        self.user_inputs = []
        self.last_commit_file = None

        self.param_dict = load_param_dict(self, self.rat_type, self.mo_version)
        self.mo_param_dict = None
        self.rulebook_param_dict = None

        self.exec_script_errors = []

    def _load_rulebook(self):
        print("rat_type =", self.rat_type)
        print("mo_version =", self.mo_version)
        print("mode =", self.mode)
        print("du_type =", self.du_type)

        if self.mode == "cell" and self.du_type.upper() == "DU10" and self.rat_type.upper() == "5G":
            if is_debug:
                print(f"{self.rat_type}_{self.mo_version}_du10_cell 세팅")
            filename = f"{self.rat_type}_{self.mo_version}_rulebook_du10_cell.json"
        elif self.mode == "bts" and self.du_type.upper() == "DU10" and self.rat_type.upper() == "5G":
            if is_debug:
                print(f"{self.rat_type}_{self.mo_version}_du10_bts 세팅")
            filename = f"{self.rat_type}_{self.mo_version}_rulebook_du10_bts.json"
        elif self.mode == "cell" and self.du_type.upper() == "DU20":
            if is_debug:
                print(f"{self.rat_type}_{self.mo_version}_du20_cell 세팅")
            filename = f"{self.rat_type}_{self.mo_version}_rulebook_du20_cell.json"
        elif self.mode == "bts" and self.du_type.upper() == "DU10":
            if is_debug:
                print(f"{self.rat_type}_{self.mo_version}_du20_bts 세팅")
            filename = f"{self.rat_type}_{self.mo_version}_rulebook_du20_bts.json"
        elif self.mode == "cell" and self.du_type.upper() == "FSMF" and self.rat_type.upper() == "4G":
            if is_debug:
                print(f"{self.rat_type}_{self.mo_version}_FSMF_cell 세팅")
            filename = f"{self.rat_type}_{self.mo_version}_rulebook_FSMF_cell.json"
        elif self.mode == "bts" and self.du_type.upper() == "FSMF" and self.rat_type.upper() == "4G":
            if is_debug:
                print(f"{self.rat_type}_{self.mo_version}_FSMF_bts 세팅")
            filename = f"{self.rat_type}_{self.mo_version}_rulebook_FSMF_bts.json"
        else:
            raise ValueError(f"지원되지 않는 mode/du_type 조합: {self.mode}/{self.du_type}")

        try:
            rulebook_dict = load_from_server(filename, filetype="json", purpose="rulebook")
            return rulebook_dict
        except Exception as e:
            print(f"[오류] rulebook 로드 실패: {e}")
            return {}

    def do_tgt_bts(self, arg):
        """
        BTS 작업을 시작합니다.
        사용법 : tgt-bts <BTS_ID>
        후보 : 130112
        """
        tokens = shlex.split(arg.strip())
        if len(tokens) != 1:
            self.perror("사용법: tgt-bts <BTS_ID>")
            return

        bts_id = tokens[0]
        dest_bts_id = self.config.get("dest_bts")

        if dest_bts_id is None:
            self.perror("[오류] 내부적으로 BTS ID가 설정되지 않았습니다. (dest-bts를 먼저 실행했는지 확인해주세요)")
            return
        elif dest_bts_id != bts_id:
            self.perror(f"[오류] tgt-bts ID '{bts_id}'가 현재 설정된 BTS ID '{dest_bts_id}'와 다릅니다.")
            return
        ## bts에선 ru_type 고정
        if self.mode == "bts" and self.rat_type == "4G" :
            self.ru_type = "AHCA"
        elif self.mode == "bts" and self.rat_type == "5G" :
            self.ru_type = "AEQY"
            self.cell_type = "AEQY_4_2"
        elif self.mode == "cell" :
            if not self.ru_type:
                self.perror("[오류] RU 타입이 설정되어 있지 않습니다. 먼저 set-ru-type 명령어를 실행해주세요.")
                return

        self.task_key = secrets.token_hex(3)
        if is_debug:
            self.poutput(f"[작업 세션 시작] task key 생성됨: {self.task_key}")

        ### auto-comm의 평면적 구조를 위한 초기화 선행작업
        self.bts_id = None
        self.prompt_stack = []
        self.match_tail = ""
        ###

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
        self.prompt_stack = ["config"]
        self.prompt = self._build_prompt()

        from cli.settings import is_debug
        if is_debug:
            self.poutput(f"RESULT: OK; config workspace for bts-{bts_id} was removed.")

    def get_names(self):
        is_top_level = not self.match_tail or self.match_tail.strip() == ""

        top_level_allowed = {
            "do_tgt_bts", "do_no_tgt_bts", "do_set_cfg_tmpl", "do_set_ru_type",
            "do_gethwinfo", "do_commit_all", "do_commit_diff", "do_commit",
            "do_dnload_bts_cfg", "do_apply_bts_cfg", "do_act_bts_cfg",
            "do_no_mo", "do_no_pa", "do_show_cfg", "do_show_glb", "do_show_sib",
            "do_show_can_mo", "do_show_can_pa", "do_show_user_input",
            "do_add_auto_pa", "do_list", "do_scf_to_cli", "do_exit",
            "do_show_key", "do_auto_config"
        }

        sub_level_allowed = {
            "do_no_mo", "do_no_pa", "do_show_cfg", "do_exit", "do_show_key", "do_list"
        }

        allowed = top_level_allowed if is_top_level else sub_level_allowed
        return [n for n in super().get_names() if n in allowed]

    def get_help_topics(self):
        is_top_level = not self.match_tail or self.match_tail.strip() == ""

        top_level_allowed = {
            "tgt_bts", "no_tgt_bts", "set_cfg_tmpl", "set_ru_type", "gethwinfo",
            "commit", "dnload_bts_cfg", "apply_bts_cfg", "act_bts_cfg",
            "no_mo", "no_pa", "show_cfg", "show_glb", "show_sib",
            "show_can_mo", "show_can_pa", "show_user_input",
            "add_auto_pa", "list", "exec_script", "exit",
            "show_key", "auto_config"
        }

        sub_level_allowed = {
            "no_mo", "no_pa", "show_cfg", "exit", "show_key", "list"
        }

        allowed = top_level_allowed if is_top_level else sub_level_allowed

        base = super().get_help_topics()
        filtered = [
            (cmd, help_text)
            for cmd, help_text in base
            if isinstance(help_text, str) and cmd in allowed
        ]

        # 가짜 명령어 도움말
        extra = [
            ("<MO> <ID> : MO 생성 또는 이동 (예: EQM 12345)"),
            ("<key> <value> : 파라미터 설정 (예: cellId 1)"),
            ("list <name> <idx> <key> <value> : 리스트 파라미터 설정"),
        ]

        return filtered + extra

    def do_set_iot_lncel_id(self, arg):
        """IoT 셀 ID 설정 (예: set-iot-lncel-id 350)"""
        try:
            self.iot_lncel_id = arg.strip()
            if is_debug:
                self.poutput(f"[완료] iot_lncel_id 설정됨: {self.iot_lncel_id}")
        except ValueError:
            self.perror("정수 형태로 입력해주세요 (예: set-iot-lncel-id 350)")

    def perror(self, msg, *args, **kwargs):
        full_msg = f"[오류] {msg}"
        if hasattr(self, "exec_script_errors") and isinstance(self.exec_script_errors, list):
            self.exec_script_errors.append(full_msg)
        super().perror(msg, *args, **kwargs)