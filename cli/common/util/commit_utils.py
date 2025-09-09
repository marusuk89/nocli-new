import os
import json
import xml.etree.ElementTree as ET
import re
import copy
from cli.settings import is_debug
from cli.common.util.server_utils import load_from_server

def load_param_dict(self, rat_type: str, version_code: str):
    filename = f"{version_code}_formula_param_dict.json"
    try:
        raw_dict = load_from_server(filename, "json", purpose="dict")
        return {tuple(k.split("::")): v for k, v in raw_dict.items()}
    except Exception as e:
        self.perror(f"[오류] param_dict 로드 실패: {e}")
        return {}

def load_mo_param_dict(self, rat_type: str, version_code: str, du_type: str):
    filename = f"{du_type.upper()}_{version_code}_mo_param_dict.json"
    try:
        raw_dict = load_from_server(filename, "json", purpose="dict")
        return raw_dict
    except Exception as e:
        self.perror(f"[오류] mo_param_dict 로드 실패: {e}")
        return {}

def load_ru_dict(self, rat_type):
    if rat_type.upper() == "4G":
        filename = "ru_info_for_antl.json"
    elif rat_type.upper() == "5G":
        filename = "ru_info_for_phyant.json"
    else:
        self.perror(f"[오류] 지원되지 않는 RAT 타입입니다: {rat_type}")
        return {}
    try:
        print("filename = ",filename)
        raw_dict = load_from_server(filename, "json", purpose="dict")
        return raw_dict
    except Exception as e:
        self.perror(f"[오류] RU 정보 로드 실패: {e}")
        return {}

def apply_formula_once(original_value, formula):
    try:
        eval_globals = {"__builtins__": {}}
        eval_locals = {"UI_VALUE": float(original_value)}
        result = eval(formula, eval_globals, eval_locals)
        int_result = int(round(result))

        if is_debug:
            print(f"[디버그] apply_formula_once: original={original_value}, formula='{formula}', result={int_result}")
        return str(int_result)
    except Exception as e:
        if is_debug:
            print(f"[디버그] apply_formula_once 에러: original={original_value}, formula='{formula}', 에러={e}")
        return str(original_value)

def apply_formula_twice(original_value, formula):
    try:
        # 1차 적용
        eval_globals = {"__builtins__": {}}
        eval_locals = {"UI_VALUE": float(original_value)}
        intermediate = eval(formula, eval_globals, eval_locals)

        # 2차 적용
        eval_locals = {"UI_VALUE": float(intermediate)}
        final_result = eval(formula, eval_globals, eval_locals)
        int_result = int(round(final_result))
        if is_debug:
           print(f"[디버그] apply_formula_twice: original={original_value}, formula='{formula}', result={int_result}")
        return str(int_result)
    except Exception as e:
        if is_debug:
            print(f"[디버그] apply_formula_twice 에러: original={original_value}, formula='{formula}', 에러={e}")
        return str(original_value)

def reverse_formula(encoded_value, formula):
    try:
        encoded_value = float(encoded_value)

        # 정규식 기반 단순 선형 공식 해석
        match = re.match(r"\(UI_VALUE\s*([\+\-\*/])\s*([0-9\.]+)\)\s*\*\s*([0-9\.]+)\s*/\s*([0-9\.]+)", formula)
        if not match:
            raise ValueError("지원되지 않는 공식 형식")

        op, offset, mul, div = match.groups()
        offset = float(offset)
        mul = float(mul)
        div = float(div)

        # 정방향: ((UI ± offset) * mul / div) = encoded
        if op == "+":
            ui_value = (encoded_value * div / mul) - offset
        elif op == "-":
            ui_value = (encoded_value * div / mul) + offset
        else:
            raise ValueError("지원되지 않는 연산자")

        #int_result = int(round(ui_value))
        if is_debug:
            print(f"[디버그] reverse_formula: encoded={encoded_value}, formula='{formula}', UI_VALUE={ui_value}")
        return str(ui_value)
    except Exception as e:
        if is_debug:
            print(f"[디버그] reverse_formula 에러: encoded={encoded_value}, formula='{formula}', 에러={e}")
        return str(encoded_value)

