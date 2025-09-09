import os
from cli.core.config.init_cli import InitCLI
from cli.common.mixins.setup_commands import SetupCommandMixin
from cli.common.util.commit_utils import load_param_dict
from cli.settings import is_debug

class AutoComm(InitCLI, SetupCommandMixin):
    def __init__(self, config):
        super().__init__(
            allow_commit_diff=True,
            mo_version="24R2",
            rat_type="4G",
            config=config,
            iot_lncel_id=None,
            mode="bts"
        )
        self.prompt = "config-x/auto-comm > "
    
    # def onecmd_plus_hooks(self, line, *args, **kwargs):
    #     ## autocomm-run-script로 왔을시 원본 입력값을 유지 시켜주기 위함
    #     result = super().onecmd_plus_hooks(line, *args, **kwargs)

    #     try:
    #         original = getattr(self, "_original_line", line)
    #     except:
    #         original = line

    #     if original.strip().lower() == "exit":
    #         print("exit detected")
    #         return True

    #     return result
    
    ## 평면화 작업에 의한 수동 설정 ##
    
    def do_set_mo_version(self, arg):
        """mo_version을 설정합니다 (예: set-mo-version 24R2)"""
        version = arg.strip()
        if not version:
            self.perror("사용법: set-mo-version <버전>")
            return
        self.mo_version = version
        self.param_dict = load_param_dict(self, self.rat_type, self.mo_version)
        if is_debug:
            self.poutput(f"[완료] mo_version 설정됨: {self.mo_version}")

    def do_set_rat_type(self, arg):
        """RAT 타입을 설정합니다 (예: set-rat-type 4G)"""
        rat = arg.strip().upper()
        if rat not in {"4G", "5G"}:
            self.perror("지원되는 RAT: 4G, 5G")
            return
        self.rat_type = rat
        if is_debug:
            self.poutput(f"[완료] RAT 타입 설정됨: {self.rat_type}")

    def do_set_mode(self, arg):
        """모드 설정 (예: set-mode bts / set-mode cell / set-mode mod)"""
        mode = arg.strip().lower()
        if mode not in {"bts", "cell", "mod"}:
            self.perror("지원되는 모드: bts, cell, mod")
            return
        self.mode = mode
        if is_debug:
            self.poutput(f"[완료] 모드 설정됨: {self.mode}")

    def do_set_allow_commit_diff(self, arg):
        """commit diff 허용 여부 설정 (예: set-allow-commit-diff true)"""
        val = arg.strip().lower()
        self.allow_commit_diff = (val == "true")
        if is_debug:
            self.poutput(f"[완료] allow_commit_diff 설정됨: {self.allow_commit_diff}")

    