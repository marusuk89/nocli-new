import argparse
import json
import os
import shlex
from proto import message_pb2
from cli.settings import grpc_stub
from cli.settings import is_debug

class SetupCommandMixin:
    def _next_request_id(self) -> int:
        if not hasattr(self, "request_id"):
            self.request_id = 1
        rid = self.request_id
        self.request_id += 1
        return rid
    
    def do_set_bts(self, arg):
        """
        BTS ID와 IP를 수동으로 세팅합니다.
        사용법: set-bts <BTS_ID> <IP>
        예시:  set-bts 2350003 4.5.13.5
        """
        tokens = shlex.split(arg)
        if len(tokens) != 2:
            self.perror("사용법: set-bts <BTS_ID> <IP>")
            return

        bts_id, bts_ip = tokens

        # gRPC 호출
        safe = [shlex.quote(x) for x in (bts_id, bts_ip)]
        payload = " ".join(safe)

        request = message_pb2.Request(command="set-bts", payload=payload)
        response = grpc_stub.SendCommand(request)

        if response.success:
            if hasattr(self, "config"):
                self.config.set("cmd_status", True)
            self.poutput(f"[BTS 설정] ID={bts_id}, IP={bts_ip}")
            return True
        else:
            if hasattr(self, "config"):
                self.config.set("cmd_status", False)
            self.perror(f"[설정 실패] {response.result}")
            return False

    def do_dest_bts(self, arg):
        """기지국 id를 통해 제대로 연결되었다면 ip주소를 반환합니다."""
        request = message_pb2.Request(command="dest-bts", payload=arg)
        response = grpc_stub.SendCommand(request)

        if response.success:
            if hasattr(self, "config"):
                self.config.set("dest_bts", arg.strip())
                self.config.set("cmd_status", True)
            
            self.poutput(f"[서버 설정] {response.result}")
            return True
        else:
            if hasattr(self, "config"):
                self.config.set("cmd_status", False)
            self.perror(f"[서버 오류] {response.result}")
            return False

    def do_auto_inte(self, arg):
        """
        BTS inte 명령을 실행합니다.
        사용법: auto-inte <BTS_ID> <VER> <MR> <NE_NAME> <BTS_IP>
        예시: auto-inte 2350003 SBTS25R2 MRC-5G/MR-LGU+5G Magok_Site100
        """
        tokens = shlex.split(arg)
        if len(tokens) != 5:
            self.perror("사용법: auto-inte <BTS_ID> <VER> <MR> <NE_NAME> <BTS_IP>")
            return

        bts_id, ver, mr, ne_name, bts_ip = tokens

        # gRPC 호출 (payload는 shlex.quote로 감싸 전달 → 서버에서 shlex.split로 안전 파싱)
        safe = [shlex.quote(x) for x in (bts_id, ver, mr, ne_name, bts_ip)]
        payload = " ".join(safe)

        request = message_pb2.Request(command="auto-inte", payload=payload)
        response = grpc_stub.SendCommand(request)

        if response.success:
            if hasattr(self, "config"):
                self.config.set("cmd_status", True)
            self.poutput(f"[integration 성공] {response.result}")
            return True
        else:
            if hasattr(self, "config"):
                self.config.set("cmd_status", False)
            self.perror(f"[integration 실패] {response.result}")
            return False
        
    def do_auto_deinte(self, arg):
        """
        BTS (Deintegration) 명령을 실행합니다.
        사용법: auto-deinte <BTS_ID>
        예시: auto-deinte 2350003
        """
        tokens = shlex.split(arg)
        if len(tokens) != 1:
            self.perror("사용법: auto-deinte <BTS_ID>")
            return

        bts_id = tokens[0]

        # gRPC 호출 (payload는 shlex.quote로 감싸 전달 → 서버에서 shlex.split로 안전 파싱)
        payload = shlex.quote(bts_id)

        request = message_pb2.Request(command="auto-deinte", payload=payload)
        response = grpc_stub.SendCommand(request)

        if response.success:
            if hasattr(self, "config"):
                self.config.set("cmd_status", True)
            self.poutput(f"[deinte 성공] {response.result}")
            return True
        else:
            if hasattr(self, "config"):
                self.config.set("cmd_status", False)
            self.perror(f"[deinte 실패] {response.result}")
            return False

    def do_dest_bts_ip(self, arg):
        """ip주소 세팅"""
        request = message_pb2.Request(command="dest-bts-ip", payload=arg)
        response = grpc_stub.SendCommand(request)

        if response.success:
            if hasattr(self, "config"):
                self.config.set("dest_bts_ip", arg.strip())
                self.config.set("cmd_status", True)
            print(f"[Server Reply] {response.result}")
            return True
        else:
            if hasattr(self, "config"):
                self.config.set("cmd_status", False)
            if is_debug:
                self.perror(f"[서버 오류] {response.result}")
            return False

    def do_check_ping(self, arg):
        """해당 기지국 id로 ping을 시도합니다."""
        request = message_pb2.Request(command="check-ping", payload=arg)
        response = grpc_stub.SendCommand(request)
        if response.success:
            if hasattr(self, "config"):
                self.config.set("cmd_status", True)
            print(f"[Server Reply] {response.result}")
            return True
        else:
            if hasattr(self, "config"):
                self.config.set("cmd_status", False)
            self.perror(f"[서버 오류] {response.result}")
            return False

    def do_update_sw_ver(self, arg):
        """BTS 소프트웨어 업데이트 수행"""
        parser = argparse.ArgumentParser(prog="update-sw-ver", add_help=False)
        parser.add_argument("bts_id", help="대상 BTS ID")
        parser.add_argument("--file", required=True, help="업데이트할 파일 이름 (예: swfile.zip)")
        parser.add_argument("--no-activate", action="store_true", help="업데이트 후 활성화 생략")
        parser.add_argument("--no-override", action="store_true", help="RU SW 무시 생략")

        try:
            args = parser.parse_args(shlex.split(arg))

            payload_dict = {
                "bts_id": args.bts_id,
                "input_file": args.file,
                "shouldActivate": not args.no_activate,
                "overrideIndependentRUSW": not args.no_override,
            }

            payload_json = json.dumps(payload_dict)
            request = message_pb2.Request(command="update-sw-ver", payload=payload_json)
            response = grpc_stub.SendCommand(request)

            if response.success:
                if hasattr(self, "config"):
                    self.config.set("cmd_status", True)
                self.poutput(f"[업데이트 완료] {response.result}")
            else:
                if hasattr(self, "config"):
                    self.config.set("cmd_status", False)
                self.perror(f"[서버 오류]\n{response.result}")

        except SystemExit:
            self.perror("사용법: update-sw-ver <bts_id> --file <파일명> [--no-activate] [--no-override]")

    def do_check_soam(self, arg):
        """미구현"""
        parser = argparse.ArgumentParser(prog="check-soam", add_help=False)
        parser.add_argument("bts_id", help="대상 BTS ID")

        try:
            args = parser.parse_args(shlex.split(arg))

            request = message_pb2.Request(command="check-soam", payload=args.bts_id)
            response = grpc_stub.SendCommand(request)
            if response.success:
                if hasattr(self, "config"):
                    self.config.set("cmd_status", True)
                if is_debug:
                    self.poutput(f"[서버 응답] {response.result}")
            else:
                if hasattr(self, "config"):
                    self.config.set("cmd_status", False)
                self.perror(f"[서버 오류] {response.result}")

        except SystemExit:
            self.perror("사용법: check-soam <bts_id>")

    def do_check_ssh(self, arg):
        """미구현"""
        parser = argparse.ArgumentParser(prog="check-ssh", add_help=False)
        parser.add_argument("bts_id", help="대상 BTS ID")

        try:
            args = parser.parse_args(shlex.split(arg))

            request = message_pb2.Request(command="check-ssh", payload=args.bts_id)
            response = grpc_stub.SendCommand(request)
            if response.success:
                if hasattr(self, "config"):
                    self.config.set("cmd_status", True)
                if is_debug:
                    self.poutput(f"[서버 응답] {response.result}")
            else:
                if hasattr(self, "config"):
                    self.config.set("cmd_status", False)
                self.perror(f"[서버 오류] {response.result}")

        except SystemExit:
            self.perror("사용법: check-ssh <bts_id>")