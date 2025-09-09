import base64
import cmd2
import os
import xml.etree.ElementTree as ET
import json
import re
from io import BytesIO
from xml.etree.ElementTree import ElementTree
from datetime import datetime
from proto import message_pb2
from cli_server.core.workspace.ws_manager import WsManager, getWorkspace
from cli_server.common.utils.xml_utils import remove_empty_lines_from_str
from concurrent.futures import ThreadPoolExecutor, as_completed
from cli_server.ext.admincli_interface import AdminCliInterface
from cli_server.core.workspace.workspace import WorkSpace

class ExecutionHelper(cmd2.Cmd):
    is_debug = True

    def __init__(self):
        super().__init__()
        self.ws_manager = WsManager()
        self.xml_tree = None
        self.mo_class = None
        self.match_tail = None
        self.bts_id = None
        self.prompt = "nocli-cfg"

        self.admincli = AdminCliInterface()


    def handle_commit(self, arg):
        try:
            # payload: command_type||filename||message||translate_flag||translate_mode||xml_base64
            command_type, orig_filename, message, translate_flag, translate_mode, xml_base64 = arg.split("||", 5)

            ws = getWorkspace()
            bts_id = ws.get("bts_id")

            # XML 복원
            xml_data = base64.b64decode(xml_base64.encode("utf-8")).decode("utf-8")
            xml_data = remove_empty_lines_from_str(xml_data)

            # 기존 선언부 제거 및 새 선언부 추가
            lines = xml_data.strip().splitlines()
            body_lines = lines

            if not any("<header>" in line for line in body_lines):
                for i, line in enumerate(body_lines):
                    if "<cmData" in line:
                        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
                        header_block = f"""  <header>
                <log action="create" dateTime="{timestamp}"/>
            </header>"""
                        body_lines.insert(i + 1, header_block)
                        break

            # 선언부/raml 줄이 있으면 제거
            if lines[0].strip().startswith("<?xml"):
                body_lines = lines[2:]  # 첫 두 줄 제거

            header = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            raml_open = '<raml xmlns="raml21.xsd" version="2.1">'
            #raml_close = '</raml>'

            final_xml = f"{header}\n{raml_open}\n" + "\n".join(body_lines)

            # 경로 설정
            base_dir = os.path.dirname(os.path.abspath(__file__))
            save_dir = os.path.join(base_dir, "..", "data", "received", bts_id)
            os.makedirs(save_dir, exist_ok=True)
            filename = orig_filename
            save_path = os.path.join(save_dir, filename)

            # 저장
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(final_xml)

            self.poutput(f"[서버] XML 저장 완료: {save_path}")
            ws.set('final_file', save_path)

            if message:
                meta_path = save_path.replace(".xml", ".meta.txt")
                with open(meta_path, "w", encoding="utf-8") as f:
                    f.write(message.strip() + "\n")

            return message_pb2.Response(
                success=True,
                result=(
                    f"{save_path}"
                )
            )


        except Exception as e:
            return message_pb2.Response(success=False, result=f"[서버 오류] {str(e)}")
        
    def handle_commit_cli(self, arg):
        """
        클라이언트에서 전송한 CLI 텍스트 명령어 스크립트를 저장합니다.
        payload: commit-cli||filename||cli_base64
        """
        try:
            # payload 파싱
            command_type, filename, cli_base64 = arg.split("||", 2)

            # 디코딩
            cli_data = base64.b64decode(cli_base64.encode("utf-8")).decode("utf-8")
            cli_data = cli_data.strip()

            # 저장 경로 설정
            base_dir = os.path.dirname(os.path.abspath(__file__))
            save_dir = os.path.join(base_dir, "..", "data", "received")
            os.makedirs(save_dir, exist_ok=True)

            save_path = os.path.join(save_dir, filename)

            # 저장
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(cli_data)

            self.poutput(f"[서버] CLI 저장 완료: {save_path}")

            return message_pb2.Response(
                success=True,
                result=(
                    f"{save_path}"
                )
            )

        except Exception as e:
            return message_pb2.Response(success=False, result=f"[서버 오류] {str(e)}")


    def handle_set_cfg_scf(self, filename: str) -> message_pb2.Response:
        """
        요청한 XML 템플릿 파일을 읽어서 클라이언트로 전달합니다.
        (네임스페이스 처리 X, 원본 그대로 전달)
        """
        try:
            ws = getWorkspace()
            bts_id = ws.get("bts_id")
            base_dir = os.path.dirname(__file__)
            tmpl_dir = os.path.abspath(os.path.join(base_dir, "..", "data", "received", bts_id))
            if not filename.endswith(".xml"):
                filename += ".xml"

            xml_path = os.path.join(tmpl_dir, filename)

            if not os.path.exists(xml_path):
                return message_pb2.Response(success=False, result=f"{xml_path}에 {filename} 파일이 존재하지 않습니다.")

            # 파일 그대로 읽기
            with open(xml_path, "r", encoding="utf-8") as f:
                xml_text = f.read()

            ws.set('final_file', xml_path)

            return message_pb2.Response(success=True, result=xml_text)

        except Exception as e:
            return message_pb2.Response(success=False, result=f"서버 XML 전송 실패: {e}")
         
    def handle_get_ref_xml(self, file_name: str):
        file_name = file_name.strip()
        if not file_name.endswith(".xml"):
            file_name += ".xml"
        base_dir = os.path.dirname(os.path.abspath(__file__))
        ref_dir = os.path.join(base_dir, "..", "data", "ref")
        full_path = os.path.join(ref_dir, file_name)

        if not os.path.exists(full_path):
            return message_pb2.Response(success=False, result="참조 XML 파일이 존재하지 않습니다.")

        try:
            with open(full_path, "r", encoding="utf-8") as f:
                xml_str = f.read()
            return message_pb2.Response(success=True, result=xml_str)
        except Exception as e:
            return message_pb2.Response(success=False, result=f"[getRefXml] 파일 읽기 오류: {str(e)}")
        
    def handle_update_current_xml(self, xml_b64: str):
        try:
            xml_str = base64.b64decode(xml_b64.encode("utf-8")).decode("utf-8")

            root = ET.fromstring(xml_str)
            tree = ElementTree(root)

            base_dir = os.path.dirname(os.path.abspath(__file__))
            working_dir = os.path.join(base_dir, "..", "data", "received")
            os.makedirs(working_dir, exist_ok=True)

            file_path = os.path.join(working_dir, "current.xml")

            # 들여쓰기 + 선언부 포함
            ET.indent(root, space="  ")
            tree.write(file_path, encoding="utf-8", xml_declaration=True)

            return message_pb2.Response(success=True, result="XML 저장 완료")
        except Exception as e:
            return message_pb2.Response(success=False, result=f"[updateCurrentXml] 저장 오류: {str(e)}")
        
    def handle_show_glb(self, arg):
        """
        서버 data/received 디렉토리의 파일 목록을 필터링하여 반환
        payload: ext||limit||sort
        """
        try:
            ext, limit_str, sort_key = arg.split("||")
            limit = int(limit_str)

            base_dir = os.path.dirname(os.path.abspath(__file__))
            received_dir = os.path.join(base_dir, "..", "data", "received")
            os.makedirs(received_dir, exist_ok=True)

            # 파일 목록 가져오기
            files = []
            for name in os.listdir(received_dir):
                if ext == "xml" and not name.endswith(".xml"):
                    continue
                if ext == "txt" and not name.endswith(".txt"):
                    continue
                full_path = os.path.join(received_dir, name)
                if os.path.isfile(full_path):
                    mtime = os.path.getmtime(full_path)
                    files.append((name, mtime))

            # 정렬
            if sort_key == "name":
                files.sort(key=lambda x: x[0])
            elif sort_key == "key":
                # '__<task_key>' 기준으로 마지막 구간만 추출
                def extract_key(name):
                    parts = name.rsplit("__", 1)
                    return parts[1] if len(parts) == 2 else ""
                files.sort(key=lambda x: extract_key(x[0]))
            else:  # 기본: 시간 역순
                files.sort(key=lambda x: x[1], reverse=True)

            # 제한 적용
            if limit > 0:
                files = files[:limit]

            result = "\n".join(name for name, _ in files) or "(비어 있음)"
            return message_pb2.Response(success=True, result=result)

        except Exception as e:
            return message_pb2.Response(success=False, result=f"[서버 오류] {e}")
        
    ## 파일 저장 부분 ##

    def handle_save_file(self, payload: str) -> message_pb2.Response:
        """
        클라이언트에서 파일 저장 요청 처리
        payload 형식: purpose||filename||base64_encoded_content
        """
        try:
            parts = payload.split("||", 3)
            if len(parts) != 3:
                return message_pb2.Response(success=False, result="[handle_save_file] 잘못된 payload 형식")

            purpose, filename, encoded_content = parts
            content = base64.b64decode(encoded_content)

            base_dir = os.path.dirname(os.path.abspath(__file__))
            date_str = datetime.now().strftime("%Y%m%d")

            # 목적별 서브디렉토리 정의
            purpose_dirs = {
                "log": "logs",
                "autocomm": "autocomm",
                "rulebook": "rulebook",
                "cli": "scripts",
                "cfgTmpl": "scripts"
            }

            # 날짜 하위 디렉토리 여부 설정
            use_date_dir = {
                "log": True,
                "autocomm": True,
                "rulebook": False,
                "cli": True,
                "cfgTmpl": False
            }

            subdir = purpose_dirs.get(purpose)
            if not subdir:
                return message_pb2.Response(success=False, result=f"[handle_save_file] 정의되지 않은 purpose: {purpose}")

            # 저장 경로 결정
            if "/" in filename:
                save_path = os.path.join(base_dir, "..", "data", subdir, filename)
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
            else:
                if use_date_dir.get(purpose, False):
                    target_dir = os.path.join(base_dir, "..", "data", subdir, date_str)
                else:
                    target_dir = os.path.join(base_dir, "..", "data", subdir)
                os.makedirs(target_dir, exist_ok=True)
                save_path = os.path.join(target_dir, filename)

            # 확장자 기반 바이너리 판단
            binary_extensions = (".xlsx", ".xls", ".zip")
            is_binary = filename.lower().endswith(binary_extensions)
            mode = "wb" if is_binary else ("a" if purpose == "log" else "w")

            if is_binary:
                with open(save_path, mode) as f:
                    f.write(content)
            else:
                with open(save_path, mode, encoding="utf-8") as f:
                    f.write(content.decode("utf-8"))

            return message_pb2.Response(success=True, result=f"[handle_save_file] 저장 완료: {save_path}")

        except Exception as e:
            return message_pb2.Response(success=False, result=f"[handle_save_file] 예외 발생: {e}")

    def handle_get_file(self, payload: str) -> message_pb2.Response:
        """
        'purpose::filename' 형식의 payload를 받아 목적에 따라 파일을 읽음.
        엑셀 파일(.xlsx)은 바이너리로 처리하고, 나머지는 utf-8 텍스트 파일로 처리.
        """
        try:
            if "::" not in payload:
                return message_pb2.Response(success=False, result="payload 형식 오류: <purpose>::<filename>")

            purpose, filename = payload.split("::", 1)
            base_dir = os.path.dirname(__file__)
            data_root = os.path.abspath(os.path.join(base_dir, "..", "data"))

            # 목적에 따른 경로 분기
            if purpose == "prodmap":
                file_path = os.path.join(data_root, "prodmaptbl", filename)
            elif purpose == "template":
                file_path = os.path.join(data_root, "template", filename)
            elif purpose == "cli":
                file_path = os.path.join(data_root, "scripts", filename)
            elif purpose == "log":
                today = datetime.now().strftime("%Y%m%d")
                file_path = os.path.join(data_root, "logs", today, filename)
            elif purpose == "autocomm":
                today = datetime.now().strftime("%Y%m%d")
                file_path = os.path.join(data_root, "autocomm", today, filename)
            elif purpose == "rulebook":
                file_path = os.path.join(data_root, "rulebook", filename)
            elif purpose == "ruTemplate":
                file_path = os.path.join(data_root, "scripts", "ru_templates", filename)
            elif purpose == "dict":
                file_path = os.path.join(data_root, "dict", filename)
            elif purpose == "cablink":
                file_path = os.path.join(data_root, "cablink", filename)
            else:
                file_path = os.path.join(data_root, filename)  # fallback

            if not os.path.exists(file_path):
                return message_pb2.Response(success=False, result=f"[서버] 파일 없음: {file_path}")

            # 엑셀 파일은 바이너리로 읽기
            if filename.endswith(".xlsx"):
                with open(file_path, "rb") as f:
                    content = f.read()
            else:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    content = content.encode("utf-8")  # 텍스트는 바이트로 변환

            encoded = base64.b64encode(content).decode("utf-8")
            return message_pb2.Response(success=True, result=encoded)

        except Exception as e:
            return message_pb2.Response(success=False, result=f"[서버 오류] get-file 실패: {e}")
        
    def handle_delete_file(self, payload: str) -> message_pb2.Response:
        """
        삭제 요청을 처리하는 헬퍼 메서드
        payload 형식: "purpose||filename"
        """
        try:
            purpose, filename = payload.split("||", 1)

            if purpose != "autocomm":
                return message_pb2.Response(
                    success=False,
                    result=f"[제한] 삭제는 'autocomm' purpose만 허용됩니다. (요청: {purpose})"
                )

            base_dir = os.path.dirname(os.path.abspath(__file__))
            date_str = datetime.now().strftime("%Y%m%d")
            subdir = os.path.join("autocomm")

            target_path = os.path.join(base_dir, "..", "data", subdir, filename)

            if os.path.exists(target_path):
                os.remove(target_path)
                return message_pb2.Response(success=True, result=f"[삭제 완료] {target_path}")
            else:
                return message_pb2.Response(success=False, result=f"[삭제 실패] 파일이 존재하지 않음: {target_path}")

        except Exception as e:
            return message_pb2.Response(success=False, result=f"[handle_delete_file] 예외 발생: {e}")   

    def handle_list_tmpl(self, date_str: str) -> message_pb2.Response:
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            tmpl_dir = os.path.join(base_dir, "..", "data", "autocomm", date_str)

            if not os.path.exists(tmpl_dir):
                return message_pb2.Response(success=True, result="")  # 파일 없음

            files = [f for f in os.listdir(tmpl_dir) if f.endswith(".xlsx")]
            result = "||".join(files)
            return message_pb2.Response(success=True, result=result)
        except Exception as e:
            return message_pb2.Response(success=False, result=f"서버 오류: {e}")
        
    def handle_list_script(self, date_str: str) -> message_pb2.Response:
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            script_dir = os.path.join(base_dir, "..", "data", "autocomm", date_str)

            if not os.path.exists(script_dir):
                return message_pb2.Response(success=True, result="")  # 파일 없음

            files = [f for f in os.listdir(script_dir) if f.endswith(".cli")]
            result = "||".join(files)
            return message_pb2.Response(success=True, result=result)
        except Exception as e:
            return message_pb2.Response(success=False, result=f"[서버 오류] listScript 실패: {e}")

    def handle_init_sw_ver(self, entries):
        """
        entries: list of (bts_id, sw_ver)
        """
        results = []
        seen_bts = set()

        def update_fn(bts_id, sw_ver):
            try:
                self.ws_manager.setActive(bts_id)
                self.ws_manager.set("bts_id", bts_id)

                ip = self.admincli.getBtsIpFromNaQuery(bts_id)
                if not ip:
                    return {"bts_id": bts_id, "status": "fail", "message": "IP 조회 실패"}

                self.ws_manager.set("bts_ip", ip)

                file_path = self._resolve_sw_file_path(sw_ver)
                if not os.path.isfile(file_path):
                    return {"bts_id": bts_id, "status": "fail", "message": f"파일 없음: {file_path}"}

                result = self.admincli.softwareUpdate(
                    bts_id=bts_id,
                    input_file_path=file_path,
                    shouldActivate=False,
                    overrideIndependentRUSW=False
                )

                if isinstance(result, str):
                    # 실패 여부 판단
                    if re.search(r'"requestStatus"\s*:\s*"failed"', result):
                        # 실패 이유 추출 (마지막 메시지를 기준으로)
                        matches = re.findall(r'"requestMessage"\s*:\s*"([^"]*)"', result)
                        reason = matches[-1] if matches else "알 수 없는 오류"
                        return {
                            "bts_id": bts_id,
                            "status": "fail",
                            "message": f"소프트웨어 업데이트 실패 - {reason}",
                            "raw": result
                        }

                return {"bts_id": bts_id, "status": "success", "message": result}

            except Exception as e:
                import traceback
                return {
                    "bts_id": bts_id,
                    "status": "fail",
                    "message": f"{e}",
                    "trace": traceback.format_exc()
                }

        try:
            filtered_entries = []
            for bts_id, sw_ver in entries:
                if bts_id not in seen_bts:
                    seen_bts.add(bts_id)
                    filtered_entries.append((bts_id, sw_ver))
                else:
                    results.append({
                        "bts_id": bts_id,
                        "status": "skipped",
                        "message": "중복 건 생략"
                    })

            from concurrent.futures import ThreadPoolExecutor, as_completed
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = {
                    executor.submit(update_fn, bts_id, sw_ver): bts_id
                    for bts_id, sw_ver in filtered_entries
                }
                for future in as_completed(futures):
                    results.append(future.result())

            return json.dumps(results, ensure_ascii=False)

        finally:
            self.ws_manager.set("bts_ip", None)
            self.ws_manager.set("bts_id", None)


    def _resolve_sw_file_path(self, sw_ver):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "sw_files"))
        return os.path.join(base_dir, f"{sw_ver}.zip")
