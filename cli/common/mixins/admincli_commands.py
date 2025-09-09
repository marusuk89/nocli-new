import argparse
import os
import json
import shlex
from proto import message_pb2
from cli.settings import grpc_stub
from cli.settings import is_debug

from cli.common.util.server_utils import load_from_server

class AdminCliCommandMixin:
    def _next_request_id(self) -> int:
        rid = self.request_id
        self.request_id += 1
        return rid
    
    def do_dnload_bts_cfg(self, arg):
        """
        BTS 설정 파일을 다운로드 후 UI-value 기반 환경으로 복원합니다.
        자동 수행 단계:
        1. dnload-bts-cfg (json-value 다운로드)
        2. set-cfg-scf genScf (ref 설정)
        3. commit-all -t r (json → ui-value 변환 저장)
        4. set-cfg-scf <ui-value.xml> (ref 갱신)
        """
        try:
            # 1단계: json-value 상태 다운로드
            self.do_dnload_bts_cfg_raw(arg)

            # 2단계: json-value 기준을 ref로 등록
            self.do_set_cfg_scf("genScf")

            # 3단계: 역공식 적용하여 ui-value로 커밋
            commit_arg = '-t r'
            self.last_commit_file = None  # 초기화

            # commit-all 실행 시 내부에서 self.last_commit_file에 저장되었다고 가정
            self.do_commit_all(commit_arg)

            if not self.last_commit_file:
                self.perror("commit된 파일명을 확인할 수 없습니다. commit-all 내부를 확인하세요.")
                return

            # 4단계: UI-value 기반으로 다시 ref 설정
            self.do_set_cfg_scf(self.last_commit_file)

            # 5단계: set_cfg_scf를 통해 받은 xml_tree에서 smod의 prodcodeplanned 파라미터를 통해 du타입 설정
            self._set_du_type_from_smod()

        except Exception as e:
            self.perror(f"dnload-bts-cfg 처리 중 오류 발생: {e}")

    def prepare_dummy_flag(self, mrbts_id_str: str, radio_type):
        """
        dummy 존재 여부(kill_dummy_flag) 판단만을 위한 최소한의 동작 수행
        (auto-comm gen-script 용도 전용)
        """
        try:
            # 1단계: json-value 상태만 다운로드 (raw)
            self.do_dnload_bts_cfg_raw("")  # mrbts_id는 dest-bts 기준으로 설정됨

            # 2단계: json-value 기준을 ref로 등록
            self.do_set_cfg_scf("genScf")

            # 3단계: xml_tree로부터 dummy 존재 여부 확인
            if radio_type.upper() == "4G":
                self.kill_dummy_flag = self._check_dummy_exists_4g()
            elif radio_type.upper() == "5G":
                self.kill_dummy_flag = self._check_dummy_exists_5g()

            if is_debug:
                print(f"[DEBUG] (prepare_dummy_flag) kill_dummy_flag = {self.kill_dummy_flag}")

        except Exception as e:
            self.perror(f"[오류] dummy 여부 준비 중 오류 발생: {e}")

    def _check_dummy_exists_4g(self) -> bool:
        """
        현재 xml_tree에서 더미 MO(RMOD-32767, LNCEL-65534, LNCEL-65535)가
        모두 존재하는지 확인한다.
        """
        try:
            if not self.xml_tree:
                return False
            root = self.xml_tree.getroot()

            required_dummies = {
                "RMOD-32767": False,
                "LNCEL-65534": False,
                "LNCEL-65535": False,
            }

            for mo in root.findall(".//managedObject"):
                dist_name = mo.attrib.get("distName", "")
                for key in required_dummies:
                    if key in dist_name:
                        required_dummies[key] = True

            return all(required_dummies.values())

        except Exception as e:
            self.perror(f"dummy 존재 확인 중 오류 발생: {e}")
            return False
    
    def _check_dummy_exists_5g(self) -> bool:
        """
        현재 xml_tree에서 더미 MO(RMOD-31, NRCELL-6144)가
        모두 존재하는지 확인한다.
        """
        try:
            if not self.xml_tree:
                return False
            root = self.xml_tree.getroot()

            required_dummies = {
                "RMOD-31": False,
                "NRCELL-6144": False,
            }

            for mo in root.findall(".//managedObject"):
                dist_name = mo.attrib.get("distName", "")
                for key in required_dummies:
                    if key in dist_name:
                        required_dummies[key] = True

            return all(required_dummies.values())

        except Exception as e:
            self.perror(f"dummy 존재 확인 중 오류 발생: {e}")
            return False

    def do_dnload_bts_cfg_raw(self, arg):
        if is_debug:
            print("self.bts_id : ", self.bts_id)
        request = message_pb2.Request(command="generateScf", payload=self.bts_id)
        response = grpc_stub.SendCommand(request)
        if response.success:
            self.config.set("cmd_status", True)
            if is_debug:
                self.poutput(f"[서버 응답] {response.result}")
        else:
            self.config.set("cmd_status", False)
            self.perror(f"[서버 오류] {response.result}")

    def do_gethwinfo(self, arg):
        request = message_pb2.Request(command="getHwInfo")
        if is_debug:
            print("raw payload", request.payload)
        response = grpc_stub.SendCommand(request)
        if response.success:
            self.config.set("cmd_status", True)
            if is_debug:
                self.poutput(f"[서버 응답] {response.result}")
        else:
            self.config.set("cmd_status", False)
            self.perror(f"[서버 오류] {response.result}")
    
    def _set_du_type_from_smod(self):
        """
        self.xml_tree에서 SMOD-1의 prodCodePlanned 값을 읽고,
        PRODMAPTBL.json을 기반으로 DU10 또는 DU20 타입을 자동 설정합니다.
        """
        try:
            root = self.xml_tree.getroot()

            # SMOD-1을 찾음
            smod_elem = None
            for mo in root.findall(".//managedObject"):
                if mo.attrib.get("class", "").endswith("SMOD") and "SMOD-1" in mo.attrib.get("distName", ""):
                    smod_elem = mo
                    break

            if smod_elem is None:
                self.perror("[오류] xml_tree에서 SMOD-1을 찾을 수 없습니다.")
                return

            prod_code = None
            for p in smod_elem.findall("p"):
                if p.attrib.get("name") == "prodCodePlanned":
                    prod_code = p.text.strip()
                    break

            if not prod_code:
                self.perror("[오류] prodCodePlanned 값이 없습니다.")
                return
            
            data = load_from_server("PRODMAPTBL.json", "json", "prodmap")
            prod_dict = data.get("PRODMAPTBL", {}).get("value", {}) if data else {}
            if not prod_dict:
                self.perror("[오류] 서버에서 PRODMAPTBL.json 데이터를 가져오지 못했습니다.")
                return

            matched_type = None
            for ru_type, code in prod_dict.items():
                print("code = ", code)
                print("prod_code = ", prod_code)
                if code == prod_code:
                    matched_type = ru_type
                    break

            if not matched_type:
                self.perror(f"[오류] prodCodePlanned 값 '{prod_code}'에 해당하는 RU 타입을 찾을 수 없습니다.")
                return

            # RU 타입 앞 두 글자 기준으로 DU 타입 결정
            if self.rat_type.upper() == "4G" :
                print("!matched_type = ", matched_type)
                prefix = matched_type[:2].upper()
                if prefix == "AS":
                    du_type = "DU20"
                elif prefix == "FS":
                    du_type = "FSMF"
                else:
                    self.perror(f"[오류] RU 타입 '{matched_type}'에서 DU 타입을 판별할 수 없습니다.")
                    return

            elif self.rat_type.upper() == "5G" :
                print("matched_type = ", matched_type)
                if matched_type == "ASIK":
                    du_type = "DU10"
                elif matched_type == "ASIL":
                    du_type = "DU20"
                else:
                    self.perror(f"[오류] RU 타입 '{matched_type}'에서 DU 타입을 판별할 수 없습니다.")
                    return
                
            if is_debug:
                    print("set_du_type_from_smod : ", du_type)

            # set-du-type 자동 실행
            self.do_set_du_type(du_type)

        except Exception as e:
            self.perror(f"DU 타입 자동 설정 중 오류 발생: {e}")
    
    def do_commission(self, arg):
        parser = argparse.ArgumentParser(prog="commission")
        parser.add_argument("filename")
        parser.add_argument("--skip", type=bool, default=False)
        parser.add_argument("--activate", type=bool, default=False)
        args = parser.parse_args(shlex.split(arg))

        payload = json.dumps({
            "requestId": self._next_request_id(),
            "file": args.filename,
            "skip": args.skip,
            "activate": args.activate
        })
        if is_debug:
            print("payload:", payload)
        request = message_pb2.Request(command="commission", payload=payload)
        if is_debug:
            print("raw payload:", request.payload)
        response = grpc_stub.SendCommand(request)
        if response.success:
            self.config.set("cmd_status", True)
            if is_debug:
                self.poutput(f"[서버 응답] {response.result}")
        else:
            self.config.set("cmd_status", False)
            self.perror(f"[서버 오류] {response.result}")


    def do_recommission(self, arg):
        parser = argparse.ArgumentParser(prog="recommission")
        parser.add_argument("filename")
        parser.add_argument("--skip", action="store_true", help="스킵 여부")
        parser.add_argument("--activate", action="store_true", help="활성화 여부")
        args = parser.parse_args(shlex.split(arg))

        payload = json.dumps({
            "requestId": self._next_request_id(),
            "file": args.filename,
            "skip": args.skip,
            "activate": args.activate
        })
        request = message_pb2.Request(command="recommission", payload=payload)
        response = grpc_stub.SendCommand(request)
        if response.success:
            self.config.set("cmd_status", True)
            if is_debug:
                self.poutput(f"[서버 응답] {response.result}")
        else:
            self.config.set("cmd_status", False)
            self.perror(f"[서버 오류] {response.result}")

    def do_apply_bts_cfg_commission(self, arg):
        """
        BTS 설정 파일을 적용합니다 (활성화하지 않음).
        사용법: commission-bts-cfg
        """
        if not self.last_commit_file:
            self.perror("최근 커밋된 파일이 없습니다. 먼저 commit을 수행하세요.")
            return

        try:
            payload = json.dumps({
                "requestId": self._next_request_id(),
                "file": self.last_commit_file,
                "skip": False,
                "activate": False
            })
            request = message_pb2.Request(command="commission", payload=payload)
            response = grpc_stub.SendCommand(request)
            if response.success:
                self.config.set("cmd_status", True)
                self.poutput(f"[서버 응답] {response.result}")
            else:
                self.config.set("cmd_status", False)
                self.perror(f"[서버 오류] {response.result}")

        except SystemExit:
            self.perror("사용법: apply-bts-cfg")

    def do_act_bts_cfg_commission(self, arg):
        """
        BTS 설정 파일을 적용하고 즉시 활성화합니다.
        사용법: act-bts-cfg [--skip]
        """
        parser = argparse.ArgumentParser(prog="act-bts-cfg")
        parser.add_argument("--skip", action="store_true", help="유효성 검사 생략")

        try:
            args = parser.parse_args(shlex.split(arg))
            payload = json.dumps({
                "requestId": self._next_request_id(),
                "file": self.last_commit_file,
                "skip": args.skip,
                "activate": True
            })
            request = message_pb2.Request(command="commission", payload=payload)
            response = grpc_stub.SendCommand(request)
            if response.success:
                self.config.set("cmd_status", True)
                self.poutput(f"[서버 응답] {response.result}")
            else:
                self.config.set("cmd_status", False)
                self.perror(f"[서버 오류] {response.result}")
        except SystemExit:
            self.perror("사용법: act-bts-cfg <filename> [--skip]")

    def do_apply_bts_cfg(self, arg):
        """
        BTS 설정 파일을 적용합니다 (활성화하지 않음).
        사용법: apply-bts-cfg

        - init-bts 모드에서는 'commission'
        - init-cell 모드에서는 'recommission'
        """
        if not self.last_commit_file:
            self.perror("최근 커밋된 파일이 없습니다. 먼저 commit을 수행하세요.")
            return

        if self.mode == "bts":
            command_name = "commission"
        elif self.mode == "cell":
            command_name = "recommission"
        else:
            self.perror(f"[오류] apply-bts-cfg 명령은 'bts' 또는 'cell' 모드에서만 사용할 수 있습니다. (현재: {self.mode})")
            return

        try:
            payload = json.dumps({
                "requestId": self._next_request_id(),
                "file": self.last_commit_file,
                "skip": False,
                "activate": False
            })
            request = message_pb2.Request(command=command_name, payload=payload)
            response = grpc_stub.SendCommand(request)

            if response.success:
                self.config.set("cmd_status", True)
                self.poutput(f"[서버 응답] {response.result}")
            else:
                self.config.set("cmd_status", False)
                self.perror(f"[서버 오류] {response.result}")

        except SystemExit:
            self.perror("사용법: apply-bts-cfg")


    def do_apply_bts_cfg_old(self, arg):
        """
        BTS 설정 파일을 적용합니다 (활성화하지 않음).
        사용법: apply-bts-cfg
        """
        if not self.last_commit_file:
            self.perror("최근 커밋된 파일이 없습니다. 먼저 commit을 수행하세요.")
            return

        try:
            # args = parser.parse_args(shlex.split(arg))
            payload = json.dumps({
                "requestId": self._next_request_id(),
                "file": self.last_commit_file,
                "skip": False,
                "activate": False
            })
            request = message_pb2.Request(command="recommission", payload=payload)
            response = grpc_stub.SendCommand(request)
            if response.success:
                self.config.set("cmd_status", True)
                self.poutput(f"[서버 응답] {response.result}")
            else:
                self.config.set("cmd_status", False)
                self.perror(f"[서버 오류] {response.result}")

        except SystemExit:
            self.perror("사용법: apply-bts-cfg <filename>")

    def do_act_bts_cfg(self, arg):
        """
        BTS 설정 파일을 적용하고 즉시 활성화합니다.
        사용법: act-bts-cfg [--skip]

        - init-bts 모드에서는 'commission'
        - init-cell 모드에서는 'recommission'
        """
        if not self.last_commit_file:
            self.perror("최근 커밋된 파일이 없습니다. 먼저 commit을 수행하세요.")
            return

        if self.mode == "bts":
            command_name = "commission"
        elif self.mode == "cell":
            command_name = "recommission"
        else:
            self.perror(f"[오류] act-bts-cfg 명령은 'bts' 또는 'cell' 모드에서만 사용할 수 있습니다. (현재: {self.mode})")
            return

        parser = argparse.ArgumentParser(prog="act-bts-cfg")
        parser.add_argument("--skip", action="store_true", help="유효성 검사 생략")

        try:
            args = parser.parse_args(shlex.split(arg))
            payload = json.dumps({
                "requestId": self._next_request_id(),
                "file": self.last_commit_file,
                "skip": args.skip,
                "activate": True
            })
            request = message_pb2.Request(command=command_name, payload=payload)
            response = grpc_stub.SendCommand(request)

            if response.success:
                self.config.set("cmd_status", True)
                self.poutput(f"[서버 응답] {response.result}")
            else:
                self.config.set("cmd_status", False)
                self.perror(f"[서버 오류] {response.result}")
        except SystemExit:
            self.perror("사용법: act-bts-cfg [--skip]")

    def do_act_bts_cfg_old(self, arg):
        """
        BTS 설정 파일을 적용하고 즉시 활성화합니다.
        사용법: act-bts-cfg [--skip]
        """
        parser = argparse.ArgumentParser(prog="act-bts-cfg")
        parser.add_argument("--skip", action="store_true", help="유효성 검사 생략")

        try:
            args = parser.parse_args(shlex.split(arg))
            payload = json.dumps({
                "requestId": self._next_request_id(),
                "file": self.last_commit_file,
                "skip": args.skip,
                "activate": True
            })
            request = message_pb2.Request(command="recommission", payload=payload)
            response = grpc_stub.SendCommand(request)
            if response.success:
                self.config.set("cmd_status", True)
                self.poutput(f"[서버 응답] {response.result}")
            else:
                self.config.set("cmd_status", False)
                self.perror(f"[서버 오류] {response.result}")
        except SystemExit:
            self.perror("사용법: act-bts-cfg <filename> [--skip]")

    def do_activateplan(self, arg):
        parser = argparse.ArgumentParser(prog="activateplan")
        parser.add_argument("deltaDN")
        args = parser.parse_args(shlex.split(arg))

        payload = json.dumps({
            "requestId": self._next_request_id(),
            "deltaDN": args.deltaDN
        })
        request = message_pb2.Request(command="activateplan", payload=payload)
        response = grpc_stub.SendCommand(request)
        if response.success:
            self.config.set("cmd_status", True)
            if is_debug:
                self.poutput(f"[서버 응답] {response.result}")
        else:
            self.config.set("cmd_status", False)
            self.perror(f"[서버 오류] {response.result}")