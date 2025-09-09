from datetime import datetime
import traceback
import argparse
import base64
import copy
import os
import shlex
import xml.etree.ElementTree as ET
from cli.common.util.commit_utils import generate_translated_tree, warn_missing_required_params, generate_cli_script_from_xml
from cli.common.prettify_utils import prettify_xml
from cli.settings import grpc_stub
from proto import message_pb2
from cli.settings import is_debug

class CommitCommandMixin:
    def do_commit(self, arg):
        """
        최종 커밋을 수행합니다.
        공식 formula 2단계를 적용하여 저장 및 서버 전송합니다.
        사용법: commit -m "설명 메시지"
        """
        parser = argparse.ArgumentParser(prog="commit", add_help=False)
        parser.add_argument("-m", "--message", type=str, default="(commit)", help="설명 메시지")

        try:
            args = parser.parse_args(shlex.split(arg))
            # 내부적으로 commit-diff -t 2 실행
            if self.mode == "bts":
                cmd_arg = f'-t 1 -m "{args.message}"' if args.message else '-t 1'
                self.do_commit_all(cmd_arg)
            elif self.mode == "cell" and self.rat_type.upper() == "4G":
                cmd_arg = f'-t 2 -m "{args.message}"' if args.message else '-t 2'
                self.do_commit_diff(cmd_arg)
            elif self.mode == "cell" and self.rat_type.upper() == "5G":
                cmd_arg = f'-t 1 -m "{args.message}"' if args.message else '-t 1'
                self.do_commit_diff_para(cmd_arg)

        except SystemExit:
            self.perror("사용법: commit or commit [-m \"설명\"]")

    def do_commit_all(self, arg):
        """
        [내부용] 전체 XML 상태를 저장합니다.
        - 기본 XML 저장 (translate 옵션 없을 경우)
        - translated 저장: -t 1|2|r (1=once, 2=twice, r=reverse)
        """
        parser = argparse.ArgumentParser(prog="commit-all", add_help=False)
        parser.add_argument("-m", "--message", type=str, default="", help="저장 설명 메시지")
        parser.add_argument("-t", "--translate", choices=["1", "2", "r"],
                            help="translated 저장 (1=공식 1회, 2=2회, r=역공식)")

        try:
            args = parser.parse_args(shlex.split(arg))

            if not hasattr(self, "task_key"):
                self.perror("현재 task_key가 설정되지 않았습니다. 먼저 tgt-bts 명령어를 실행하세요.")
                return
            warnings = warn_missing_required_params(self.xml_tree, self.mo_param_dict)
            for line in warnings:
                self.poutput(line)

            if not hasattr(self, "xml_tree") or self.xml_tree is None:
                self.perror("XML이 아직 로드되지 않았습니다.")
                return

            root = copy.deepcopy(self.xml_tree.getroot())
            for elem in root.iter():
                if '}' in elem.tag:
                    elem.tag = elem.tag.split('}', 1)[1]
            self.xml_tree = ET.ElementTree(root)

            base_dir = os.getcwd() if self.env_type == "PROD" else os.path.dirname(os.path.abspath(__file__))

            if self.env_type == "PROD":
                today_str = datetime.now().strftime("%Y%m%d")
                data_dir = os.path.join(base_dir, "xml", today_str)
            else:
                data_dir = os.path.abspath(os.path.join(base_dir, "..", "..", "data"))

            generated_dir = os.path.join(data_dir, "generated")
            scripts_dir = os.path.join(data_dir, "generated")
            os.makedirs(generated_dir, exist_ok=True)
            os.makedirs(scripts_dir, exist_ok=True)

            ref = self.config.get("reference_config") if hasattr(self, "config") else None
            bts_id = getattr(self, "bts_id", "unknown")
            basename = os.path.splitext(ref)[0] if ref else f"MRBTS{bts_id}"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            task_key = self.task_key
            #print("self.param_dict : ", self.param_dict)
            param_dict_formula = self.param_dict

            if args.translate:
                if not param_dict_formula:
                    self.perror("translation dict가 없습니다.")
                    return

                mode_map = {"1": "once", "2": "twice", "r": "reverse"}
                mode = mode_map[args.translate]
                filename = f"{basename}__commit_{timestamp}_translated__{task_key}.xml"
                self.last_commit_file = filename
                output_path = os.path.join(generated_dir, filename)
                translated_tree = generate_translated_tree(self.xml_tree, param_dict_formula, mode=mode)
                xml_str = prettify_xml(translated_tree.getroot())
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(xml_str)
                if is_debug:
                    self.poutput(f"[클라] translated 저장 완료: {output_path}")
            else:
                filename = f"{basename}__commit_{timestamp}__{task_key}.xml"
                self.last_commit_file = filename
                output_path = os.path.join(generated_dir, filename)
                cmdata = self.xml_tree.find(".//{*}cmData")

                if cmdata is not None and cmdata.find("{*}header") is None:
                    header = ET.Element("header")
                    log = ET.SubElement(header, "log", {
                        "dateTime": datetime.now().strftime("%Y-%m-%dT%H:%M:%S+09:00"),
                        "action": "created"
                    })
                    cmdata.insert(0, header)

                xml_str = prettify_xml(self.xml_tree.getroot())
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(xml_str)
                if is_debug:
                    self.poutput(f"[클라] 기본 XML 저장 완료: {output_path}")

            # CLI 스크립트 생성 및 저장 (task_key 포함)
            cli_filename = filename.replace(".xml", ".cli")
            cli_path = os.path.join(scripts_dir, cli_filename)
            try:
                generate_cli_script_from_xml(output_path, cli_path)
                if is_debug:
                    self.poutput(f"[클라] CLI 스크립트 저장 완료: {cli_path}")
            except Exception as e:
                self.perror(f"[클라] CLI 스크립트 생성 실패: {e}")
                return

            # 서버 전송 (XML)
            xml_encoded = base64.b64encode(xml_str.encode("utf-8")).decode("utf-8")
            translate_flag = "1" if args.translate else "0"
            translate_mode = mode if args.translate else ""
            payload = f"commit||{filename}||{args.message}||{translate_flag}||{translate_mode}||{xml_encoded}"
            request = message_pb2.Request(command="commit", payload=payload)
            response = grpc_stub.SendCommand(request)
            if response.success:
                self.config.set("cmd_status", True)
                if is_debug:
                    self.poutput(f"[서버 응답] {response.result}")
            else:
                self.config.set("cmd_status", False)
                self.perror(f"[서버 오류] {response.result}")

            # 서버 전송 (CLI)
            try:
                with open(cli_path, "r", encoding="utf-8") as f:
                    cli_encoded = base64.b64encode(f.read().encode("utf-8")).decode("utf-8")
                payload_cli = f"commit-cli||{cli_filename}||{cli_encoded}"
                request_cli = message_pb2.Request(command="commit-cli", payload=payload_cli)
                response_cli = grpc_stub.SendCommand(request_cli)
                if response_cli.success:
                    if is_debug:
                        self.poutput(f"[서버 응답] CLI 저장 완료: {response_cli.result}")
                else:
                    self.perror(f"[서버 오류] CLI 저장 실패: {response_cli.result}")
            except Exception as e:
                self.perror(f"[서버 오류] CLI 전송 실패: {e}")

            if getattr(self, "_last_command_had_semicolon", False):
                self.poutput("")
                self.poutput("──────────── 저장 정보 ────────────")
                self.poutput(f"[XML] {output_path}")
                self.poutput(f"[CLI] {cli_path}")
                if response.success and response.result:
                    self.poutput(f"[서버 XML] {response.result}")
                    self.poutput(f"[서버 CLI] {response_cli.result}")
                self.poutput("──────────────────────────────────")

        except SystemExit:
            self.perror("사용법: commit-all [-m 설명] [-t 1|2|r]")

    def do_commit_diff(self, arg):
        """
        [내부용] 참조(ref) XML에 없는 managedObject만 추출하여 저장합니다.
        - 기본: diff commit 저장
        - 옵션: -t 1/2/r 공식 formula 적용 저장
        """
        parser = argparse.ArgumentParser(prog="commit-diff", add_help=False)
        parser.add_argument("-m", "--message", type=str, default="(cellcommit)", help="설명 메시지")
        parser.add_argument("-t", "--translate", choices=["1", "2", "r"],
                            help="translated 저장 방식 (1=1회, 2=2회, r=역공식)")

        try:
            args = parser.parse_args(shlex.split(arg))

            if not hasattr(self, "task_key"):
                self.perror("현재 task_key가 설정되지 않았습니다. 먼저 tgt-bts 명령어를 실행하세요.")
                self.config.set("cmd_status", False)
                return

            if not getattr(self, "allow_commit_diff", False):
                self.perror("이 모드에서는 commit-diff 명령을 사용할 수 없습니다.")
                self.config.set("cmd_status", False)
                return

            if not hasattr(self, "ref_tree") or self.ref_tree is None:
                self.perror("참조(ref) XML이 아직 로드되지 않았습니다. set-cfg-tmpl 먼저 실행하세요.")
                self.config.set("cmd_status", False)
                return
            
            warnings = warn_missing_required_params(self.xml_tree, self.mo_param_dict)
            for line in warnings:
                self.poutput(line)

            root = copy.deepcopy(self.xml_tree.getroot())
            for elem in root.iter():
                if '}' in elem.tag:
                    elem.tag = elem.tag.split('}', 1)[1]
            self.xml_tree = ET.ElementTree(root)

            base_dir = os.path.dirname(os.path.abspath(__file__))
            data_dir = os.path.abspath(os.path.join(base_dir, "..", "..", "data"))
            generated_dir = os.path.join(data_dir, "generated")
            scripts_dir = os.path.join(data_dir, "scripts")
            os.makedirs(generated_dir, exist_ok=True)
            os.makedirs(scripts_dir, exist_ok=True)

            ref = self.config.get("reference_config") if hasattr(self, "config") else None
            bts_id = getattr(self, "bts_id", "unknown")
            basename = os.path.splitext(ref)[0] if ref else f"MRBTS{bts_id}"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            task_key = self.task_key  # 🔑 task_key 반영

            ref_distnames = set()
            ref_cmdata = self.ref_tree.getroot().find(".//{*}cmData")
            if ref_cmdata is not None:
                for mo in ref_cmdata.findall("{*}managedObject"):
                    dist_name = mo.attrib.get("distName")
                    if dist_name:
                        ref_distnames.add(dist_name)

            new_root = ET.Element("raml", {"version": "2.0"})
            cm_data = ET.SubElement(new_root, "cmData", {"type": "plan"})
            current_cmdata = self.xml_tree.find(".//{*}cmData")
            if current_cmdata is not None:
                for mo in current_cmdata.findall("{*}managedObject"):
                    dist_name = mo.attrib.get("distName")
                    op = mo.attrib.get("operation", "")

                    # 조건 1: 삭제 처리된 MO는 무조건 포함 (ref에 있어도 상관없음)
                    if op == "delete":
                        cm_data.append(copy.deepcopy(mo))

                    # 조건 2: ref에 없는 MO는 생성 대상
                    elif dist_name and dist_name not in ref_distnames:
                        new_mo = copy.deepcopy(mo)
                        new_mo.set("operation", "create")
                        cm_data.append(new_mo)

            if len(cm_data.findall("{*}managedObject")) == 0:
                self.poutput("추가/수정된 정보가 없습니다. commit 파일이 생성되지 않습니다.")
                self.config.set("cmd_status", False)
                return

            param_dict_formula = self.param_dict

            if args.translate:
                if not param_dict_formula:
                    self.perror("translation dict가 없습니다.")
                    self.config.set("cmd_status", False)
                    return
                if isinstance(new_root, ET.Element):
                    new_root = ET.ElementTree(new_root)

                mode_map = {"1": "once", "2": "twice", "r": "reverse"}
                mode = mode_map[args.translate]

                filename = f"{basename}__cellcommit_{timestamp}_translated__{task_key}.xml"
                output_path = os.path.join(generated_dir, filename)
                translated_tree = generate_translated_tree(new_root, param_dict_formula, mode=mode)
                xml_str = prettify_xml(translated_tree.getroot())
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(xml_str)
                if is_debug:
                    self.poutput(f"[클라] translated 저장 완료: {output_path}")
            else:
                filename = f"{basename}__cellcommit_{timestamp}__{task_key}.xml"
                output_path = os.path.join(generated_dir, filename)
                xml_str = prettify_xml(new_root)
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(xml_str)
                if is_debug:
                    self.poutput(f"[클라] 기본 XML 저장 완료: {output_path}")

            self.last_commit_file = filename

            # CLI 스크립트 생성 및 저장
            cli_filename = filename.replace(".xml", ".cli")
            cli_path = os.path.join(scripts_dir, cli_filename)
            try:
                generate_cli_script_from_xml(output_path, cli_path)
                if is_debug:
                    self.poutput(f"[클라] CLI 스크립트 저장 완료: {cli_path}")
            except Exception as e:
                self.perror(f"[클라] CLI 스크립트 생성 실패: {e}")
                self.config.set("cmd_status", False)
                return

            # 서버 전송 (XML)
            command_type = "commit-diff"
            translate_flag = "1" if args.translate else "0"
            translate_mode = mode if args.translate else ""
            xml_encoded = base64.b64encode(xml_str.encode("utf-8")).decode("utf-8")
            payload = f"{command_type}||{filename}||{args.message}||{translate_flag}||{translate_mode}||{xml_encoded}"
            request = message_pb2.Request(command="commit", payload=payload)
            response = grpc_stub.SendCommand(request)
            if response.success:
                if is_debug:
                    self.poutput(f"[서버 응답] {response.result}")
            else:
                self.perror(f"[서버 오류] {response.result}")
                self.config.set("cmd_status", False)
                return

            # 서버 전송 (CLI)
            try:
                with open(cli_path, "r", encoding="utf-8") as f:
                    cli_encoded = base64.b64encode(f.read().encode("utf-8")).decode("utf-8")
                payload_cli = f"commit-cli||{cli_filename}||{cli_encoded}"
                request_cli = message_pb2.Request(command="commit-cli", payload=payload_cli)
                response_cli = grpc_stub.SendCommand(request_cli)
                if response_cli.success:
                    if is_debug:
                        self.poutput(f"[서버 응답] CLI 저장 완료: {response_cli.result}")
                else:
                    self.perror(f"[서버 오류] CLI 저장 실패: {response_cli.result}")
            except Exception as e:
                self.perror(f"[서버 오류] CLI 전송 실패: {e}")

            self.config.set("cmd_status", True)

            if getattr(self, "_last_command_had_semicolon", False):
                self.poutput("")
                self.poutput("──────────── 저장 정보 ────────────")
                self.poutput(f"[XML] {output_path}")
                self.poutput(f"[CLI] {cli_path}")
                if response.success and response.result:
                    self.poutput(f"[서버 XML] {response.result}")
                    self.poutput(f"[서버 CLI] {response_cli.result}")
                self.poutput("──────────────────────────────────")

        except SystemExit:
            self.config.set("cmd_status", False)
            self.perror("사용법: commit-diff [-m \"설명\"] -t 1|2|r")
        except Exception as e:
            self.config.set("cmd_status", False)
            self.perror(f"commit-diff 처리 실패: {e}")

    def do_commit_diff_para(self, arg):
        """
        [내부용] 참조(ref) XML과 비교하여 변경된 managedObject만 추출하여 저장합니다.
        - 신규 MO는 operation="create"
        - 기존 MO에서 p/리스트에 변경이 있으면 '최종 상태 전체'로 operation="update"
        - 옵션: -t 1/2/r 공식 formula 적용 저장
        """

        # === 내부 헬퍼들 (누락 방지 위해 이 함수 안에 정의) ===
        def _collect_p_map(mo):
            return {
                p.attrib.get("name"): (p.text.strip() if p.text else "")
                for p in mo.findall("{*}p")
                if p.attrib.get("name")
            }

        def _collect_list_map(mo):
            """리스트를 비교 가능한 구조로 수집: {list_name: {"p_values":[...], "items":[{...}, ...]}}"""
            out = {}
            for lst in mo.findall("{*}list"):
                lname = lst.attrib.get("name")
                if not lname:
                    continue
                p_values = [(p.text or "").strip() for p in lst.findall("{*}p")]
                items = []
                for item in lst.findall("{*}item"):
                    item_dict = {}
                    for p in item.findall("{*}p"):
                        pname = p.attrib.get("name")
                        if pname:
                            item_dict[pname] = (p.text or "").strip()
                    if item_dict:
                        items.append(item_dict)
                out[lname] = {"p_values": p_values, "items": items}
            return out

        def _normalize_list_for_compare(list_data):
            """비교 안정화를 위해 items의 dict를 (키정렬 튜플)로 변환."""
            norm = {}
            for lname, data in list_data.items():
                pvals = list(data.get("p_values", []))
                items_raw = data.get("items", [])
                items_norm = [tuple(sorted(d.items())) for d in items_raw]
                norm[lname] = {"p_values": pvals, "items": items_norm}
            return norm

        # === 어느 단계에서, 어느 MO에서 실패했는지 추적 ===
        stage = "init"
        current_dist = None

        try:
            parser = argparse.ArgumentParser(prog="commit-diff-para", add_help=False)
            parser.add_argument("-m", "--message", type=str, default="(cellcommit)", help="설명 메시지")
            parser.add_argument("-t", "--translate", choices=["1", "2", "r"],
                                help="translated 저장 방식 (1=1회, 2=2회, r=역공식)")
            args = parser.parse_args(shlex.split(arg))

            if not hasattr(self, "task_key"):
                self.perror("현재 task_key가 설정되지 않았습니다. 먼저 tgt-bts 명령어를 실행하세요.")
                self.config.set("cmd_status", False)
                return

            if not getattr(self, "allow_commit_diff", False):
                self.perror("이 모드에서는 commit-diff 명령을 사용할 수 없습니다.")
                self.config.set("cmd_status", False)
                return

            if not hasattr(self, "ref_tree") or self.ref_tree is None:
                self.perror("참조(ref) XML이 아직 로드되지 않았습니다. set-cfg-tmpl 먼저 실행하세요.")
                self.config.set("cmd_status", False)
                return

            # 0) 필수 파라미터 경고
            stage = "warn_missing_required_params"
            try:
                warnings = warn_missing_required_params(self.xml_tree, self.mo_param_dict)
                for line in warnings:
                    self.poutput(line)
            except Exception as e:
                self.perror(f"[warn] 필수 파라미터 점검 중 오류: {type(e).__name__}: {e}")

            # 1) 네임스페이스 정제
            stage = "strip_namespaces"
            root = copy.deepcopy(self.xml_tree.getroot())
            for elem in root.iter():
                if '}' in elem.tag:
                    elem.tag = elem.tag.split('}', 1)[1]
            self.xml_tree = ET.ElementTree(root)

            # 2) 경로/파일명 준비
            stage = "prepare_paths"
            base_dir = os.path.dirname(os.path.abspath(__file__))
            data_dir = os.path.abspath(os.path.join(base_dir, "..", "..", "data"))
            generated_dir = os.path.join(data_dir, "generated")
            scripts_dir = os.path.join(data_dir, "scripts")
            os.makedirs(generated_dir, exist_ok=True)
            os.makedirs(scripts_dir, exist_ok=True)

            ref = self.config.get("reference_config") if hasattr(self, "config") else None
            bts_id = getattr(self, "bts_id", "unknown")
            basename = os.path.splitext(ref)[0] if ref else f"MRBTS{bts_id}"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            task_key = self.task_key

            # 3) 참조 XML distName별 p/list 맵 구성
            stage = "build_ref_maps"
            ref_param_map = {}
            ref_list_map = {}
            ref_cmdata = self.ref_tree.getroot().find(".//{*}cmData")
            if ref_cmdata is not None:
                for mo in ref_cmdata.findall("{*}managedObject"):
                    dist = mo.attrib.get("distName")
                    if not dist:
                        continue
                    ref_param_map[dist] = _collect_p_map(mo)
                    ref_list_map[dist] = _normalize_list_for_compare(_collect_list_map(mo))

            # 4) 변경분 추출 (create/update)
            stage = "diff_current_vs_ref"
            new_root = ET.Element("raml", {"version": "2.0"})
            cm_data = ET.SubElement(new_root, "cmData", {"type": "plan"})
            current_cmdata = self.xml_tree.find(".//{*}cmData")

            if current_cmdata is not None:
                for mo in current_cmdata.findall("{*}managedObject"):
                    current_dist = mo.attrib.get("distName") or "<unknown>"
                    try:
                        # ★ 추가: 명시적 삭제는 그대로 통과
                        op = (mo.attrib.get("operation") or "").lower()
                        if op == "delete":
                            new_mo = ET.Element("managedObject", {
                                "class": mo.attrib.get("class", ""),
                                "distName": current_dist,
                                "version": mo.attrib.get("version", ""),
                                "operation": "delete",
                            })
                            cm_data.append(new_mo)
                            continue
                        # 신규 MO → create
                        if current_dist not in ref_param_map:
                            new_mo = copy.deepcopy(mo)
                            new_mo.set("operation", "create")
                            cm_data.append(new_mo)
                            continue

                        # 기존 MO → p/list 차이 감지
                        cur_p = _collect_p_map(mo)
                        ref_p = ref_param_map.get(current_dist, {})
                        p_changed = any(k not in ref_p or ref_p.get(k) != cur_p.get(k) for k in cur_p) \
                                    or any(k not in cur_p for k in ref_p)  # 키 추가/삭제도 차이

                        cur_l = _normalize_list_for_compare(_collect_list_map(mo))
                        ref_l = ref_list_map.get(current_dist, {})
                        list_names_changed = set(cur_l.keys()) != set(ref_l.keys())
                        default_list = {"p_values": [], "items": []}
                        list_content_changed = any(
                            cur_l.get(name, default_list) != ref_l.get(name, default_list)
                            for name in (cur_l.keys() | ref_l.keys())
                        )

                        if p_changed or list_names_changed or list_content_changed:
                            new_mo = copy.deepcopy(mo)
                            new_mo.set("operation", "update")
                            for child in new_mo.findall(".//managedObject"):
                                if "operation" in child.attrib:
                                    del child.attrib["operation"]
                            cm_data.append(new_mo)

                    except Exception as e:
                        # 어떤 MO에서 터졌는지, MO 일부까지 보여주기
                        mo_preview = (ET.tostring(mo, encoding="unicode")[:800]
                                    if mo is not None else "<no-mo>")
                        self.perror(f"[diff][{current_dist}] {type(e).__name__}: {e}\n"
                                    f"MO(preview): {mo_preview}")
                        raise  # 상위 예외 처리로 전달

            if len(cm_data.findall("managedObject")) == 0:
                self.poutput("변경된 정보가 없습니다. commit 파일이 생성되지 않습니다.")
                self.config.set("cmd_status", False)
                return

            # 5) 번역 모드 처리 / XML 문자열화
            filename = f"{basename}__cellcommit_para_{timestamp}"
            stage = "serialize_xml"
            if args.translate:
                filename += "_translated"
            filename += f"__{task_key}.xml"
            output_path = os.path.join(generated_dir, filename)

            if args.translate:
                stage = "translate_tree"
                param_dict_formula = self.param_dict
                if not param_dict_formula:
                    self.perror("translation dict가 없습니다.")
                    self.config.set("cmd_status", False)
                    return
                try:
                    mode_map = {"1": "once", "2": "twice", "r": "reverse"}
                    mode = mode_map[args.translate]
                    translated_tree = generate_translated_tree(ET.ElementTree(new_root), param_dict_formula, mode=mode)
                except KeyError as ke:
                    self.perror(f"[translate] KeyError: 누락 키={ke}. translation dict/매핑을 확인하세요.")
                    self.perror(traceback.format_exc())
                    self.config.set("cmd_status", False)
                    return
                except Exception as e:
                    self.perror(f"[translate] {type(e).__name__}: {e}\n{traceback.format_exc()}")
                    self.config.set("cmd_status", False)
                    return

                stage = "prettify_translated"
                xml_str = prettify_xml(translated_tree.getroot())
            else:
                stage = "prettify_xml"
                xml_str = prettify_xml(new_root)

            stage = "write_xml"
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(xml_str)
            self.last_commit_file = filename

            # 6) CLI 스크립트 생성
            stage = "generate_cli"
            try:
                cli_filename = filename.replace(".xml", ".cli")
                cli_path = os.path.join(scripts_dir, cli_filename)
                generate_cli_script_from_xml(output_path, cli_path)
                if is_debug:
                    self.poutput(f"[클라] CLI 스크립트 저장 완료: {cli_path}")
            except KeyError as ke:
                self.perror(f"[CLI 변환] KeyError: 누락 키={ke}. XML → CLI 매핑에서 해당 키가 필요한지 확인.")
                self.perror(traceback.format_exc())
                self.config.set("cmd_status", False)
                return
            except Exception as e:
                self.perror(f"[클라] CLI 스크립트 생성 실패: {e}\n{traceback.format_exc()}")
                self.config.set("cmd_status", False)
                return

            # 7) 서버 전송 (XML)
            stage = "send_xml"
            command_type = "commit-diff-para"
            translate_flag = "1" if args.translate else "0"
            translate_mode = mode if args.translate else ""
            xml_encoded = base64.b64encode(xml_str.encode("utf-8")).decode("utf-8")
            payload = f"{command_type}||{filename}||{args.message}||{translate_flag}||{translate_mode}||{xml_encoded}"
            request = message_pb2.Request(command="commit", payload=payload)
            response = grpc_stub.SendCommand(request)
            if response.success:
                if is_debug:
                    self.poutput(f"[서버 응답] {response.result}")
            else:
                self.perror(f"[서버 오류] {response.result}")
                self.config.set("cmd_status", False)
                return

            # 8) 서버 전송 (CLI)
            stage = "send_cli"
            try:
                with open(cli_path, "r", encoding="utf-8") as f:
                    cli_encoded = base64.b64encode(f.read().encode("utf-8")).decode("utf-8")
                payload_cli = f"commit-cli||{cli_filename}||{cli_encoded}"
                request_cli = message_pb2.Request(command="commit-cli", payload=payload_cli)
                response_cli = grpc_stub.SendCommand(request_cli)
                if response_cli.success:
                    if is_debug:
                        self.poutput(f"[서버 응답] CLI 저장 완료: {response_cli.result}")
                else:
                    self.perror(f"[서버 오류] CLI 저장 실패: {response_cli.result}")
            except Exception as e:
                self.perror(f"[서버 오류] CLI 전송 실패: {e}\n{traceback.format_exc()}")

            self.config.set("cmd_status", True)

        except SystemExit:
            self.config.set("cmd_status", False)
            self.perror("사용법: commit-diff-para [-m \"설명\"] -t 1|2|r")

        except Exception as e:
            # 최종 안전망: 단계/마지막 distName/스택 추가 출력
            self.config.set("cmd_status", False)
            tb = traceback.format_exc()
            self.perror(f"commit-diff-para 처리 실패 [{stage}][dist={current_dist}] "
                        f"{type(e).__name__}: {e}\n{tb}")
