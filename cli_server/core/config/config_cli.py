from cli.common.execution_helper import ExecutionHelper
from cli.core.config.init_cli import InitCLI

class ConfigCLI(ExecutionHelper):
    prompt = "config > "

    def do_init_bts(self, args):
        """기지국 초기 설정 진입"""
        cli = InitCLI()
        cli.prompt = "config/init-bts > "
        cli.cmdloop()

    def do_init_cell(self, args):
        """셀 초기 설정 진입"""
        cli = InitCLI()
        cli.prompt = "config/init-cell > "
        cli.cmdloop()
