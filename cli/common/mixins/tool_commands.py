import os
import re
import shlex
from datetime import datetime
import xml.etree.ElementTree as ET
from cli.common.util.commit_utils import generate_cli_script_from_xml, load_param_dict, reverse_formula
import openpyxl
import json
from cli.settings import is_debug
from dotenv import load_dotenv

class ToolCommandMixin:
    def do_exec_script(self, arg):
        """
        스크립트 파일의 명령어들을 cmdqueue에 추가하여 자동 실행되게 합니다.
        사용법: exec-script <파일명>
        """
        filename = arg.strip()
        if not filename:
            self.perror("사용법: exec-script <파일명>")
            return

        try:
            # 경로 결정(실행 위치 기준)
            base_dir = os.getcwd()
            if self.env_type == "DEV":
                script_path = os.path.join(base_dir, "cli", "data", "scripts", filename)
            else:
                script_path = os.path.join(base_dir, "scripts", filename)

            if not os.path.exists(script_path):
                self.perror(f"[오류] 스크립트 파일이 존재하지 않습니다: {script_path}")
                return

            with open(script_path, "r", encoding="utf-8") as f:
                script_text = f.read()

            for i, raw_line in enumerate(script_text.splitlines(), 1):
                line = raw_line.strip()

                # LNBTS ID 치환 (init-bts 모드일 때만)
                if self.mode == "bts" and self.bts_id and "LNBTS 000" in line:
                    line = line.replace("LNBTS 000", f"LNBTS {self.bts_id}")
                    self.poutput(f"[INFO] 'LNBTS 000' → 'LNBTS {self.bts_id}' 으로 치환됨")

                if is_debug:
                    print(f"[디버그] {i}번째 줄 읽음: {repr(line)}")

                if not line or line.startswith("#"):
                    continue

                self.last_script_line = line  # default 오염 방지용

                tokens = shlex.split(line)
                if not tokens:
                    continue

                cmd = tokens[0]
                cmd_func = getattr(self, f"do_{cmd.replace('-', '_')}", None)

                if is_debug:
                    print("cmd       :", cmd)
                    print("cmd_func  :", cmd_func)

                if callable(cmd_func):
                    normalized_cmd = cmd.replace("-", "_")
                    new_line = " ".join([normalized_cmd] + tokens[1:])
                    if is_debug:
                        print(f"[실행] 공식 명령어 실행 → {normalized_cmd}")
                        print(f"new_line : {new_line}")

                    self._original_line = line
                    self.onecmd(new_line)
                else:
                    if is_debug:
                        print(f"[실행] default로 처리 → {line}")

                    self._original_line = line
                    self.default(line)

            if is_debug:
                self.poutput("[완료] exec-script 큐 설정 완료. 자동 실행됩니다.")

            # 오류 로그 처리
            today = datetime.today().strftime("%Y%m%d")
            log_filename = "execScript_error.log"
            log_path = os.path.join(base_dir, "..", "..", "data", "logs", today, log_filename)

            if self.exec_script_errors:
                os.makedirs(os.path.dirname(log_path), exist_ok=True)

                log_lines = []
                for err in self.exec_script_errors:
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    log_lines.append(f"[{timestamp}] {err}")
                log_text = "\n".join(log_lines)

                with open(log_path, "w", encoding="utf-8") as logf:
                    logf.write(log_text)

                if is_debug:
                    self.poutput(f"[완료] 오류 로그가 저장되었습니다 → {log_path}")

            else:
                if is_debug:
                    self.poutput("[완료] 오류 없이 exec-script가 실행되었습니다.")

        except Exception as e:
            self.perror(f"[오류] exec-script 실패: {e}")

    def cmdloop(self, intro=None):
        #print(f"[디버그] 현재 루프 클래스: {self.__class__}")
        return super().cmdloop(intro)
    
    ## 엔지니어
    ## 파라미터 rrcguardtimer의 경우 formular가 100을 나누는 로직으로 현재 formular공식에서 int로 값을 변경하는 과정에서 값이 누락되어 임의로 변경해야함
    ## int로 변환하지 않을시 int 형태여야 인지되는 파라미터도 있어서 rrcguardtimer용 함수를 만들어야 하는 상황이라 임의로 변경하기로 함
    def do_rulebook_to_dict_old(self, arg):
        """
        Nokia CLI SCF Rulebook XML을 파싱하여 dict로 변환합니다.
        사용법: rulebook-to-dict <XML파일명>
        """
        xml_filename = arg.strip()
        if not xml_filename:
            self.perror("사용법: rulebook-to-dict <XML파일명>")
            return

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        data_dir = os.path.join(base_dir, "..", "data", "rulebook")
        xml_path = os.path.join(data_dir, xml_filename)

        if not os.path.exists(xml_path):
            self.perror(f"XML 파일이 존재하지 않습니다: {xml_path}")
            return

        def strip_ns(tag):
            return tag.split("}")[-1] if "}" in tag else tag

        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            result = {}

            # param_dict 로드 (포뮬러 포함)
            param_dict = load_param_dict(self, self.rat_type, self.mo_version)

            for mo in root.iter():
                if strip_ns(mo.tag) != "managedObject":
                    continue

                class_attr = mo.attrib.get("class", "")
                mo_base = class_attr.split(":")[-1]
                dist = mo.attrib.get("distName", "")
                mo_id = None

                id_pattern = rf"{mo_base}-(\d+)"
                match = re.search(id_pattern, dist)
                if match:
                    mo_id = match.group(1)
                else:
                    mo_id = "__default__"

                if mo_base not in result:
                    result[mo_base] = {}

                if mo_id not in result[mo_base]:
                    result[mo_base][mo_id] = {}

                for p in mo.findall("./*"):
                    tag = strip_ns(p.tag)
                    pname = p.attrib.get("name")

                    # --------- [수정1] 리스트 파라미터 감지 ----------
                    if tag == "list":
                        param_data = {
                            "req": 0,
                            "ishow": 0,
                            "soam": 1,
                            "type": "list",
                            "isList": True,
                            "children": []
                        }

                        # 기존 방식: <item><p name=... /></item>
                        items = p.findall("./{*}item")
                        if items:
                            for item in items:
                                child_block = {}
                                for child_p in item.findall("./{*}p"):
                                    child_name = child_p.attrib.get("name")
                                    child_value = child_p.text.strip() if child_p.text else "0"

                                    # formula 적용
                                    key = (f"{mo_base}__{mo_id}", child_name)
                                    formula_info = param_dict.get(key) or (
                                        param_dict.get((mo_base, child_name)) if mo_id != "__default__" else None
                                    )
                                    if formula_info:
                                        formula = formula_info.get("formula")
                                        if formula:
                                            try:
                                                child_value = reverse_formula(reverse_formula(child_value, formula), formula)
                                            except Exception as e:
                                                if is_debug:
                                                    print(f"[경고] [list] 역공식 실패: {key}, 값={child_value}, 에러={e}")

                                    child_block[child_name] = {
                                        "req": 0,
                                        "ishow": 0,
                                        "soam": 1,
                                        "value": child_value
                                    }
                                if child_block:
                                    param_data["children"].append(child_block)

                        else:
                            # --------- [수정2] <p> 단독 리스트 형태 대응 ----------
                            for p_node in p.findall("./{*}p"):
                                val_text = p_node.text.strip() if p_node.text else "0"
                                param_data["children"].append({
                                    "val": {
                                        "req": 0,
                                        "ishow": 0,
                                        "soam": 1,
                                        "value": val_text
                                    }
                                })

                        result[mo_base][mo_id][p.attrib.get("name")] = param_data
                        continue  # 리스트면 아래 일반 파라미터 로직 패스

                    # --------- 일반 파라미터 처리 ----------
                    if not pname:
                        continue

                    value_text = p.text.strip() if p.text else "0"
                    cliopt = p.attrib.get("cliopt", "")

                    param_data = {
                        "req": 0,
                        "ishow": 0,
                        "soam": 1,
                        "value": value_text
                    }

                    if cliopt:
                        for entry in cliopt.split(","):
                            if "=" in entry:
                                k, v = entry.split("=")
                                k = k.strip()
                                v = v.strip().lower()
                                if k in {"req", "ishow", "soam"}:
                                    if v == "true":
                                        param_data[k] = 1
                                    elif v == "false":
                                        param_data[k] = 0
                                    else:
                                        try:
                                            param_data[k] = int(v)
                                        except ValueError:
                                            param_data[k] = 0

                    if param_data["req"] == 1:
                        param_data["value"] = "***"

                    key = (f"{mo_base}__{mo_id}", pname)
                    formula_info = param_dict.get(key)
                    if not formula_info and mo_id != "__default__":
                        fallback_key = (mo_base, pname)
                        formula_info = param_dict.get(fallback_key)
                        # if is_debug:
                            # print(f"[디버그] fallback 사용: {key} → {fallback_key}")
                    if formula_info:
                        formula = formula_info.get("formula")
                        if formula:
                            try:
                                v1 = reverse_formula(value_text, formula)
                                v2 = reverse_formula(v1, formula)
                                if is_debug:
                                    print(f"[디버그] {key}: 원본={value_text} → 1차={v1} → 2차={v2} (공식={formula})")
                                param_data["value"] = v2
                            except Exception as e:
                                print(f"[경고] 역공식 적용 실패: {key}, 값={value_text}, 에러={e}")

                    result[mo_base][mo_id][pname] = param_data

            output_path = os.path.join(data_dir, os.path.splitext(xml_filename)[0] + ".json")
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

            if is_debug:
                self.poutput(f"[완료] Rulebook JSON 파일이 저장되었습니다: {output_path}")

        except Exception as e:
            self.perror(f"[오류] XML 파싱 실패: {e}")

    def do_rulebook_to_dict(self, arg):
        """
        Nokia CLI SCF Rulebook XML을 파싱하여 dict로 변환합니다.
        사용법: rulebook-to-dict <XML파일명>
        """
        xml_filename = arg.strip()
        if not xml_filename:
            self.perror("사용법: rulebook-to-dict <XML파일명>")
            return

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        data_dir = os.path.join(base_dir, "..", "data", "rulebook")
        xml_path = os.path.join(data_dir, xml_filename)

        if not os.path.exists(xml_path):
            self.perror(f"XML 파일이 존재하지 않습니다: {xml_path}")
            return

        def strip_ns(tag):
            return tag.split("}")[-1] if "}" in tag else tag

        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            result = {}

            param_dict = load_param_dict(self, self.rat_type, self.mo_version)

            for mo in root.iter():
                if strip_ns(mo.tag) != "managedObject":
                    continue

                class_attr = mo.attrib.get("class", "")
                mo_base = class_attr.split(":")[-1]
                dist = mo.attrib.get("distName", "")
                mo_id = None

                id_pattern = rf"{mo_base}-(\d+)"
                match = re.search(id_pattern, dist)
                mo_id = match.group(1) if match else "__default__"

                if mo_base not in result:
                    result[mo_base] = {}
                if mo_id not in result[mo_base]:
                    result[mo_base][mo_id] = {}

                if dist and dist not in result:
                    result[dist] = {}

                def parse_param(p):
                    tag = strip_ns(p.tag)
                    pname = p.attrib.get("name")

                    if tag == "list":
                        param_data = {
                            "req": 0, "ishow": 0, "soam": 1,
                            "type": "list", "isList": True, "children": []
                        }
                        items = p.findall("./{*}item")
                        if items:
                            for item in items:
                                child_block = {}
                                for child_p in item.findall("./{*}p"):
                                    child_name = child_p.attrib.get("name")
                                    child_value = child_p.text.strip() if child_p.text else "0"

                                    key = (f"{mo_base}__{mo_id}", child_name)
                                    formula_info = param_dict.get(key) or (
                                        param_dict.get((mo_base, child_name)) if mo_id != "__default__" else None
                                    )
                                    if formula_info:
                                        formula = formula_info.get("formula")
                                        if formula:
                                            try:
                                                child_value = reverse_formula(reverse_formula(child_value, formula), formula)
                                            except:
                                                pass
                                    child_block[child_name] = {
                                        "req": 0, "ishow": 0, "soam": 1, "value": child_value
                                    }
                                if child_block:
                                    param_data["children"].append(child_block)
                        else:
                            for p_node in p.findall("./{*}p"):
                                val_text = p_node.text.strip() if p_node.text else "0"
                                param_data["children"].append({
                                    "val": {"req": 0, "ishow": 0, "soam": 1, "value": val_text}
                                })

                        return pname, param_data

                    if not pname:
                        return None, None

                    value_text = p.text.strip() if p.text else "0"
                    cliopt = p.attrib.get("cliopt", "")

                    param_data = {
                        "req": 0, "ishow": 0, "soam": 1, "value": value_text
                    }

                    if cliopt:
                        for entry in cliopt.split(","):
                            if "=" in entry:
                                k, v = entry.split("=")
                                k = k.strip()
                                v = v.strip().lower()
                                if k in {"req", "ishow", "soam"}:
                                    if v == "true":
                                        param_data[k] = 1
                                    elif v == "false":
                                        param_data[k] = 0
                                    else:
                                        try:
                                            param_data[k] = int(v)
                                        except:
                                            param_data[k] = 0

                    if param_data["req"] == 1:
                        param_data["value"] = "***"

                    key = (f"{mo_base}__{mo_id}", pname)
                    formula_info = param_dict.get(key) or (
                        param_dict.get((mo_base, pname)) if mo_id != "__default__" else None
                    )
                    if formula_info:
                        formula = formula_info.get("formula")
                        if formula:
                            try:
                                v1 = reverse_formula(value_text, formula)
                                v2 = reverse_formula(v1, formula)
                                param_data["value"] = v2
                            except:
                                pass

                    return pname, param_data

                for p in mo.findall("./*"):
                    pname, param_data = parse_param(p)
                    if pname and param_data:
                        result[mo_base][mo_id][pname] = param_data
                        result[dist][pname] = param_data

            output_path = os.path.join(data_dir, os.path.splitext(xml_filename)[0] + ".json")
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

            if is_debug:
                self.poutput(f"[완료] Rulebook JSON 저장 완료: {output_path}")

        except Exception as e:
            self.perror(f"[오류] XML 파싱 실패: {e}")