def generate_translated_tree(xml_tree, param_dict, mode="once"):
    """
    XML 트리를 변환합니다.

    mode:
    - 'once'    : 공식 1회 적용
    - 'twice'   : 공식 2회 중첩 적용
    - 'reverse' : 공식 역방향 적용
    """
    if is_debug:
        print(f"[디버그] generate_translated_tree mode = {mode}")
    new_tree = copy.deepcopy(xml_tree)
    cmdata = new_tree.find(".//{*}cmData")

    for mo in cmdata.findall("{*}managedObject"):
        mo_class = mo.attrib.get("class")
        mo_class = mo_class.split(':')[1] if ':' in mo_class else mo_class

        # 일반 파라미터 처리
        for p in mo.findall("{*}p"):
            param_name = p.attrib.get("name")
            if param_name is None:
                continue
            key = (mo_class, param_name)
            if key in param_dict:
                entry = param_dict[key]
                formula = entry.get("formula")
                default_value = entry.get("default")
                value = (p.text or "").strip()

                if not value:
                    continue

                try:
                    if mode == "once":
                        new_value = apply_formula_once(value, formula)
                    elif mode == "twice":
                        new_value = apply_formula_twice(value, formula)
                    elif mode == "reverse":
                        new_value = reverse_formula(value, formula)
                    else:
                        if is_debug:
                            print(f"[디버그] 지원되지 않는 mode: {mode}")
                        new_value = value  # fallback

                except Exception as e:
                    if is_debug:
                        print(f"[디버그] 공식 실패, 기본값 사용: {mo_class}::{param_name} = {default_value} (에러: {e})")
                    new_value = default_value or value

                p.text = new_value

        # 리스트 내부 파라미터 처리
        for lst in mo.findall("{*}list"):
            for item in lst.findall(".//{*}item"):
                for p in item.findall("./{*}p"):
                    param_name = p.attrib.get("name")
                    if param_name is None:
                        continue
                    key = (mo_class, param_name)
                    if key in param_dict:
                        entry = param_dict[key]
                        formula = entry.get("formula")
                        default_value = entry.get("default")
                        value = (p.text or "").strip()

                        if not value:
                            continue

                        try:
                            if mode == "once":
                                new_value = apply_formula_once(value, formula)
                            elif mode == "twice":
                                new_value = apply_formula_twice(value, formula)
                            elif mode == "reverse":
                                new_value = reverse_formula(value, formula)
                            else:
                                new_value = value  # fallback

                        except Exception as e:
                            if is_debug:
                                print(f"[디버그] 공식 실패 (list 내): {mo_class}::{param_name} = {default_value} (에러: {e})")
                            new_value = default_value or value

                        p.text = new_value

    return new_tree


def strip_header_and_namespace(xml_str: str) -> str:
    # <?xml ... ?> 제거
    xml_str = re.sub(r'<\?xml[^>]+\?>\s*', '', xml_str, count=1)
    # <raml ...> 제거
    xml_str = re.sub(r'<raml[^>]*>\s*', '', xml_str, count=1)
    return xml_str

def warn_missing_required_params(xml_tree, mo_param_dict):
    """
    필수 파라미터 누락 여부를 검사하여 경고를 출력합니다.
    - xml_tree: ElementTree 객체
    - mo_param_dict: MO 구조 dict
    """
    cmdata = xml_tree.find(".//{*}cmData")
    if not cmdata:
        return []

    warnings = []

    for mo in cmdata.findall("{*}managedObject"):
        mo_class = mo.attrib.get("class", "").split(":")[-1]
        dist_name = mo.attrib.get("distName", "")
        mo_info = mo_param_dict.get(mo_class)
        if not mo_info:
            continue

        defined_params = mo_info.get("params", {})
        required_keys = {k for k, v in defined_params.items() if v.get("required")}

        existing_keys = {p.attrib.get("name") for p in mo.findall("{*}p")}
        missing_keys = required_keys - existing_keys

        ### 마이클님께 물어볼것
        # for key in sorted(missing_keys):
        #    warnings.append(f"[경고] [{mo_class}] {dist_name} → 필수 파라미터 '{key}' 누락")

    return warnings

