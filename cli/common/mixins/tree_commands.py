import argparse
import os
import re
import shlex
from cli.common.util.commit_utils import load_ru_dict
from xml.etree import ElementTree as ET
from cli.settings import is_debug
from cli.core.config.ru_template_map import ru_template_map
from cli.core.config.nr_cell_map import resolve_nrcell_template_key
from cli.core.config.nr_cell_grp_map import resolve_nrcell_grp_template_key

class TreeCommandMixin:
    def _build_prompt(self):
        if not self.prompt_stack:
            return f"config/init-cell({self.mo_version}, {self.rat_type}) > "
        return " > ".join(self.prompt_stack) + " > "
    
    def precmd(self, statement):
        self._original_line = statement.raw
        return super().precmd(statement)

    def default(self, line):
        orig_line = getattr(self, "_original_line", line)
        if is_debug:
            print("orig_line : ", orig_line)
            
        if orig_line.strip().startswith(("exec_script", "set_cfg_tmpl", "auto_config")):
            # run-script로 오염된 상황 → 현재 line 유지
            line = self.last_script_line
        else:
            # 정상적인 경우 → original_line을 신뢰
            line = orig_line.strip()
        tokens = shlex.split(line)
        if is_debug:
            print("tokens : ",tokens)
        if not tokens:
            self.perror("빈 명령입니다.")
            return

        if tokens[0].lower() == "list":
            if len(tokens) != 5:
                self.perror("사용법: list <listName> <index> <key> <value>")
                return
            _, list_name, index, key, value = tokens
            self._set_list_param(list_name, index, {key: value})
            return

        if len(tokens) == 2 and (tokens[0].replace("_", "").isupper() or tokens[0] == "tgt-bts"):
            mo_name, mo_id = tokens
            if mo_name == "tgt-bts":
                self._enter_or_create_mo("MRBTS", mo_id)
            else:
                self._enter_or_create_mo(mo_name, mo_id)
            return

        if len(tokens) == 2:
            key, value = tokens
            self._set_param(key, value)
            return

        self.perror(f"인식할 수 없는 명령입니다: '{line}'")

    def _enter_or_create_mo(self, mo_class: str, mo_id: str):
        # 최초 MRBTS 처리
        if not self.bts_id:
            if mo_class == "MRBTS":
                self.bts_id = mo_id
                self.match_tail = f"MRBTS-{mo_id}"
                self.prompt_stack = [f"MRBTS({mo_id})"]
            else:
                self.perror("먼저 MRBTS <ID>를 설정해주세요.")
                return
        else:
            if not self.prompt_stack:
                self.perror("내부 오류: 현재 위치한 MO 정보가 없습니다.")
                return

            parent_mo = self.mo_class
            if parent_mo not in self.mo_param_dict:
                self.perror(f"[오류] '{parent_mo}'는 사전에 정의된 MO가 아닙니다.")
                return

            children = self.mo_param_dict[parent_mo].get("children", [])
            if mo_class not in children:
                self.perror(f"[오류] '{parent_mo}' 아래에는 '{mo_class}'를 생성할 수 없습니다.")
                return

            # ID 치환 (000 → bts_id)
            if mo_id == "000" and self.bts_id and mo_class in {"LNBTS", "NRBTS"}:
                self.poutput(f"[INFO] '{mo_class} 000' → '{mo_class} {self.bts_id}' 으로 치환됨")
                mo_id = self.bts_id

            # param의 range로부터 ID 유효성 검사
            mo_id_param = mo_class.lower() + "Id"
            param_info = self.mo_param_dict.get(mo_class, {}).get("params", {}).get(mo_id_param)

            ## TOPP의 임시 id부여를 위해서
            if mo_class != "TOPP" and param_info and "range" in param_info and param_info["range"]:
                match = re.match(r"^(\d+)\.\.\.(\d+), step (\d+)$", param_info["range"])
                if match:
                    min_val, max_val, step = map(int, match.groups())
                    if is_debug:
                        print(f"[디버그] ID 범위 검사 진입: {mo_class}.{mo_id_param} = {mo_id}, 허용 범위 = {min_val}~{max_val}, step {step}")
                    try:
                        id_val = int(mo_id)
                        if id_val < min_val or id_val > max_val or (id_val - min_val) % step != 0:
                            self.perror(f"[오류] '{mo_class}'의 ID는 {min_val}~{max_val} 범위이며 step {step}이어야 합니다.")
                            return
                    except ValueError:
                        self.perror(f"[오류] '{mo_class}'의 ID '{mo_id}'는 숫자가 아닙니다.")
                        return

            self.match_tail += f"/{mo_class}-{mo_id}"
            self.prompt_stack.append(f"{mo_class.lower()}({mo_id})")

        # MO 존재 여부 확인 후 생성 또는 이동
        cmdata = self.xml_tree.find(".//{*}cmData")
        found = any(
            mo.attrib.get("distName") == self.match_tail
            for mo in cmdata.findall("{*}managedObject")
        )

        if not found:
            self._create_managed_object(mo_class, mo_id)
        else:
            self._move_to_managed_object(mo_class)


    def _validate_mo_create_preconditions(self, mo_class: str):
        """
        특정 MO 생성 전에 필요한 전제 조건들을 검사한다.
        조건이 만족되지 않으면 ValueError 예외를 발생시킨다.
        """
        if self.du_type == "du10" and self.rat_type.upper() == "4G":
            if mo_class == "ETHLK" and not hasattr(self, "last_trmod_id"):
                raise ValueError("ETHLK 생성 실패: 참조할 TRMOD ID가 설정되지 않았습니다. 먼저 TRMOD-*를 생성하세요.")

    def _create_managed_object(self, mo_class: str, mo_id: str):
        try:
            self._validate_mo_create_preconditions(mo_class)
        except ValueError as e:
            self.perror(f"[오류] {e}")
            return

        cmdata = self.xml_tree.find(".//{*}cmData")

        # class value
        if mo_class == "MRBTS":
            class_value = "com.nokia.srbts:MRBTS"
        else:
            path_parts = self.match_tail.split("/")
            branch = path_parts[1].split("-")[0].lower() if len(path_parts) >= 2 else "unknown"
            if self.rat_type == "4G" and branch == "lnbts":
                class_value = f"NOKLTE:{mo_class}"
            else:
                class_value = f"com.nokia.srbts.{branch}:{mo_class}"

        # === [추가] 5G + ru_type=APHA → ASIRMOD으로 클래스 치환 ===
        actual_mo_class = mo_class
        if mo_class == "RMOD" and self.rat_type.upper() == "5G" and getattr(self, "ru_type", None) == "APHA":
            actual_mo_class = "ASIRMOD"

        ET.SubElement(cmdata, "managedObject", {
            "class": class_value.replace(f":{mo_class}", f":{actual_mo_class}"),
            "distName": self.match_tail.replace(f"/{mo_class}-", f"/{actual_mo_class}-"),
            "version": self._resolve_version(mo_class),
            "operation": "create"
        })

        self.mo_class = mo_class 
        self.prompt = self._build_prompt().replace(mo_class.lower(), actual_mo_class.lower())
        if is_debug:
            print(f"mo 생성됨 : {actual_mo_class}")
        self.user_inputs.append(("MO-CREATE", self.match_tail.replace(f"/{mo_class}-", f"/{actual_mo_class}-")))

        self._apply_rulebook_param(actual_mo_class, mo_id)

        if mo_class in ("RMOD", "ASIRMOD") and hasattr(self, "ru_type"):
            try:
                ru_dict = load_ru_dict(self, self.rat_type)
                if self.ru_type in ru_dict:
                    self._set_param("prodCodePlanned", ru_dict[self.ru_type]["CODE"])
                self.last_rmod_id = mo_id

                if self.rat_type == "5G":
                    self.last_rmod_id = mo_id
                    self._append_rmod_to_sync2_target_dnlist(mo_class, mo_id)

                # === [복구] 기존 RU 템플릿 처리 블록 ===
                if is_debug:
                    print("self.ru_type = ", self.ru_type)

                if self.ru_type == "FXCA" and getattr(self, "sector_3", False):
                    if is_debug:
                        print("3 sector activated")
                    template_key = ru_template_map.get("FXCA2")
                else:
                    if is_debug:
                        print("3 sector deactivated")
                    if self.rat_type.upper() == "4G":
                        template_key = ru_template_map.get(self.ru_type)
                    elif self.rat_type.upper() == "5G":
                        template_key = ru_template_map.get(self.cell_type)

                if not template_key:
                    self.perror(f"[경고] RU 타입 '{self.ru_type}'에 대한 템플릿 매핑이 존재하지 않습니다.")
                    return

                script_name = f"{template_key}.cli"
                if self.rat_type == "4G":
                    self.do_exec_script(f"antl_templates/{script_name}")
                elif self.rat_type == "5G":
                    self.do_exec_script(f"phyant_templates/{script_name}")

            except Exception as e:
                self.perror(f"[오류] : {e}")

        # ===== [신규] NRCELL 생성 시 RU별 템플릿 자동 실행 =====
        if mo_class == "NRCELL":
            try:
                # NRCELL은 5G에서만 의미가 있으므로 RAT 확인(강제 차단은 안 함)
                ru_type = getattr(self, "cell_type", None)

                nrcell_tmpl_key = resolve_nrcell_template_key(ru_type)
                if not nrcell_tmpl_key:
                    if is_debug:
                        print("[NRCELL] 매핑된 템플릿 키가 없어 실행 생략")
                    return

                script_name = f"{nrcell_tmpl_key}.cli"
                # NRCELL 템플릿 전용 디렉터리
                self.do_exec_script(f"nrcell_templates/{script_name}")

                if is_debug:
                    print(f"[NRCELL] 템플릿 실행: nrcell_templates/{script_name} (ru_type={ru_type})")

            except Exception as e:
                self.perror(f"[오류][NRCELL 템플릿] : {e}")

        # ===== [신규] NRCELL 생성 시 RU별 템플릿 자동 실행 =====
        if mo_class == "NRCELLGRP":
            try:
                # NRCELL은 5G에서만 의미가 있으므로 RAT 확인(강제 차단은 안 함)
                ru_type = getattr(self, "cell_type", None)
                
                nrcell_grp_tmpl_key = resolve_nrcell_grp_template_key(ru_type)
                if not nrcell_grp_tmpl_key:
                    if is_debug:
                        print("[NRCELLGRP] 매핑된 템플릿 키가 없어 실행 생략")
                    return

                script_name = f"{nrcell_grp_tmpl_key}.cli"
                # NRCELL 템플릿 전용 디렉터리
                self.do_exec_script(f"nrcell_grp_templates/{script_name}")

                if is_debug:
                    print(f"[NRCELLGRP] 템플릿 실행: nrcell_grp_templates/{script_name} (ru_type={ru_type})")

            except Exception as e:
                self.perror(f"[오류][NRCELLGRP 템플릿] : {e}")

        # TRMOD / ETHLK (기존 유지)
        if mo_class == "TRMOD":
            print("TRMOD 세팅")
            self.last_trmod_id = mo_id
            if is_debug:
                self.poutput(f"[DEBUG] 현재 작업 대상 TRMOD: {mo_id}")

        if mo_class == "ETHLK":
            if self.du_type.upper() == "DU10" and self.rat_type.upper() == "4G":
                trmod_dist = f"MRBTS-{self.bts_id}/EQM-1/APEQM-1/CABINET-1/TRMOD-{self.last_trmod_id}"
                self._set_param("modDN", trmod_dist)
            elif self.du_type.upper() == "DU20":
                smod_dist = f"MRBTS-{self.bts_id}/EQM-1/APEQM-1/CABINET-1/SMOD-1"
                self._set_param("modDN", smod_dist)

        # NRCELL 후처리 (5G)
        if mo_class == "NRCELL" and self.rat_type == "5G":
            try:
                self._nrcell_post_create_dedicated_groups(mo_id)
            except Exception as e:
                if is_debug:
                    self.poutput(f"[DEBUG] NRCELL 후처리 예외: {e}")


    # =========================
    # 헬퍼: 리스트/그룹 유틸
    # =========================
    def _next_index(self, dn: str, list_name: str) -> int:
        cmdata = self.xml_tree.find(".//{*}cmData")
        mo = cmdata.find(f".//{{*}}managedObject[@distName='{dn}']")
        if mo is None:
            return 1
        lst = mo.find(f"./{{*}}list[@name='{list_name}']")
        if lst is None:
            return 1
        item_cnt = len(lst.findall("./{*}item"))
        if item_cnt > 0:
            return item_cnt + 1
        return len(lst.findall("./{*}p")) + 1

    def _list_has_p_value(self, dn: str, list_name: str, value: str) -> bool:
        cmdata = self.xml_tree.find(".//{*}cmData")
        mo = cmdata.find(f".//{{*}}managedObject[@distName='{dn}']")
        if mo is None:
            return False
        lst = mo.find(f"./{{*}}list[@name='{list_name}']")
        if lst is None:
            return False
        for p in lst.findall("./{*}p"):
            if (p.text or "").strip() == str(value):
                return True
        return False

    def _lbps_item_exists(self, dn: str, list_name: str, nr_cell_id: str) -> bool:
        cmdata = self.xml_tree.find(".//{*}cmData")
        mo = cmdata.find(f".//{{*}}managedObject[@distName='{dn}']")
        if mo is None:
            return False
        lst = mo.find(f"./{{*}}list[@name='{list_name}']")
        if lst is None:
            return False
        for item in lst.findall("./{*}item"):
            for p in item.findall("./{*}p"):
                if p.get("name") == "nrCellId" and (p.text or "").strip() == str(nr_cell_id):
                    return True
        return False

    def _pick_or_create_group_id(self, nrbts_prefix: str, mo_name: str, preferred_id: str = "0") -> str:
        """존재하면 첫 번째 그룹 사용, 없으면 preferred_id(기본 0) 생성 후 사용"""
        cmdata = self.xml_tree.find(".//{*}cmData")
        found = []
        for mo in cmdata.findall(".//{*}managedObject"):
            dn = mo.get("distName", "")
            if nrbts_prefix and dn.startswith(f"{nrbts_prefix}/{mo_name}-"):
                try:
                    gid = dn.split(f"{mo_name}-", 1)[1]
                    found.append(gid)
                except Exception:
                    pass
        if found:
            return found[0]
        # 없으면 생성
        self._enter_or_create_mo(mo_name, preferred_id)
        self.onecmd("exit")
        return preferred_id

    # =========================
    # 헬퍼: RMOD 후처리 (5G) - SYNC-2.targetDNList 업데이트
    # =========================
    def _append_rmod_to_sync2_target_dnlist(self, mo_class, mo_id: str):
        rmod_dn  = f"MRBTS-{self.bts_id}/EQM-1/APEQM-1/{mo_class}-{mo_id}"
        sync2_dn = f"MRBTS-{self.bts_id}/MNL-1/MNLENT-1/SYNC-2"

        # 다음 index
        next_idx = self._next_index(sync2_dn, "targetDNList")

        # 현재 위치 저장 및 루트로 상승(RMOD -> APEQM -> EQM -> MRBTS)
        prev_tail = self.match_tail
        self.onecmd("exit"); self.onecmd("exit"); self.onecmd("exit")

        # SYNC-2 진입/생성 후 리스트 추가 (onecmd 대신 내부 setter)
        self._enter_or_create_mo("MNL", "1")
        self._enter_or_create_mo("MNLENT", "1")
        self._enter_or_create_mo("SYNC", "2")
        self._set_list_param("targetDNList", str(next_idx), {"val": rmod_dn})

        # SYNC -> MNLENT -> MNL -> MRBTS
        self.onecmd("exit"); self.onecmd("exit"); self.onecmd("exit")

        # 원복
        for seg in prev_tail.split("/")[1:]:
            cls, _id = seg.split("-")
            self._enter_or_create_mo(cls, _id)

    # =========================
    # 헬퍼: NRCELL 후처리 (5G) - 그룹 선택/생성 + 리스트 갱신
    # =========================
    def _nrcell_post_create_dedicated_groups(self, mo_id: str):
        """
        NRCELL 생성 후, 기존 그룹에 append 하지 않고
        RMOD ID를 그룹 ID로 갖는 NRCELLGRP/NRPGRP를 새로 만들고 해당 셀만 등록 +
        NRDU-1.refNrCellGroup에 gid 추가.
        """
        print("nrcell 추가 ", mo_id)
        gid = getattr(self, "last_rmod_id", None)
        if not gid:
            self.perror("[오류] RMOD가 먼저 생성되어야 합니다. last_rmod_id가 없습니다.")
            return
        gid = str(gid)

        parts = self.match_tail.split("/")
        nrbts_prefix = "/".join(parts[:2]) if len(parts) >= 2 else None
        if not nrbts_prefix:
            self.perror("[오류] NRBTS 컨텍스트를 해석할 수 없습니다.")
            return

        # NRCELL → NRBTS
        self.onecmd("exit")

        # ===== NRCELLGRP-gid =====
        if self.mode == "bts" :
            self._enter_or_create_mo("NRCELLGRP", 0)
        elif self.mode == "cell" :
            self._enter_or_create_mo("NRCELLGRP", gid)
        # 필요 시 유지/제거: nrCellGrpId 세팅
        self._set_list_param("nrCellList", "1", {"val": str(mo_id)})
        self.onecmd("exit")

        # ===== NRPGRP-gid =====
        nrpgrp_dn = f"{nrbts_prefix}/NRPGRP-{gid}"
        self._enter_or_create_mo("NRPGRP", gid)
        self._set_list_param("lbpsCellList", "1", {
            "lbpsCellSOOrder": "100",
            "lbpsUseExtConfig": "false",
            "nrCellId": str(mo_id),
        })
        self.onecmd("exit")

        # ===== NRDU-1.refNrCellGroup에 gid 추가 =====
        nrdu_dn = f"{nrbts_prefix}/NRDU-1"
        cmdata = self.xml_tree.find(".//{*}cmData")
        nrdu_elem = cmdata.find(f".//{{*}}managedObject[@distName='{nrdu_dn}']")
        if nrdu_elem is not None:
            # 중복이면 스킵
            if not self._list_has_p_value(nrdu_dn, "refNrCellGroup", gid):
                next_idx = self._next_index(nrdu_dn, "refNrCellGroup")
                self._enter_or_create_mo("NRDU", "1")
                if self.mode == "bts" :
                    self._set_list_param("refNrCellGroup", str(next_idx), {"val": 0})
                elif self.mode == "cell" :
                    self._set_list_param("refNrCellGroup", str(next_idx), {"val": gid})
                self.onecmd("exit")
            else:
                if is_debug:
                    self.poutput(f"[DEBUG] NRDU-1.refNrCellGroup에 gid={gid} 이미 존재 → 스킵")
        else:
            self.perror(f"[경고] {nrdu_dn} 가 존재하지 않아 refNrCellGroup 갱신을 스킵합니다.")

        # 복귀: NRCELL
        self._enter_or_create_mo("NRCELL", mo_id)


    def _move_to_managed_object(self, mo_class: str):
        self.mo_class = mo_class
        self.prompt = self._build_prompt()
        if is_debug:
            print(f"mo 이동 : {mo_class}")
    def _resolve_version(self, mo_class: str) -> str:
        base = self.mo_version.upper()  # 예: "24R2", "25R1"
        if mo_class == "MRBTS":
            return f"SBTS{base}FSM3_2402_100" if base == "24R2" else f"SBTS{base}FSM3_2502_100"
        else:
            return f"EQM{base}FSM3_2322_100" if base == "24R2" else f"EQM{base}FSM3_2522_100"

    ##PA생성
    def _set_param(self, key: str, value: str):
        #self.poutput(f"[DEBUG] key={key}, value={value}")
        if self.mo_class not in self.mo_param_dict:
            self.perror(f"[오류] 알 수 없는 MO: {self.mo_class}")
            return

        mo_info = self.mo_param_dict[self.mo_class]
        if "params" not in mo_info or key not in mo_info["params"]:
            self.perror(f"[오류] '{self.mo_class}'에는 파라미터 '{key}'를 설정할 수 없습니다.")
            return

        for mo in self.xml_tree.findall(".//{*}managedObject"):
            if mo.attrib.get("class", "").split(":")[-1] == self.mo_class and mo.attrib.get("distName", "").endswith(self.match_tail):
                for p in mo.findall("{*}p"):
                    if p.attrib.get("name") == key:
                        p.text = value
                        if is_debug:
                            self.poutput(f"[DEBUG] {key} 갱신: {value}")
                        self.user_inputs.append(("SET", self.match_tail, key, value))
                        return
                ET.SubElement(mo, "p", name=key).text = value
                if is_debug:
                    self.poutput(f"[DEBUG] {key} 추가됨: {value}")
                self.user_inputs.append(("SET", self.match_tail, key, value))
                return

        self.perror("현재 MO를 찾을 수 없습니다.")
    
    def _create_empty_xml(self):
        root = ET.Element("raml", {"version": "2.0"})
        cmdata = ET.SubElement(root, "cmData", {"type": "plan"})
        return ET.ElementTree(root)
    
    ##LIST
    def _set_list_param(self, list_name: str, index: str, param_dict: dict):

        if is_debug:
            self.poutput(f"[DEBUG] _set_list_param() 호출됨")
            self.poutput(f"[DEBUG] list_name: {list_name}")
            self.poutput(f"[DEBUG] index: {index}")
            self.poutput(f"[DEBUG] param_dict: {param_dict}")
            self.poutput(f"[DEBUG] mo_class: {self.mo_class}")
            self.poutput(f"[DEBUG] match_tail: {self.match_tail}")
            
        # 1. 리스트 이름 유효성 검사
        if self.mo_class not in self.mo_param_dict:
            self.perror(f"[오류] 알 수 없는 MO: {self.mo_class}")
            return

        mo_info = self.mo_param_dict[self.mo_class]
        if list_name not in mo_info["params"]:
            self.perror(f"[오류] '{self.mo_class}'에는 리스트 '{list_name}'를 설정할 수 없습니다.")
            return
        list_def = mo_info["params"][list_name]
        if list_def.get("type") != "list" or "children" not in list_def:
            self.perror(f"[오류] '{list_name}'는 리스트 파라미터가 아닙니다.")
            return

        # 2. 자식 파라미터 유효성 검사 (val 제외)
        for k in param_dict.keys():
            if k != "val" and k not in list_def["children"]:
                self.perror(f"[오류] 리스트 '{list_name}'에는 파라미터 '{k}'를 설정할 수 없습니다.")
                return

        # 3. XML 반영
        for mo in self.xml_tree.findall(".//{*}managedObject"):
            class_name = mo.attrib.get("class", "").split(":")[-1]
            dist_name = mo.attrib.get("distName", "")
            if class_name == self.mo_class and dist_name.endswith(self.match_tail):
                list_node = None
                for lst in mo.findall("{*}list"):
                    if lst.attrib.get("name") == list_name:
                        list_node = lst
                        break
                if list_node is None:
                    list_node = ET.SubElement(mo, "list", name=list_name)

                idx = int(index) - 1

                if "val" in param_dict:  # <p> 단일 항목 케이스
                    p_nodes = list_node.findall("{*}p")
                    while len(p_nodes) <= idx:
                        ET.SubElement(list_node, "p")
                        p_nodes = list_node.findall("{*}p")
                    p_node = p_nodes[idx]
                    p_node.attrib.clear()  # name 속성 제거
                    p_node.text = param_dict["val"]
                    self.user_inputs.append(("SET-LIST", self.match_tail, list_name, index, "val", param_dict["val"]))
                    return

                # <item><p name="...">...</p></item> 구조
                item_nodes = list_node.findall("{*}item")
                while len(item_nodes) <= idx:
                    ET.SubElement(list_node, "item")
                    item_nodes = list_node.findall("{*}item")
                item = item_nodes[idx]

                for k, v in param_dict.items():
                    updated = False
                    for p in item.findall("{*}p"):
                        if p.attrib.get("name") == k:
                            p.text = v
                            updated = True
                            break
                    if not updated:
                        ET.SubElement(item, "p", name=k).text = v
                    self.user_inputs.append(("SET-LIST", self.match_tail, list_name, index, k, v))

                if is_debug:
                    self.poutput(f"[DEBUG] 리스트 {list_name}[{index}] 수정됨")
                return

        self.perror("현재 MO를 찾을 수 없습니다.")

    def _apply_rulebook_param(self, mo_class: str, mo_id: str):
        if not hasattr(self, "rulebook_param_dict"):
            return

        if mo_class == "ANTL":
            return

        rulebook = self.rulebook_param_dict.get(mo_class)
        if is_debug:
            print("mo_class : ", mo_class)
        if not rulebook:
            return

        rule_data = None
        # 특수 처리: IoT LNCEL
        if mo_class == "LNCEL" and hasattr(self, "iot_lncel_id") and self.iot_lncel_id == mo_id:
            print("iot LNCEL 설정 진입")
            rule_data = rulebook.get("999")

        elif mo_class in {"SIB", "DRX", "SDRX"} and hasattr(self, "iot_lncel_id"):
            lnc_tag = f"LNCEL-{self.iot_lncel_id}"
            if self.match_tail and lnc_tag in self.match_tail:
                rule_data = rulebook.get("999")

        # 일반 MO에 대한 매핑 로직 (distName tail 기준 추가)
        if rule_data is None:
            match_key = f"{mo_class}-{mo_id}"
            if is_debug:
                print(f"[디버그] mo_class: {mo_class}, mo_id: {mo_id}, match_key: {match_key}")

            matched_keys = []
            for k in self.rulebook_param_dict:
                if k.endswith(match_key):
                    matched_keys.append(k)

            if is_debug:
                print(f"[디버그] matched_keys = {matched_keys}")

            if len(matched_keys) >= 2:
                if is_debug:
                    print(f"[디버그] self.match_tail = {self.match_tail}")
                replaced_key = self.normalize_root_id(self.match_tail)
                if is_debug:
                    print(f"[디버그] replaced_key = {replaced_key}")
                if replaced_key in self.rulebook_param_dict:
                    rule_data = self.rulebook_param_dict[replaced_key]
                elif match_key in self.rulebook_param_dict:
                    rule_data = self.rulebook_param_dict[match_key]
                else:
                    rule_data = None

                if is_debug:
                    print("rule_data dist = ", rule_data)
            else:
                rule_data = rulebook.get(mo_id) or rulebook.get("000") or rulebook.get("__default__")
                if is_debug:
                    print("rule_data mo = ", rule_data)

        # fallback: 첫 번째 index 사용
        if rule_data is None and rulebook:
            sorted_keys = sorted(rulebook.keys())
            if sorted_keys:
                rule_data = rulebook[sorted_keys[0]]
                if is_debug:
                    print(f"[디버그] fallback: {mo_class}-{mo_id} → {mo_class}-{sorted_keys[0]} (첫 번째 index 사용)")

        if not rule_data:
            if is_debug:
                print(f"[경고] 적용 가능한 룰 없음: {mo_class}-{mo_id}")
            return

        # 리스트 파라미터 처리
        for key, meta in rule_data.items():
            if meta.get("type") == "list":
                children_list = meta.get("children", [])
                if children_list and isinstance(children_list, list):
                    for idx, child in enumerate(children_list, start=1):
                        if isinstance(child, dict) and len(child) == 1 and "val" in child:
                            val = child["val"].get("value", "0")
                            val = self.replace_root_id(val)
                            self._set_list_param(key, index=str(idx), param_dict={"val": val})
                        else:
                            param_dict = {}
                            for k, v in child.items():
                                value = v.get("value", "0")
                                value = self.replace_root_id(value)
                                param_dict[k] = value
                            self._set_list_param(key, index=str(idx), param_dict=param_dict)
            else:
                value = meta.get("value", "0")
                value = self.replace_root_id(value)
                self._set_param(key, value)



        # for key, meta in rule_data.items():
        #     if meta.get("type") == "list":
        #         children_list = meta.get("children", [])
        #         if children_list and isinstance(children_list, list):
        #             first = children_list[0]

        #             # case: 단일 <p> 형태 (key == "val")
        #             if isinstance(first, dict) and len(first) == 1 and "val" in first:
        #                 val = first["val"].get("value", "0")
        #                 val = self.replace_root_id(val)
        #                 self._set_list_param(key, index="1", param_dict={"val": val})
        #             else:
        #                 param_dict = {}
        #                 for k, v in first.items():
        #                     value = v.get("value", "0")
        #                     value = self.replace_root_id(value)
        #                     param_dict[k] = value
        #                 self._set_list_param(key, index="1", param_dict=param_dict)
        #     else:
        #         value = meta.get("value", "0")
        #         value = self.replace_root_id(value)
        #         self._set_param(key, value)

    #치환
    def replace_root_id(self, value: str) -> str:
        if "MRBTS-000" in value:
            value = value.replace("MRBTS-000", f"MRBTS-{self.bts_id}")
        if "NRBTS-000" in value:
            value = value.replace("NRBTS-000", f"NRBTS-{self.bts_id}")
        if "LNBTS-000" in value:
            value = value.replace("LNBTS-000", f"LNBTS-{self.bts_id}")
        return value
    
    def normalize_root_id(self, value: str) -> str:
        if f"MRBTS-{self.bts_id}" in value:
            value = value.replace(f"MRBTS-{self.bts_id}", "MRBTS-000")
        if f"NRBTS-{self.bts_id}" in value:
            value = value.replace(f"NRBTS-{self.bts_id}", "NRBTS-000")
        if f"LNBTS-{self.bts_id}" in value:
            value = value.replace(f"LNBTS-{self.bts_id}", "LNBTS-000")
        return value


    ##NO
    def do_no_mo(self, arg):
        """
        현재 XML 트리에서 지정된 MO 및 하위 MO들을 제거합니다.
        - SCF 삭제 예약은 하지 않습니다.
        - 현재 프롬프트가 해당 MO 또는 하위일 경우 삭제 불가
        
        사용법: no-mo <MO_CLASS> <ID>
        예시: no-mo LNMME 1
        """
        tokens = shlex.split(arg.strip())
        if len(tokens) != 2:
            self.perror("사용법: no-mo <MO_CLASS> <ID>")
            return

        mo_class, mo_id = tokens
        target_key = f"{mo_class}-{mo_id}"

        if not self.bts_id:
            self.perror("BTS ID가 설정되지 않았습니다.")
            return

        # 현재 프롬프트 위치보다 아래인 경우 삭제 금지
        cur = self.cur_mo_dist or ""
        if target_key in cur:
            self.perror(f"현재 위치가 {target_key}의 하위이므로 삭제할 수 없습니다. 먼저 상위로 이동하세요.")
            return

        cmdata = self.xml_tree.find(".//{*}cmData")
        if cmdata is None:
            self.perror("cmData를 찾을 수 없습니다.")
            return

        delete_targets = []
        for mo in list(cmdata.findall("{*}managedObject")):
            dist = mo.attrib.get("distName", "")
            if f"/{target_key}" in dist or dist.endswith(target_key):
                delete_targets.append((mo, dist))

        if not delete_targets:
            self.perror(f"{target_key} 를 포함한 MO를 찾을 수 없습니다.")
            return

        for mo, dist in delete_targets:
            cmdata.remove(mo)
            self.poutput(f"[INFO] {dist} 제거됨 (트리에서 삭제됨)")


    def do_no_mo_scf(self, arg):
        """
        MO 객체를 삭제합니다.
        사용법: no-mo-scf <MO_CLASS> <ID>
        예시: no-mo-scf LNMME 1
        """
        tokens = shlex.split(arg.strip())
        if len(tokens) != 2:
            self.perror("사용법: no-mo <MO_CLASS> <ID>")
            return

        mo_class, mo_id = tokens

        if not self.bts_id:
            self.perror("BTS ID가 설정되지 않았습니다.")
            return

        cmdata = self.xml_tree.find(".//{*}cmData")
        found = False

        keyword = f"/{mo_class}-{mo_id}"
        for mo in list(cmdata.findall("{*}managedObject")):
            dist = mo.attrib.get("distName", "")
            if keyword in dist:
                cmdata.remove(mo)
                self._append_delete_operation(mo_class, dist)
                self.poutput(f"[INFO] {dist} 삭제 예약됨 (operation=delete)")
                found = True

        if not found:
            self.perror(f"{mo_class}-{mo_id} 를 포함한 MO를 찾을 수 없습니다.")

    def _append_delete_operation(self, mo_class: str, dist_name: str):
        """
        삭제 대상 MO를 delete operation 형태로 cmData에 추가
        """
        cmdata = self.xml_tree.find(".//{*}cmData")

        # branch 결정
        path_parts = dist_name.split("/")
        branch = path_parts[1].split("-")[0].lower() if len(path_parts) >= 2 else "unknown"
        if self.rat_type == "4G" and branch == "lnbts":
            class_value = f"NOKLTE:{mo_class}"
        else:
            class_value = f"com.nokia.srbts.{branch}:{mo_class}"

        ET.SubElement(cmdata, "managedObject", {
            "class": class_value,
            "distName": dist_name,
            "version": self._resolve_version(mo_class),
            "operation": "delete"
        })


    def do_no_pa(self, arg):
        """
        현재 MO에서 지정된 파라미터를 삭제합니다.
        사용법: no-pa <param>
        """
        import shlex
        tokens = shlex.split(arg.strip())

        if len(tokens) != 1:
            self.perror("사용법: no-pa <param>")
            return

        param_name = tokens[0]

        if not self.mo_class:
            self.perror("현재 위치한 MO가 없습니다.")
            return

        target_mo = None
        for mo in self.xml_tree.findall(".//{*}managedObject"):
            if mo.attrib.get("distName", "") == self.match_tail:
                target_mo = mo
                break

        if not target_mo:
            self.perror("현재 MO에 해당하는 XML 객체를 찾을 수 없습니다.")
            return

        found = False
        for p in target_mo.findall("{*}p"):
            if p.attrib.get("name") == param_name:
                target_mo.remove(p)
                found = True
                self.poutput(f"[INFO] '{param_name}' 파라미터가 삭제되었습니다.")
                break

        if not found:
            self.poutput(f"[INFO] '{param_name}' 파라미터는 현재 MO에 존재하지 않습니다.")

    def do_no_list(self, arg):
        """
        리스트 전체 삭제 또는 리스트 항목 내 파라미터 삭제를 수행합니다.
        
        사용법:
        - 리스트 전체 삭제:            no-list <listName>
        - 리스트 항목 파라미터 삭제:    no-list <listName><index> <param>
        - (신규) 인덱스 모를 때 일괄삭제: no-list <listName> <param>

        예시:
        - no-list srioConnectionList
        - no-list srioConnectionList0 mode
        - no-list srioConnectionList mode     # ← 모든 item에서 'mode' 파라미터 삭제
        """
        tokens = shlex.split(arg.strip())
        if not tokens:
            self.perror("사용법:\n  no-list <listName>\n  no-list <listName><index> <param>\n  no-list <listName> <param>")
            return

        target_mo = self._find_current_mo()
        if not target_mo:
            self.perror("현재 MO를 찾을 수 없습니다.")
            return

        # 1) 전체 리스트 삭제
        if len(tokens) == 1:
            list_name = tokens[0]
            for lst in target_mo.findall("{*}list"):
                if lst.attrib.get("name") == list_name:
                    target_mo.remove(lst)
                    self.poutput(f"[INFO] 리스트 '{list_name}' 전체가 삭제되었습니다.")
                    return
            self.poutput(f"[INFO] 리스트 '{list_name}'는 현재 MO에 존재하지 않습니다.")
            return

        # 2) 리스트 내 특정 파라미터 삭제 (두 가지 케이스)
        elif len(tokens) == 2:
            first, param_name = tokens

            import re
            match = re.match(r"^([a-zA-Z_]+)(\d+)$", first)

            if match:
                # 2-1) 기존 방식: <listName><index> <param>
                list_name, index = match.group(1), int(match.group(2))

                for lst in target_mo.findall("{*}list"):
                    if lst.attrib.get("name") == list_name:
                        items = lst.findall("{*}item")
                        if index >= len(items):
                            self.perror(f"리스트 '{list_name}'에 인덱스 {index} 항목이 없습니다.")
                            return
                        item = items[index]
                        for p in item.findall("{*}p"):
                            if p.attrib.get("name") == param_name:
                                item.remove(p)
                                self.poutput(f"[INFO] 리스트 '{list_name}[{index}]'에서 파라미터 '{param_name}' 삭제됨.")
                                return
                        self.poutput(f"[INFO] 리스트 '{list_name}[{index}]'에 '{param_name}' 파라미터가 존재하지 않습니다.")
                        return

                self.poutput(f"[INFO] 리스트 '{list_name}'는 현재 MO에 존재하지 않습니다.")
                return

            else:
                # 2-2) 신규 방식: <listName> <paramSpec>
                # - item 리스트: 모든 item에서 name=paramSpec(또는 name=value 매칭) 삭제
                # - direct-p 리스트: <p>에 name 있으면 name 매칭, 없으면 "값" 매칭
                list_name = first
                spec = param_name  # ex) "mode"  또는  "mode=eCpri10"  또는  (direct-p) "MRBTS-.../RMOD-8"

                key = None
                val = None
                if "=" in spec:
                    key, val = spec.split("=", 1)
                    key = key.strip()
                    val = val.strip()
                else:
                    key = spec.strip()

                total_items = 0
                deleted = 0
                direct_ps_count = 0
                direct_deleted = 0

                target_list = None
                for lst in target_mo.findall("{*}list"):
                    if lst.attrib.get("name") == list_name:
                        target_list = lst
                        break

                if target_list is None:
                    self.poutput(f"[INFO] 리스트 '{list_name}'는 현재 MO에 존재하지 않습니다.")
                    return

                # (A) <item> 기반 리스트 처리
                items = target_list.findall("{*}item")
                if items:
                    total_items = len(items)
                    for item in items:
                        for p in list(item.findall("{*}p")):
                            pname = p.attrib.get("name")
                            ptext = (p.text or "").strip()
                            if val is None:
                                # key만 있는 경우 → name 매칭으로 삭제
                                if pname == key:
                                    item.remove(p)
                                    deleted += 1
                            else:
                                # key=value 형태 → name, value 둘 다 매칭
                                if pname == key and ptext == val:
                                    item.remove(p)
                                    deleted += 1

                # (B) direct-<p> 리스트 처리 ( <list> 바로 아래에 <p>들 )
                direct_ps = target_list.findall("{*}p")
                if direct_ps:
                    direct_ps_count = len(direct_ps)
                    for p in list(direct_ps):
                        pname = p.attrib.get("name")  # 있을 수도, 없을 수도
                        ptext = (p.text or "").strip()

                        if pname:
                            # name 있는 direct-p
                            if val is None:
                                if pname == key:
                                    target_list.remove(p)
                                    direct_deleted += 1
                            else:
                                if pname == key and ptext == val:
                                    target_list.remove(p)
                                    direct_deleted += 1
                        else:
                            # name 없는 direct-p (값만 존재)
                            # key만 온 경우: 값 == key 인 항목 삭제
                            # key=value 온 경우: value쪽만 비교 (key는 무시)
                            if val is None:
                                if ptext == key:
                                    target_list.remove(p)
                                    direct_deleted += 1
                            else:
                                if ptext == val:
                                    target_list.remove(p)
                                    direct_deleted += 1

                # 결과 메시지
                if items or direct_ps:
                    msg_parts = []
                    if items:
                        msg_parts.append(f"item {total_items}개 중 {deleted}개 p 삭제")
                    if direct_ps:
                        msg_parts.append(f"direct-p {direct_ps_count}개 중 {direct_deleted}개 삭제")
                    if not msg_parts:
                        self.poutput(f"[INFO] 리스트 '{list_name}'에서 삭제된 항목이 없습니다.")
                    else:
                        self.poutput(f"[INFO] 리스트 '{list_name}': " + ", ".join(msg_parts))
                else:
                    self.poutput(f"[INFO] 리스트 '{list_name}'는 비어 있습니다.")
                return

    def _find_current_mo(self):
        """현재 match_tail 기준으로 XML에서 해당 MO를 반환"""
        if not self.mo_class or not self.match_tail:
            return None
        for mo in self.xml_tree.findall(".//{*}managedObject"):
            if mo.attrib.get("distName", "") == self.match_tail:
                return mo
        return None
    
    def do_add_auto_pa(self, arg):
        """
        현재 MO에 파라미터들을 자동으로 추가합니다.
        사용법: add-auto_pa [-r | -a]
        """

        if not self.mo_class:
            self.perror("현재 위치한 MO가 없습니다.")
            return

        if self.mo_class not in self.mo_param_dict:
            self.perror(f"[오류] MO '{self.mo_class}'에 대한 정보가 사전에 등록되어 있지 않습니다.")
            return

        args = shlex.split(arg)
        add_all = "-a" in args

        params = self.mo_param_dict[self.mo_class].get("params", {})
        if not params:
            self.poutput(f"[{self.mo_class}] 등록된 파라미터가 없습니다.")
            return

        # 현재 XML에서 해당 MO 객체 찾기
        for mo in self.xml_tree.findall(".//{*}managedObject"):
            dist = mo.attrib.get("distName", "")
            if dist == self.match_tail:
                target_mo = mo
                break

        if target_mo is None:
            self.perror("현재 MO에 해당하는 XML 객체를 찾을 수 없습니다.")
            return

        added_count = 0
        for key, info in params.items():
            if not add_all and not info.get("required", False):
                continue

            # 이미 존재하는지 확인
            if any(p.attrib.get("name") == key for p in target_mo.findall("{*}p")):
                continue

            value = info.get("default")
            if value is None or str(value).lower() == "null":
                value = f"TEMP_{key}"

            ET.SubElement(target_mo, "p", name=key).text = value
            added_count += 1
            if is_debug:
                self.poutput(f"[DEBUG] '{key}' 추가됨: {value}")

        self.poutput(f"[{self.mo_class}] 파라미터 자동 추가 완료: {added_count}개 추가됨.")

    def do_exit(self, arg):
        """
        현재 계층에서 한 단계 위로 이동합니다.
        """
        if is_debug:
            print("[디버그] do_exit() 진입")
            print(f"[디버그] match_tail repr: {repr(self.match_tail)}")
            print(f"[디버그] type(match_tail): {type(self.match_tail)}")

        if not self.match_tail or self.match_tail.strip() == "" or not self.prompt_stack:
            return True

        # 이전 상태 출력
        if is_debug :
            print(f"[디버그] 이전 match_tail: {self.match_tail}")
            print(f"[디버그] 이전 prompt_stack: {self.prompt_stack}")
            print(f"[디버그] 이전 mo_class: {self.mo_class}")

        # 프롬프트 스택이 1개 → 최상단
        if len(self.prompt_stack) == 1:
            answer = input("정말 initcli를 종료하시겠습니까? [yes/no]: ").strip().lower()
            if answer != "yes":
                self.poutput("종료를 취소했습니다.")
                return

            # 상태 저장
            #self._save_session_to_config()

            # 종료
            return True

        # 프롬프트 스택 pop
        self.prompt_stack.pop()

        # match_tail 재계산
        if self.match_tail:
            self.match_tail = "/".join(self.match_tail.split("/")[:-1])
        else:
            self.match_tail = None

        # mo_class 재설정
        if len(self.prompt_stack) > 0:
            top = self.prompt_stack[-1]
            mo_class_raw = top.split("(")[0].upper()

            # 예외 처리: cfg-bts는 실제로 MRBTS를 뜻함
            if mo_class_raw == "CFG-BTS":
                self.mo_class = "MRBTS"
            else:
                self.mo_class = mo_class_raw
        else:
            self.mo_class = None

        # 프롬프트 갱신
        self.prompt = self._build_prompt()

        # 이후 상태 출력
        if is_debug : 
            print(f"[디버그] 이후 match_tail: {self.match_tail}")
            print(f"[디버그] 이후 prompt_stack: {self.prompt_stack}")
            print(f"[디버그] 이후 mo_class: {self.mo_class}")
            print(f"[디버그] 이후 prompt: {self.prompt}")
            print(f"[확인] cmdloop 계속됨 여부: {len(self.prompt_stack) > 0}")

    def do_exit_all(self, arg):
        """
        현재 계층에서 MRBTS까지 반복적으로 exit를 수행합니다.
        사용법: exit-all
        """
        if is_debug:
            print(f"[exit-all] 현재 계층 깊이: {len(self.prompt_stack)}")
        while len(self.prompt_stack) > 1:
            self.onecmd("exit")

    def emptyline(self):
        # 아무 것도 하지 않음 → 그냥 프롬프트 유지
        pass

    

    def do_auto_config(self, arg: str):
        """
        RU 타입 기반 자동 MO 생성

        사용법:
            # [공통] RU 타입은 먼저 set-ru-type으로 설정되어 있어야 함

            [1] LNCEL 하위 구성 자동 생성 (인자 없음)
                auto-config
                → 현재 위치가 LNCEL-*일 때만 동작
                → LNCEL 하위 MO(CAPR, DRX, SIB 등) 일괄 생성

            [2] ANTL 생성
                auto-config ANTL *                → RMOD 내부에서 모든 ANTL 자동 생성
                auto-config ANTL 3                → ANTL-3 하나만 생성

            [3] CHANNEL 생성
                auto-config CHANNEL * --rmod 3    → CHANNELGROUP 내부에서 모든 채널 생성 (RX + TX)
                auto-config CHANNEL 2 --rmod 3    → 특정 포트 번호 기반 채널만 생성

            [4] LCELL + CHANNELGROUP + CHANNEL 자동 생성
                auto-config LCELL <ID>
                예: auto-config LCELL 105
                → CELLMAPPING 내부에서 LCELL-105 생성 + CHANNELGROUP-1 생성 + 채널 자동 생성

        주의:
            - ANTL은 반드시 RMOD 내부에서 호출해야 함
            - CHANNEL은 반드시 CHANNELGROUP 내부에서 호출해야 함
            - LCELL은 반드시 CELLMAPPING 내부에서 호출해야 함
            - LNCEL 자동 구성은 위치가 LNCEL-*일 때만 호출 가능
        """
        
        print(f"[디버그] do_auto_config 진입! arg: {repr(arg)}")
        if not arg.strip():
            if self.mo_class != "LNCEL":
                self.perror("auto-config는 LNCEL-* 내부에서만 사용할 수 있습니다.")
                return
            
            if self.du_type in ("du10", "DU10", "fsmf", "FSMF") and self.mode == "bts":
                LNCEL_script_steps = [
                    ("CAPR", "0"),
                    "exit",
                    ("CATMCEL", "0"),
                    "exit",
                    ("CDFIM", "1"),
                    "exit",
                    ("DRX", "0"),
                    "exit",
                    ("SDRX", "0"),
                    "exit",
                    ("SIB", "0"),
                    "exit",
                    ("IFGDPR", "0"),
                    "exit",
                    ("IFGPR", "0"),
                    "exit",
                    ("IRFIM", "1"),
                    "exit",
                    ("LNCEL_FDD", "0"),
                    ("APUCCH_FDD", "0"),
                    "exit",
                    ("MPUCCH_FDD", "0"),
                    "exit",
                    "exit",
                    ("LNHOIF", "1"),
                    "exit",
                    "exit"
                ]
            elif self.du_type in ("du10", "DU10", "fsmf", "FSMF") and self.mode == "cell":
                LNCEL_script_steps = [
                    ("CAPR", "0"),
                    "exit",
                    ("CATMCEL", "0"),
                    "exit",
                    ("CDFIM", "1"),
                    "exit",
                    ("DRX", "0"),
                    "exit",
                    ("SDRX", "0"),
                    "exit",
                    ("SIB", "0"),
                    "exit",
                    ("IFGDPR", "0"),
                    "exit",
                    ("IFGPR", "0"),
                    "exit",
                    ("LNCEL_FDD", "0"),
                    ("APUCCH_FDD", "0"),
                    "exit",
                    ("MPUCCH_FDD", "0"),
                    "exit",
                    "exit",
                    "exit"
                ]
            elif self.du_type in ("du20", "DU20"):
                LNCEL_script_steps = [
                    ("CAPR", "0"),
                    "exit",
                    ("CATMCEL", "0"),
                    "exit",
                    ("CDFIM", "1"),
                    "exit",
                    ("DRX", "0"),
                    "exit",
                    ("SDRX", "0"),
                    "exit",
                    ("SIB", "0"),
                    "exit",
                    ("IFGDPR", "0"),
                    "exit",
                    ("IFGPR", "0"),
                    "exit",
                    ("IRFIM", "1"),
                    "exit",
                    ("LNCEL_FDD", "0"),
                    ("APUCCH_FDD", "0"),
                    "exit",
                    ("MPUCCH_FDD", "0"),
                    "exit",
                    "exit",
                    ("BBPOOLALLOC", "0"),
                    "exit",
                    "exit"
                ]

            for step in LNCEL_script_steps:
                if step == "exit":
                    self.onecmd("exit")
                else:
                    name, value = step
                    self._enter_or_create_mo(name, value)
                    # 파라미터 설정 생략 — 템플릿 or rulebook으로 확장 시 추가
                    # self._set_param(...) 은 명시적 설계 없으면 넣지 않음

            if is_debug:
                self.poutput("[OK] LNCEL 하위 구성 자동 완료")
            return


        parser = argparse.ArgumentParser(prog="auto-config", add_help=False)
        parser.add_argument("mo_type", type=str, help="MO 종류 (ANTL 또는 CHANNEL)")
        parser.add_argument("mo_index", type=str, help="'*' 또는 숫자", nargs="?")
        parser.add_argument("--rmod", type=int, help="참조할 RMOD ID (CHANNEL용)")

        try:
            args = parser.parse_args(shlex.split(arg))
        except SystemExit:
            self.perror("사용법: auto-config <MO> [*|숫자] [--rmod ID]")
            return

        if not hasattr(self, "ru_type") or not self.ru_type:
            self.perror("먼저 set-ru-type 명령어로 RU 타입을 설정해주세요.")
            return

        try:
            ru_dict = load_ru_dict(self, self.rat_type)

            tmp_ru_type = None
            if self.rat_type.upper() == "4G":
                tmp_ru_type = self.ru_type
            elif self.rat_type.upper() == "5G":
                tmp_ru_type = self.cell_type
            if tmp_ru_type not in ru_dict:
                self.perror(f"RU 타입 '{tmp_ru_type}'에 대한 auto-config 정보가 없습니다.")
                return

            ru_info = ru_dict[tmp_ru_type]
            mo_type = args.mo_type.upper()

            # ANTL 처리
            if mo_type == "ANTL":
                if self.mo_class != "RMOD":
                    self.perror("ANTL은 RMOD-* 내부에서만 생성할 수 있습니다.")
                    return

                antennas = ru_info.get("ANTENNA", [])
                template = ru_info.get("ANTL_TEMPLATE", {})

                if args.mo_index == "*" or args.mo_index is None:
                    indices = list(range(1, len(antennas) + 1))
                else:
                    try:
                        index = int(args.mo_index)
                        if index < 1 or index > len(antennas):
                            self.perror(f"ANTL-{index}는 유효한 범위를 벗어났습니다.")
                            return
                        indices = [index]
                    except ValueError:
                        self.perror("두 번째 인자는 '*' 또는 숫자여야 합니다.")
                        return

                for i in indices:
                    self._enter_or_create_mo("ANTL", str(i))
                    self._set_param("antPortId", str(i))
                    for key, val in template.items():
                        self._set_param(key, val)
                    self.onecmd("exit")

                if is_debug:
                    self.poutput(f"[OK] ANTL 자동 생성 완료 ({len(indices)}개)")

            # CHANNEL 처리
            elif mo_type == "CHANNEL":
                rmod_id = args.rmod if args.rmod is not None else getattr(self, "last_rmod_id", None)
                if rmod_id is None:
                    self.perror("참조할 RMOD ID가 없습니다. (--rmod 사용 또는 RMOD를 먼저 생성하세요)")
                    return

                if self.mo_class != "CHANNELGROUP":
                    self.perror("CHANNEL은 CHANNELGROUP 내부에서 생성해야 합니다.")
                    return

                ch_idx = 1

                # ✅ 4G 분기
                if self.rat_type == "4G":
                    print("CHANNEL 4G용 진입")
                    txrx_ports = ru_info.get("TXRX_PORTS", [])

                    # 3sector인 경우 port 5 추가
                    if self.ru_type == "FXCA" and self.sector_3:
                        if is_debug:
                            print("3 sector로 인한 5번 추가")
                        txrx_ports += [5]

                    total_ports = len(txrx_ports)

                    if args.mo_index == "*" or args.mo_index is None:
                        indices = list(range(1, total_ports + 1))
                    else:
                        try:
                            index = int(args.mo_index)
                            if index < 1 or index > total_ports:
                                self.perror(f"CHANNEL-{index}는 유효한 범위를 벗어났습니다.")
                                return
                            indices = [index]
                        except ValueError:
                            self.perror("두 번째 인자는 '*' 또는 숫자여야 합니다.")
                            return

                    # RX 채널 생성
                    for i in indices:
                        port = txrx_ports[i - 1]
                        self._enter_or_create_mo("CHANNEL", str(ch_idx))
                        antl_dist = self._find_antl_dist(rmod_id, port)
                        if not antl_dist:
                            self.perror(f"RMOD-{rmod_id} 하위에서 ANTL-{port}을 찾을 수 없습니다.")
                            return
                        self._set_param("antlDN", antl_dist)
                        self._set_param("direction", "RX")
                        ch_idx += 1
                        self.onecmd("exit")

                    # TX 채널 생성
                    for i in indices:
                        port = txrx_ports[i - 1]
                        self._enter_or_create_mo("CHANNEL", str(ch_idx))
                        antl_dist = self._find_antl_dist(rmod_id, port)
                        if not antl_dist:
                            self.perror(f"RMOD-{rmod_id} 하위에서 ANTL-{port}을 찾을 수 없습니다.")
                            return
                        self._set_param("antlDN", antl_dist)
                        self._set_param("direction", "TX")
                        ch_idx += 1
                        self.onecmd("exit")

                    if is_debug:
                        self.poutput(f"[OK] 4G CHANNEL 자동 생성 완료 ({(len(indices) * 2)}개)")

                # ✅ 5G 분기
                elif self.rat_type == "5G":
                    print("CHANNEL 5G용 진입")
                    print("ru_info = ", ru_info)

                    # 1) 방향 리스트 확보 (기존 동일)
                    directions = self._resolve_channel_directions(ru_info)
                    if not directions:
                        self.perror(f"[오류] RU 타입 {getattr(self, 'ru_type', '')}에 대한 채널 정보가 없습니다. "
                                    f"(DU={getattr(self, 'du_type', '')}, nrCellType={getattr(self, 'nrcell_type', '')})")
                        return

                    total_channels = len(directions)

                    # 2) 인덱스 처리 (기존 동일)
                    if args.mo_index == "*" or args.mo_index is None:
                        indices = list(range(1, total_channels + 1))
                    else:
                        try:
                            index = int(args.mo_index)
                            if index < 1 or index > total_channels:
                                self.perror(f"CHANNEL-{index}는 유효한 범위를 벗어났습니다.")
                                return
                            indices = [index]
                        except ValueError:
                            self.perror("두 번째 인자는 '*' 또는 숫자여야 합니다.")
                            return

                    # 3) ANTL/PHYANT 분기 — ru_info의 ANT_TYPE 사용
                    ant_type = self._resolve_ant_type_from_ru_info(ru_info)

                    rmod_class_name = "RMOD"
                    antl_class_name = "ANTL"

                    if self.rat_type.upper() == "5G" and getattr(self, "ru_type", None) == "APHA":
                        rmod_class_name = "ASIRMOD"
                        antl_class_name = "ASIANTL"

                    # --------------------------
                    # ANTL 모드
                    # --------------------------
                    if ant_type == "ANTL":
                        tx_ports, rx_ports = self._select_antl_ports_by_counts(directions)

                        # APHA 특수 처리
                        if getattr(self, "ru_type", None) == "APHA":
                            tx_ports = [1, 2, 3, 4]
                            rx_ports = [1, 2]

                        # AZQS 특수 처리
                        if getattr(self, "cell_type", None) == "AZQS_2_2_0":
                            tx_ports = [1, 5]
                            rx_ports = [2, 6]

                        # AZQS 특수 처리
                        if getattr(self, "cell_type", None) == "AZQS_2_2_4":
                            tx_ports = [1, 5]
                            rx_ports = [2, 6]

                        tx_i = rx_i = 0

                        for i in indices:
                            ch_dir = directions[i - 1]
                            self._enter_or_create_mo("CHANNEL", str(ch_idx))

                            if ch_dir == "TX":
                                port = tx_ports[tx_i % len(tx_ports)]
                                tx_i += 1
                            else:
                                port = rx_ports[rx_i % len(rx_ports)]
                                rx_i += 1

                            # ✅ APHA인 경우 RMOD → ASIRMOD, ANTL → ASIANTL 로 반영
                            self._set_param(
                                "antlDN",
                                f"MRBTS-{self.bts_id}/EQM-1/APEQM-1/{rmod_class_name}-{self.last_rmod_id}/{antl_class_name}-{port}"
                            )
                            self._set_param("direction", ch_dir)

                            ch_idx += 1
                            self.onecmd("exit")

                        if is_debug:
                            self.poutput(f"[OK] 5G CHANNEL(ANTL) 자동 생성 완료 ({len(indices)}개)")

                    # --------------------------
                    # PHYANT 모드 (기존 그대로)
                    # --------------------------
                    elif ant_type == "PHYANT" :
                        for i in indices:
                            ch_dir = directions[i - 1]
                            self._enter_or_create_mo("CHANNEL", str(ch_idx))
                            self._set_param(
                                "resourceDN",
                                f"MRBTS-{self.bts_id}/EQM-1/APEQM-1/RMOD-{self.last_rmod_id}/PHYANT-1"
                            )
                            self._set_param("direction", ch_dir)
                            ch_idx += 1
                            self.onecmd("exit")

                        if is_debug:
                            self.poutput(f"[OK] 5G CHANNEL(PHYANT) 자동 생성 완료 ({len(indices)}개)")
                
            elif mo_type == "LCELL":
                if self.mo_class != "CELLMAPPING":
                    self.perror("LCELL 자동 생성은 CELLMAPPING 내부에서만 가능합니다.")
                    return

                if args.mo_index is None:
                    self.perror("LCELL 생성 시 ID를 명시해야 합니다. 예: auto-config LCELL 105")
                    return

                try:
                    lcell_id = int(args.mo_index)
                except ValueError:
                    self.perror("LCELL ID는 숫자여야 합니다.")
                    return

                self._enter_or_create_mo("LCELL", str(lcell_id))
                self._enter_or_create_mo("CHANNELGROUP", "1")
                self.onecmd(f"auto_config CHANNEL *")
                self.onecmd("exit")
                self.onecmd("exit")

            elif mo_type == "LCELNR":
                if self.mo_class != "CELLMAPPING":
                    self.perror("LCELNR 자동 생성은 CELLMAPPING 내부에서만 가능합니다.")
                    return

                if args.mo_index is None:
                    self.perror("LCELNR 생성 시 ID를 명시해야 합니다. 예: auto-config LCELNR 105")
                    return

                try:
                    lcelnr_id = int(args.mo_index)
                except ValueError:
                    self.perror("LCELNR ID는 숫자여야 합니다.")
                    return

                self._enter_or_create_mo("LCELNR", str(lcelnr_id))
                self._enter_or_create_mo("CHANNELGROUP", "1")
                self.onecmd(f"auto_config CHANNEL *")
                self.onecmd("exit")
                self.onecmd("exit")

            else:
                self.perror(f"[오류] 지원하지 않는 auto-config MO: {mo_type}")

        except Exception as e:
            self.perror(f"[오류] auto-config 실패: {e}")
            
    # ===== helper: ANT_TYPE 읽기 (ANTL/PHYANT) =====
    def _resolve_ant_type_from_ru_info(self, ru_info: dict) -> str:
        v = ru_info.get("ANT_TYPE") or ru_info.get("ant_type")
        return (v or "PHYANT").upper()

    # ===== helper: ANTL 포트 선택 (정적 테이블 없이 directions 수량으로 결정) =====
    def _select_antl_ports_by_counts(self, directions: list[str]) -> tuple[list[int], list[int]]:
        """
        규칙:
        - TX 개수 ≤ 2 → TX 포트 [1,2] ;  > 2 → [1,2,5,6]
        - RX 개수 ≤ 2 → RX 포트 [1,2] ;  > 2 → [1,2,5,6]
        """
        tx_cnt = sum(1 for d in directions if d == "TX")
        rx_cnt = sum(1 for d in directions if d == "RX")
        base = [1, 2]
        ext  = [1, 2, 5, 6]
        tx_ports = base if tx_cnt <= 2 else ext
        rx_ports = base if rx_cnt <= 2 else ext
        return tx_ports, rx_ports
    
    def _resolve_channel_directions(self, ru_info: dict) -> list:
        """
        현재 JSON 구조(셀타입 키 기반)에 맞춘 채널 방향 해석.
        기대 ru_info 예:
        {
            "CODE": "...",
            "CHANNEL_TEMPLATE": {
            "DU10": { "2DL2UL": [ ... ] },
            "DU20": { "4DL4UL": [ ... ] }
            }
        }
        선택 규칙:
        1) ct[DU]에 유일한 키만 있으면 그 키 사용
        2) 유일키가 아니면 self.cell_type에서 변형(예: '..._4_2')을 파싱해
            '4DL2UL' 형태로 변환 후 해당 키 사용
        3) 실패하면 빈 리스트
        """
        ct = ru_info.get("CHANNEL_TEMPLATE", {})
        if not ct:
            if is_debug: self.poutput("[DBG] CHANNEL_TEMPLATE 없음")
            return []

        du = getattr(self, "du_type", None)
        if du not in ct or not isinstance(ct[du], dict):
            if is_debug: self.poutput(f"[DBG] DU 키 미존재/형식 불일치: du={du}, ct.keys={list(ct.keys())}")
            return []

        du_node = ct[du]
        # 'direction' 같은 구포맷 키는 현재 구조에선 없다고 가정하나, 혹시 대비
        if isinstance(du_node, list):
            return du_node
        if "direction" in du_node and isinstance(du_node["direction"], list):
            return du_node["direction"]

        # 1) 유일 키면 바로 사용
        keys_wo_dir = [k for k in du_node.keys() if k != "direction"]
        if len(keys_wo_dir) == 1:
            only_key = keys_wo_dir[0]
            if is_debug: self.poutput(f"[DBG] 단일키 자동 선택: {only_key}")
            return du_node[only_key]

        # 2) self.cell_type에서 변형 파싱 → 4DL2UL/2DL2UL 등으로 매핑
        cell_type = getattr(self, "cell_type", "") or ""
        ru = getattr(self, "ru_type", "") or ""
        nrct_guess = ""
        if cell_type and ru and cell_type.upper().startswith(ru.upper() + "_"):
            variant = cell_type[len(ru) + 1:]  # '4_2', '2_2_0' 등
            nrct_guess = self._variant_to_nrcell_from_variant(variant)

        if is_debug:
            self.poutput(f"[DBG] du={du}, keys={list(du_node.keys())}, nrct_guess={nrct_guess}")

        if nrct_guess and nrct_guess in du_node:
            return du_node[nrct_guess]

        if is_debug: self.poutput("[DBG] 매칭 실패 → 빈 리스트 반환")
        return []

    def _variant_to_nrcell_from_variant(variant: str) -> str:
        """
        '4_2' → '4DL2UL', '4_4' → '4DL4UL', '2_2_0' → '2DL2UL'
        숫자 2개(D, U)만 읽고 나머진 무시.
        """
        v = (variant or "").strip("_")
        if not v:
            return ""
        parts = v.split("_")
        if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
            return f"{parts[0]}DL{parts[1]}UL"
        return ""

    def do_chg_mo_id(self, arg):
        """
        현재 위치한 MO의 ID를 새로운 ID로 변경합니다.
        하위 모든 managedObject의 distName도 함께 변경됩니다.
        사용법: chg-mo-id <새로운 ID>
        예시: chg-mo-id 1
        """
        tokens = shlex.split(arg)
        if len(tokens) != 1:
            self.perror("사용법: chg-mo-id <새로운 ID>")
            return

        new_id = tokens[0]
        if not new_id.isdigit():
            self.perror("[오류] ID는 숫자만 가능합니다.")
            return

        if not self.match_tail or not self.mo_class:
            self.perror("[오류] 현재 위치 정보가 없습니다.")
            return

        # 현재 distName 추출
        old_token = f"{self.mo_class}-"  # 예: CLOCK-
        match = re.search(rf"{old_token}(\d+)", self.match_tail)
        if not match:
            self.perror(f"[오류] 현재 match_tail에서 {self.mo_class} ID를 찾을 수 없습니다.")
            return

        old_id = match.group(1)
        if old_id == new_id:
            self.poutput(f"[안내] 현재 ID와 동일하므로 변경하지 않습니다.")
            return

        old_str = f"{self.mo_class}-{old_id}"
        new_str = f"{self.mo_class}-{new_id}"
        changed_count = 0

        for mo in self.xml_tree.iter("managedObject"):
            dist = mo.attrib.get("distName", "")
            if dist.startswith(self.match_tail):
                new_dist = dist.replace(old_str, new_str)
                mo.attrib["distName"] = new_dist
                changed_count += 1

        # self.match_tail도 갱신
        self.match_tail = self.match_tail.replace(old_str, new_str)

        # CLI 프롬프트도 재구성
        self.prompt = self._build_prompt()
        self.poutput(f"[완료] {old_str} → {new_str} (총 {changed_count}개 MO 경로 변경)")

        self.onecmd("exit")
