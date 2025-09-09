import os
from copy import deepcopy
from cli.settings import is_debug
from cli.common.util.server_utils import load_from_server

def apply_class_based_mapping(cli_text, xml_tree):
    """
    CLI 텍스트 내의 <MO_CLASS> 000 패턴만 XML 트리에서 찾아 실제 distName에서 ID 추출 후 치환한다.
    구조 유지: 'LNCEL 000' → 'LNCEL 22109' (distName은 안 쓰고 ID만 바꿈)
    """
    lines = cli_text.splitlines()
    result_lines = []

    for i, line in enumerate(lines, 1):
        tokens = line.strip().split()

        # 치환 조건: "<MO_CLASS> 000"
        if len(tokens) == 2 and tokens[1] == "000" and tokens[0].isupper():
            mo_class = tokens[0]
            distname = find_distname_by_class(mo_class, xml_tree)

            if distname:
                # distname에서 마지막 ID 추출: MRBTS-.../LNCEL-22109 → 22109
                mo_id = distname.split("/")[-1].split("-")[-1]
                new_line = f"{mo_class} {mo_id}"
                result_lines.append(" " * (len(line) - len(line.lstrip())) + new_line)
                if is_debug:
                    print(f"[디버그] 라인 {i}: '{line.strip()}' → '{new_line}' (ID만 치환)")
            else:
                result_lines.append(line)
                if is_debug:
                    print(f"[디버그] 라인 {i}: '{line.strip()}' → 매핑 실패 → 그대로 유지")
        else:
            result_lines.append(line)

    return "\n".join(result_lines)


def find_distname_by_class(mo_class, xml_tree):
    """
    XML 트리에서 주어진 MO class (예: LNCEL)에 해당하는 managedObject의 distName을 찾는다.
    class 속성은 네임스페이스(:)가 포함될 수 있음.
    """
    root = xml_tree.getroot()
    found = []

    for mo in root.iter("managedObject"):
        mo_class_attr = mo.attrib.get("class")
        dist = mo.attrib.get("distName")

        # 네임스페이스 제거: com.nokia.srbts.eqm:ANTL → ANTL
        mo_class_trimmed = mo_class_attr.split(":")[-1] if mo_class_attr else None

        if is_debug:
            print(f"mo_class =  {mo_class}")
            print(f"mo_class_attr =  {mo_class_attr}")

        if mo_class_trimmed == mo_class:
            found.append(dist)
            if is_debug:
                print(f"[디버그] 매칭된 MO 발견 → class={mo_class_attr}, distName={dist}")

    if not found:
        if is_debug:
            print(f"[디버그] find_distname_by_class: '{mo_class}'에 해당하는 MO를 XML에서 찾지 못함")
        return None

    return found[0]

def load_cli_template_as_rule(filepath: str) -> dict:
    result = {}
    current_mo = None

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if line.lower() == "exit-all":
                current_mo = None
                continue

            tokens = line.split(maxsplit=1)
            if len(tokens) != 2:
                continue

            key, val = tokens

            if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]

            if key.isupper() and val.isdigit():  # MO 선언부
                current_mo = key
                if current_mo not in result:
                    result[current_mo] = {}
            elif current_mo:
                result[current_mo][key] = {"value": val}

    return result


def load_cablink_blocks(file_path, cablink_ids):
    """
    서버에서 CABLINK 템플릿 파일을 로드하여,
    주어진 CABLINK ID 별로 텍스트 블록을 분리하여 반환한다.
    각 블록은 라인 단위 리스트로 구성됨.
    """

    filename_only = os.path.basename(file_path)

    try:
        cli_text = load_from_server(filename_only, filetype="text", purpose="cablink")
    except Exception as e:
        raise ValueError(f"[오류] CABLINK 템플릿 로드 실패: {e}")

    blocks = {}
    for cid in cablink_ids:
        marker = f"### CABLINK_{cid} ###"
        start = cli_text.find(marker)
        if start == -1:
            continue
        end = cli_text.find("### CABLINK_", start + 1)
        if end == -1:
            block_text = cli_text[start:]
        else:
            block_text = cli_text[start:end]
        
        blocks[cid] = [line.rstrip() for line in block_text.strip().splitlines()]

    return blocks


def load_prod_code_maps():
    prod_dict = {}
    rmod_dict = {}

    try:
        prod_data = load_from_server("PRODMAPTBL.json", filetype="json", purpose="prodmap")
        prod_dict = prod_data.get("PRODMAPTBL", {}).get("value", {})
    except Exception:
        pass

    try:
        rmod_data = load_from_server("RMODPRODMAPTBL.json", filetype="json", purpose="prodmap")
        rmod_dict = rmod_data.get("RMODPRODMAPTBL", {}).get("value", {})
    except Exception:
        pass

    # 병합
    return {**prod_dict, **rmod_dict}