def generate_cli_script_from_xml(xml_path: str, output_path: str):
    tree = ET.parse(xml_path)
    root = tree.getroot()
    cmdata = root.find(".//{*}cmData")
    if cmdata is None:
        raise ValueError("cmData가 없음")

    commands = []
    last_path = []

    mos = sorted(cmdata.findall("{*}managedObject"), key=lambda mo: mo.attrib.get("distName", ""))

    for mo in mos:
        distname = mo.attrib.get("distName")
        if not distname:
            continue

        path = distname.split("/")
        common = 0
        for i in range(min(len(path), len(last_path))):
            if path[i] == last_path[i]:
                common += 1
            else:
                break

        for _ in range(len(last_path) - common):
            commands.append("exit")

        for part in path[common:]:
            if "-" in part:
                cls, id = part.split("-", 1)
                if cls != "MRBTS":
                    commands.append(f"{cls} {id}")

        for p in mo.findall("{*}p"):
            key = p.attrib.get("name")
            value = (p.text or "").strip()
            if " " in value:
                value = f'"{value}"'
            commands.append(f"{key} {value}")

        for lst in mo.findall("{*}list"):
            list_name = lst.attrib.get("name")
            items = lst.findall("{*}item")
            for idx, item in enumerate(items, start=1):
                for p in item.findall("{*}p"):
                    key = p.attrib.get("name")
                    value = (p.text or "").strip()
                    if " " in value:
                        value = f'"{value}"'
                    commands.append(f"list {list_name} {idx} {key} {value}")

        last_path = path

    for _ in range(len(last_path) - 1):
        commands.append("exit")

    with open(output_path, "w", encoding="utf-8") as f:
        for cmd in commands:
            f.write(cmd + "\n")

def generate_cli_script_from_xml_string(xml_str: str) -> str:
    try:
        root = ET.fromstring(xml_str)
    except ET.ParseError as e:
        raise ValueError(f"XML 파싱 실패: {e}")

    cmdata = root.find(".//{*}cmData")
    if cmdata is None:
        raise ValueError("cmData가 없음")

    commands = []
    last_path = []
    mos = sorted(cmdata.findall("{*}managedObject"), key=lambda mo: mo.attrib.get("distName", ""))

    for mo in mos:
        distname = mo.attrib.get("distName")
        if not distname:
            continue

        path = distname.split("/")

        # 공통 prefix 계산
        common = 0
        for i in range(min(len(path), len(last_path))):
            if path[i] == last_path[i]:
                common += 1
            else:
                break

        for _ in range(len(last_path) - common):
            commands.append("exit")

        for part in path[common:]:
            if "-" in part:
                cls, id = part.split("-", 1)
                if cls != "MRBTS":
                    commands.append(f"{cls} {id}")

        for p in mo.findall("{*}p"):
            key = p.attrib.get("name")
            value = (p.text or "").strip()
            if " " in value:
                value = f'"{value}"'
            commands.append(f"{key} {value}")

        for lst in mo.findall("{*}list"):
            list_name = lst.attrib.get("name")
            items = lst.findall("{*}item")
            for idx, item in enumerate(items, start=1):
                for p in item.findall("{*}p"):
                    key = p.attrib.get("name")
                    value = (p.text or "").strip()
                    if " " in value:
                        value = f'"{value}"'
                    commands.append(f"list {list_name} {idx} {key} {value}")

        last_path = path

    for _ in range(len(last_path) - 1):
        commands.append("exit")

    return "\n".join(commands)
