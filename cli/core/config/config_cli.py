import argparse
import shlex

from cli.settings import is_debug
from cli.common.base_cli import BaseCLI
from cli.core.config.init_cli import InitCLI
from cli.core.config.config_stp_cli import ConfigStp
from cli.core.config.config_manager import ConfigManager
from cli.common.mixins.admincli_commands import AdminCliCommandMixin
from cli.common.mixins.set_commands import SetCommandMixin

class ConfigCLI(AdminCliCommandMixin, SetCommandMixin, BaseCLI):

    SUPPORTED_VERSIONS = {"24R2", "24R3", "25R1", "25R2", "25R3"}
    SUPPORTED_RATS = {"4G", "5G"}

    def __init__(self):
        if is_debug:
            print("configCli 진입")
        super().__init__()
        self.prompt = "config > "
        self.config = ConfigManager()

        #사용자가 init-stp를 입력하면 do_init_stp가 실행되도록 함
        self.aliases.update({
            "init-stp": "init_stp",
            "init-bts": "init_bts",
            "init-cell": "init_cell",
        })

    def do_init_stp(self, args):
        """기지국 초기 설정 진입"""
        if is_debug:
            self.poutput("[디버그] config/init-stp 진입")

        cli = ConfigStp(config=self.config)
        cli.prompt = "config/init-stp > "
        cli.cmdloop()

    def do_init_bts(self, args):
        """init-bts 모드 진입"""
        parser = argparse.ArgumentParser(prog="init-bts", add_help=False)
        parser.add_argument("-v", "--version", type=str, default="24R2")
        parser.add_argument("-r", "--rat", type=str, required=True, choices=["4G", "5G"])
        parser.add_argument("-i", "--iot", type=str, help="LNCEL IOT 대상 ID (예: 350)")

        try:
            parsed = parser.parse_args(shlex.split(args))

            if parsed.version not in self.SUPPORTED_VERSIONS:
                self.perror(f"지원하지 않는 버전입니다: {parsed.version}")
                self.perror(f"지원되는 버전: {', '.join(self.SUPPORTED_VERSIONS)}")
                return

            if is_debug:
                self.poutput(f"[디버그] init-bts({parsed.version}, {parsed.rat}) 진입")

            cli = InitCLI(
                allow_commit_diff=True, ## 수정 필요
                mo_version=parsed.version,
                rat_type=parsed.rat,
                config=self.config,
                iot_lncel_id=parsed.iot,  # cell 모드에서만 사용하므로 None으로 명시
                mode="bts"
            )
            cli.prompt = f"config/init-bts({parsed.version}, {parsed.rat}) > "
            cli.cmdloop()
        except SystemExit:
            self.perror("사용법: init-bts -v <24R2|25R1> -r <4G|5G>")


    def do_init_cell(self, args):
        """init-cell 모드 진입"""
        parser = argparse.ArgumentParser(prog="init-cell", add_help=False)
        parser.add_argument("-v", "--version", type=str, default="24R2")
        parser.add_argument("-r", "--rat", type=str, required=True, choices=["4G", "5G"])
        parser.add_argument("-i", "--iot", type=str, help="LNCEL IOT 대상 ID (예: 350)")

        try:
            parsed = parser.parse_args(shlex.split(args))

            if parsed.version not in self.SUPPORTED_VERSIONS:
                self.perror(f"지원하지 않는 버전입니다: {parsed.version}")
                self.perror(f"지원되는 버전: {', '.join(self.SUPPORTED_VERSIONS)}")
                return

            if is_debug:
                self.poutput(f"[init-cell] RU_TYPE : {parsed.version}, RADIO_TYPE : {parsed.rat}")
                print("dest_bts :", self.config.get("dest_bts"))

            cli = InitCLI(
                allow_commit_diff=True,
                mo_version=parsed.version,
                rat_type=parsed.rat,
                config=self.config,
                iot_lncel_id=parsed.iot,
                mode="cell"
            )
            cli.prompt = f"config/init-cell({parsed.version}, {parsed.rat}) > "
            self.do_dnload_bts_cfg_raw
            self.do_set_cfg_scf("genScf")
            cli.cmdloop()
        except SystemExit:
            self.perror("사용법: init-cell -v <버전> -r <4G|5G> [-i <iot_id>]")
    
    def do_init_mod(self, args):
        """init-mod 모드 진입"""
        parser = argparse.ArgumentParser(prog="init-mod", add_help=False)
        parser.add_argument("-v", "--version", type=str, default="24R2")
        parser.add_argument("-r", "--rat", type=str, required=True, choices=["4G", "5G"])

        try:
            parsed = parser.parse_args(shlex.split(args))

            if parsed.version not in self.SUPPORTED_VERSIONS:
                self.perror(f"지원하지 않는 버전입니다: {parsed.version}")
                self.perror(f"지원되는 버전: {', '.join(self.SUPPORTED_VERSIONS)}")
                return

            if is_debug:
                self.poutput(f"[디버그] init-mod({parsed.version}, {parsed.rat}) 진입")

            cli = InitCLI(
                allow_commit_diff=False,
                mo_version=parsed.version,
                rat_type=parsed.rat,
                config=self.config,
                iot_lncel_id=None,
                mode="cell"
            )
            cli.prompt = f"config/init-mod({parsed.version}, {parsed.rat}) > "
            cli.cmdloop()
        except SystemExit:
            self.perror("사용법: init-mod -v <버전> -r <4G|5G>")

    def do_exit(self, arg):
        """루프형 CLI에서는 exit 시 cmdloop() 종료"""
        if is_debug:
            print("configCli exit")
        return True
    
    def get_help_topics(self):
        allowed = {"init_stp", "init_bts", "init_cell", "exit"}
        return [
            (cmd, help_text)
            for cmd, help_text in super().get_help_topics()
            if cmd in allowed
        ]

    def get_names(self):
        return [
            n for n in super().get_names()
            if n.startswith("do_init_stp") or n.startswith("do_init_bts")
            or n.startswith("do_init_cell") or n.startswith("do_exit")
        ]
