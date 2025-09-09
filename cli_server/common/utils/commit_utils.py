import os
import json
import re
import copy

def load_param_dict(data_dir):
    param_dict_path = os.path.join(data_dir, "param_dict.json")
    if not os.path.exists(param_dict_path):
        return {}
    with open(param_dict_path, "r", encoding="utf-8") as f:
        raw_dict = json.load(f)
    return {tuple(k.split("::")): v for k, v in raw_dict.items()}

def apply_formula_once(original_value, formula):
    try:
        eval_globals = {"__builtins__": {}}
        eval_locals = {"UI_VALUE": float(original_value)}
        result = eval(formula, eval_globals, eval_locals)
        #int_result = int(round(result))

        print(f"[디버그] apply_formula_once: original={original_value}, formula='{formula}', result={result}")
        return str(result)
    except Exception as e:
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
        #int_result = int(round(final_result))

        print(f"[디버그] apply_formula_twice: original={original_value}, formula='{formula}', result={final_result}")
        return str(final_result)
    except Exception as e:
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

        int_result = int(round(ui_value))
        print(f"[디버그] reverse_formula: encoded={encoded_value}, formula='{formula}', UI_VALUE={int_result}")
        return str(int_result)
    except Exception as e:
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
    print(f"[디버그] generate_translated_tree mode = {mode}")
    new_tree = copy.deepcopy(xml_tree)
    cmdata = new_tree.find(".//{*}cmData")

    for mo in cmdata.findall("{*}managedObject"):
        mo_class = mo.attrib.get("class")
        for p in mo.findall("{*}p"):
            param_name = p.attrib.get("name")
            if param_name is None:
                continue
            key = (mo_class, param_name)
            if key in param_dict:
                formula = param_dict[key]
                value = (p.text or "").strip()
                if not value:
                    continue

                if mode == "once":
                    new_value = apply_formula_once(value, formula)
                elif mode == "twice":
                    new_value = apply_formula_twice(value, formula)
                elif mode == "reverse":
                    new_value = reverse_formula(value, formula)
                else:
                    print(f"[디버그] 지원되지 않는 mode: {mode}")
                    new_value = value  # fallback

                #print(f"[디버그] 변환 적용: {mo_class}::{param_name} = {value} -> {new_value}")
                p.text = new_value

    return new_tree

