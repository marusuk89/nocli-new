import json
import os
import shlex
import subprocess
from proto import message_pb2, message_pb2_grpc
from cli_server.core.workspace.ws_manager import WsManager, getWorkspace
from cli_server.common.utils.net_tools import check_ping
from cli_server.common.execution_helper import ExecutionHelper
from cli_server.ext.admincli_interface import AdminCliInterface

class CommandServiceServicer(message_pb2_grpc.CommandServiceServicer):
    def __init__(self):
        self.ws_manager = WsManager()
        self.helper = ExecutionHelper()
        self.admincli = AdminCliInterface()

    def SendCommand(self, request, context):
        #if not request.command == "set-cfg-scf":
            #print(f"[Server] Received: {request.command} - {request.payload}")

        try:
            print(f"command: {request.command}")
            if request.command == "dest-bts":
                bts_id = request.payload.strip()

                # workspace 세팅
                self.ws_manager.setActive(bts_id)

                # na_query 실행
                self.admincli = AdminCliInterface()
                ip = self.admincli.getBtsIpFromNaQuery(bts_id)

                # 디버깅 출력
                print(f"[DEBUG] 실제 getBtsIpFromNaQuery 결과: {ip}")
                print(f"[DEBUG] 현재 active_ws bts_id: {self.ws_manager.get('bts_id')}")

                # set-bts로 이미 입력된 IP 가져오기
                manual_ip = self.ws_manager.get("bts_ip")

                # 조회 실패 판정: ip가 None, 빈 문자열, "0.0.0.0"일 때
                if not ip or ip == "0.0.0.0":
                    if manual_ip:
                        return message_pb2.Response(
                            success=True,
                            result=f"BTS {bts_id} 설정됨 (조회 실패, 수동 입력 IP {manual_ip} 유지)"
                        )
                    else:
                        return message_pb2.Response(
                            success=False,
                            result=f"BTS {bts_id} 설정됨 (IP 조회 실패, 수동 입력 없음)"
                        )

                # 조회 성공한 경우
                if manual_ip and manual_ip != ip:
                    # 수동 입력과 조회 결과가 다르면 경고 (입력값 유지)
                    msg = (f"[경고] 수동 입력 IP({manual_ip})와 조회된 IP({ip})가 다릅니다. "
                        f"입력값({manual_ip})을 유지합니다.")
                    print("[DEBUG]", msg)
                    return message_pb2.Response(success=True, result=msg)
                else:
                    # 수동 입력 없거나 일치 → 조회값 세팅
                    self.ws_manager.set("bts_ip", ip)
                    return message_pb2.Response(success=True, result=f"BTS {bts_id} 설정 -> IP: {ip}")

            elif request.command == "set-bts":
                try:
                    tokens = shlex.split(request.payload.strip())
                except Exception as e:
                    return message_pb2.Response(success=False, result=f"인자 파싱 오류: {e}")

                if len(tokens) != 2:
                    return message_pb2.Response(success=False, result="인자 오류: BTS_ID, IP가 필요합니다.")

                bts_id, ip = tokens

                # workspace 세팅 (dest-bts와 동일하게)
                self.ws_manager.setActive(bts_id)
                self.ws_manager.set("bts_ip", ip)

                # dest-bts와 동일하게 admincli 초기화 (추후 동작 일관성 보장)
                self.admincli = AdminCliInterface()

                print(f"[DEBUG] 수동 세팅된 bts_id: {bts_id}, bts_ip: {ip}")
                print(f"[DEBUG] 현재 active_ws bts_id: {self.ws_manager.get('bts_id')}")

                return message_pb2.Response(success=True, result=f"BTS {bts_id} 설정 -> IP: {ip}")

            elif request.command == "auto-inte":
                # payload: "<BTS_ID> <VER> <MR> <NE_NAME> <BTS_IP>"  (shlex-quoted)
                try:
                    tokens = shlex.split(request.payload.strip())
                except Exception as e:
                    return message_pb2.Response(success=False, result=f"인자 파싱 오류: {e}")

                if len(tokens) != 5:
                    return message_pb2.Response(success=False, result="인자 오류: BTS_ID, VER, MR, NE_NAME, BTS_IP가 필요합니다.")

                bts_id, ver, mr, ne_name, bts_ip = tokens
                success, msg = self.admincli.executeBtsIntegration(bts_id, ver, mr, ne_name, bts_ip)
                return message_pb2.Response(success=success, result=msg)
            
            elif request.command == "auto-deinte":
                # payload: "<BTS_ID>" (shlex-quoted)
                try:
                    tokens = shlex.split(request.payload.strip())
                except Exception as e:
                    return message_pb2.Response(success=False, result=f"인자 파싱 오류: {e}")

                if len(tokens) != 1:
                    return message_pb2.Response(success=False, result="인자 오류: BTS_ID가 필요합니다.")

                bts_id = tokens[0]
                success, msg = self.admincli.executeBtsDeintegration(bts_id)
                return message_pb2.Response(success=success, result=msg)
            
            elif request.command == "dest-bts-ip":
                try:
                    ret = self.ws_manager.set("bts_ip", request.payload)  # 메시지 or True
                    success = True if ret else False
                    return message_pb2.Response(success=success, result=ret)
                except Exception as e:
                    return message_pb2.Response(success=False, result=f"Exception: {e}")

            elif request.command == "check-ping":
                ip = self.ws_manager.getBtsIp(request.payload)
                success, result = check_ping(ip)
                return message_pb2.Response(success=success, result=result)
            
            elif request.command == "update-sw-ver":
                try:
                    print(f"[디버그] 수신한 payload 원본: {request.payload}")
                    payload = json.loads(request.payload)
                    print(f"[디버그] 파싱된 payload: {payload} (type: {type(payload)})")

                    bts_id = payload["bts_id"]
                    input_file_name = payload["input_file"]  # 클라이언트는 파일명만 전달함

                    server_base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "sw_files")
                    full_file_path = os.path.abspath(os.path.join(server_base_dir, input_file_name))

                    if not os.path.isfile(full_file_path):
                        error_msg = f"[서버 오류] 파일이 존재하지 않습니다: {full_file_path}"
                        print(error_msg)
                        return message_pb2.Response(success=False, result=error_msg)

                    should_activate = payload.get("shouldActivate", True)
                    override_ru = payload.get("overrideIndependentRUSW", True)

                    result = self.admincli.softwareUpdate(
                        bts_id=bts_id,
                        input_file_path=full_file_path,
                        shouldActivate=should_activate,
                        overrideIndependentRUSW=override_ru
                    )

                    return message_pb2.Response(success=True, result=result)

                except Exception as e:
                    import traceback
                    tb_str = traceback.format_exc()
                    error_msg = f"[update-sw-ver 오류] {str(e)}\n\n[서버 Traceback]\n{tb_str}"
                    print(error_msg)
                    return message_pb2.Response(success=False, result=error_msg)
                    
            elif request.command == "check-soam":
                try:
                    bts_id = request.payload.strip()

                    result = self.admincli.getSwVersionStatus(bts_id)
                    return message_pb2.Response(success=True, result=result)

                except Exception as e:
                    return message_pb2.Response(success=False, result=f"[check-soam 오류] {str(e)}")
                
            elif request.command == "check-ssh":
                try:
                    bts_id = request.payload.strip()
                    ws = getWorkspace()
                    bts_ip = ws.get("bts_ip")

                    if not bts_ip:
                        return message_pb2.Response(success=False, result=f"[{bts_id}]의 IP가 설정되어 있지 않습니다.")

                    ssh_user = "nokia"
                    cmd = [
                        "ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5",
                        f"{ssh_user}@{bts_ip}", "exit"
                    ]

                    print("[디버그] 실행 명령어:", " ".join(cmd))  # 실제 SSH 명령어 출력

                    result = subprocess.run(
                        cmd,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )

                    if result.returncode == 0:
                        return message_pb2.Response(success=True, result=f"[{bts_id}] SSH 연결 성공 (IP: {bts_ip})")
                    else:
                        return message_pb2.Response(success=False, result=f"[{bts_id}] SSH 연결 실패 (IP: {bts_ip})")

                except Exception as e:
                    return message_pb2.Response(success=False, result=f"[check-ssh 오류] {str(e)}")

            elif request.command == "tgt_bts":
                return self.helper.handle_tgt_bts(request.payload)

            elif request.command == "no_tgt_bts":
                return self.helper.handle_no_tgt_bts(request.payload)

            elif request.command == "default":
                return self.helper.handle_default(request.payload)
            
            elif request.command == "list":
                return self.helper.handle_list(request.payload)

            elif request.command == "commit":
                return self.helper.handle_commit(request.payload)
            
            elif request.command == "commit-cli":
                return self.helper.handle_commit_cli(request.payload)

            elif request.command == "show_cfg":
                return self.helper.handle_show_cfg(request.payload)
            
            elif request.command == "set-cfg-scf":
                print("tmpl!!!!!")
                return self.helper.handle_set_cfg_scf(request.payload)

            elif request.command == "show-glb":
                return self.helper.handle_show_glb(request.payload)

            elif request.command == "show_sib":
                return self.helper.handle_show_sib(request.payload)

            elif request.command == "delmo":
                return self.helper.handle_delmo(request.payload)

            elif request.command == "go_top":
                return self.helper.handle_go_top(request.payload)
            
            elif request.command == "getHwInfo":
                print("hwinfo!!!!!")
                data = json.loads(request.payload)
                result = self.admincli.getHwInfo()
                return message_pb2.Response(success=True, result=result)

            elif request.command == "commission":
                print("commission!!!!")
                data = json.loads(request.payload)
                ws = getWorkspace()
                file = ws.get('final_file')
                skip = data.get("skip", False)
                activate = data.get("activate", False)
                result = self.admincli.commission(file, skipParameterRelationErrors=skip, shouldBeActivated=activate)
                return message_pb2.Response(success=True, result=result)

            elif request.command == "recommission":
                data = json.loads(request.payload)
                ws = getWorkspace()
                file = ws.get('final_file')
                skip = data.get("skip", False)
                activate = data.get("activate", False)

                result = self.admincli.recommission(file, skipParameterRelationErrors=skip, shouldBeActivated=activate)
                return message_pb2.Response(success=True, result=result)

            elif request.command == "activateplan":
                result = self.admincli.activatePlan(request.payload.strip())
                return message_pb2.Response(success=True, result=result)

            elif request.command == "generateScf":
                ws = getWorkspace()

                # 실행 직전 디버깅 출력
                print(f"[DEBUG] generateScf 실행 직전 workspace 객체: {ws}")
                if ws:
                    print(f"[DEBUG] generateScf 실행 직전 bts_id: {ws.get('bts_id')}")

                bts_id = ws.get("bts_id") if ws else None
                print("bts_id : ", bts_id)

                result = self.admincli.generateScf(bts_id=bts_id)
                return message_pb2.Response(success=True, result=result)
            elif request.command == "getRefXml":
                return self.helper.handle_get_ref_xml(request.payload)
            elif request.command == "updateCurrentXml":
                return self.helper.handle_update_current_xml(request.payload)
            elif request.command == "rulebook":
                return self.helper.handle_rulebook_file(request.payload)
            elif request.command == "saveFile":
                return self.helper.handle_save_file(request.payload)
            elif request.command == "getFile":
                return self.helper.handle_get_file(request.payload)
            elif request.command == "deleteFile":
                return self.helper.handle_delete_file(request.payload)
            elif request.command == "listTmpl":
                return self.helper.handle_list_tmpl(request.payload)
            elif request.command == "listScript":
                return self.helper.handle_list_script(request.payload)
            if request.command == "init-sw-ver":
                try:
                    entries = json.loads(request.payload)  # list of [bts_id, sw_ver]
                    result_text = self.helper.handle_init_sw_ver(entries)
                    return message_pb2.Response(success=True, result=result_text)
                except Exception as e:
                    return message_pb2.Response(success=False, result=f"[init-sw-ver 실패] {e}")

            else:
                print("else!!!!")
                default_line = f"{request.command} {request.payload}".strip()
                return self.helper.handle_default(default_line)

        except Exception as e:
            return message_pb2.Response(success=False, result=f"Exception: {e}")
