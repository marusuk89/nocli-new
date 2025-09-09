import cmd2
from datetime import datetime
from cli.common.base_tool import BaseTool
from cli.common.util.server_utils import save_to_server

class BaseCLI(cmd2.Cmd, BaseTool):
    def __init__(self):
        super().__init__()
        self.debug = True

    def onecmd_plus_hooks(self, line, *args, **kwargs):
        line = line.strip()
        is_semicolon = line.endswith(";")
        self._last_command_had_semicolon = is_semicolon

        if is_semicolon:
            line = line[:-1].strip()

        tokens = line.split()
        if not tokens:
            return False

        if '-' in tokens[0]:
            tokens[0] = tokens[0].replace('-', '_')
            line = ' '.join(tokens)

        command_name = tokens[0]

        # 명령 실행 (결과 저장)
        result = super().onecmd_plus_hooks(line, *args, **kwargs)

        # (선택적) 명령 상태 읽기
        status = None
        if hasattr(self, "config") and hasattr(self.config, "get"):
            try:
                status = self.config.get("cmd_status")
            except Exception:
                pass

        # 커맨드 로그 기록
        is_do_command = (
            command_name in {
                name[3:] for name in dir(self)
                if name.startswith("do_")
                and name != "do_exit"
                and callable(getattr(self, name))
            }
        )

        if is_do_command and not getattr(self, "_logging_in_progress", False): ## 외부 호출일때만 실행
            self._logging_in_progress = True ## True로 되면 내부호출로 인식 if문을 타지 않음 -> 로그 기록 x
            try:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                prompt = getattr(self, "prompt", "").strip()
                result_str = "RESULT: OK" if status is True else "RESULT: NOK"
                line_log = f"{timestamp} | {prompt} | {line} | {result_str}\n"

                # 로그 저장용 임시 파일 생성
                temp_log_path = "/tmp/command_history.log"
                with open(temp_log_path, "w", encoding="utf-8") as f:
                    f.write(line_log)

                # 서버에 로그 파일 저장 요청
                save_to_server(self, output_path=temp_log_path, purpose="log")

                if is_semicolon:
                    self.poutput(result_str)

            except Exception as e:
                self.perror(f"명령어 기록 실패: {e}")
            finally:
                self._logging_in_progress = False

        if command_name == "exit":
            return result
        return False

    