import argparse
import copy
import shlex
import os
import json
import tempfile
from proto import message_pb2
import xml.etree.ElementTree as ET
from cli.settings import grpc_stub
from cli.common.util.commit_utils import load_mo_param_dict
from cli.common.util.tmpl_utils import apply_class_based_mapping, load_cli_template_as_rule
from cli.common.util.xml_utils import strip_namespace
from cli.common.util.server_utils import load_from_server, save_to_server
from cli.settings import is_debug
from cli.common.util.path_utils import get_path

class SetCommandMixin:
    def do_set_cfg_scf(self, arg):
        """
        서버에서 템플릿 XML 파일을 받아서 로드합니다.
        사용법: set-cfg-scf <파일명>
        """
        filename = arg.strip()
        if not filename:
            self.perror("사용법: set-cfg-scf <파일명>")
            return
        
        request = message_pb2.Request(command="set-cfg-scf", payload=filename)
        response = grpc_stub.SendCommand(request)

        if response.success:
            try:
                xml_data = response.result

                # 받은 XML 문자열 파싱
                tree = ET.ElementTree(ET.fromstring(xml_data))

                #네임스페이스 정리
                strip_namespace(tree)

                # 공백/줄바꿈 정리
                self._clean_whitespace(tree.getroot())

                # 트리 설정
                self.xml_tree = tree
                self.ref_tree = copy.deepcopy(tree)

                # bts_id 추출
                #cmdata = self.xml_tree.getroot().find(".//{*}cmData")
                #first_mo = cmdata.find("{*}managedObject") if cmdata is not None else None
                #if first_mo is not None:
                #    dist_name = first_mo.attrib.get("distName", "")
                #    if dist_name.startswith("MRBTS-"):
                #        self.bts_id = dist_name.split("-")[1]
                self.config.set("cmd_status", True)
                if is_debug:
                    self.poutput(f"[서버] 템플릿 {filename} 로드 성공")
            
            except Exception as e:
                self.perror(f"[클라] XML 파싱 실패: {e}")
        else:
            self.config.set("cmd_status", False)
            self.perror(f"[서버] 실패: {response.result}")

    def _clean_whitespace(self, elem):
        """ElementTree 트리에서 불필요한 text/tail 공백/줄바꿈 제거"""
        if elem.text is not None and elem.text.strip() == "":
            elem.text = None
        if elem.tail is not None and elem.tail.strip() == "":
            elem.tail = None
        for child in elem:
            self._clean_whitespace(child)

    def do_set_du_type(self, arg):
        """
        DU 타입을 설정합니다. 이후 템플릿 구성 등에 사용됩니다.
        사용법: set-du-type <DU10 | DU20>
        예시: set-du-type DU10
        """
        parser = argparse.ArgumentParser(prog="set-du-type", add_help=False)
        parser.add_argument("du_type", choices=["du10", "du20", "DU10", "DU20", "fsmf", "FSMF"], help="DU 타입 (FSMF, DU10 또는 DU20)")

        try:
            args = parser.parse_args(shlex.split(arg))
        except SystemExit:
            self.perror("사용법: set-du-type <FSMF | DU10 | DU20>")
            return
        
        self.du_type = args.du_type.upper()
        self.rulebook_param_dict = self._load_rulebook()
        self.mo_param_dict = load_mo_param_dict(self, self.rat_type, self.mo_version, self.du_type)
        if is_debug:
            self.poutput(f"[성공] DU 타입이 '{self.du_type}'으로 설정되었습니다.")

    def do_set_ru_type(self, arg):
        """
        RU 타입을 지정합니다. 이후 prodCodePlanned 및 관련 파라미터 자동 설정에 사용됩니다.
        사용법: set-ru-type <RU_TYPE> [--band <850|2100|2600>]
        예시: set-ru-type FHCG --band 850
        """
        parser = argparse.ArgumentParser(prog="set-ru-type", add_help=False)
        parser.add_argument("ru_type", type=str, help="RU 타입")
        parser.add_argument("--band", "-f", choices=["850", "2100", "2600"], help="FHCG 전용 밴드 옵션")

        try:
            args = parser.parse_args(shlex.split(arg))
        except SystemExit:
            self.perror("사용법: set-ru-type <RU_TYPE> [--band <850|2100|2600>]")
            return

        ru_type = args.ru_type.strip().upper()
        band = args.band

        # 유효성 체크 (PROD/RMOD)
        try:
            prod_data = load_from_server("PRODMAPTBL.json", "json", purpose="prodmap")
            rmod_data = load_from_server("RMODPRODMAPTBL.json", "json", purpose="prodmap")
            prod_dict = list(prod_data.values())[0]["value"]
            rmod_dict = list(rmod_data.values())[0]["value"]
        except Exception as e:
            self.perror(f"[오류] RU 타입 데이터 로딩 실패: {e}")
            return

        valid_keys = set(prod_dict.keys()) | set(rmod_dict.keys())
        if ru_type not in valid_keys:
            self.perror(f"[오류] 알 수 없는 RU 타입: {ru_type}")
            return

        # FHCG 밴드만 허용
        if ru_type == "FHCG":
            self.band_option = band or "850"
        elif band:
            self.perror("[경고] RU 타입이 FHCG가 아니므로 --band 옵션은 무시됩니다.")
            self.band_option = None
        else:
            self.band_option = None

        # 상태 저장
        self.ru_type = ru_type
        if is_debug:
            self.poutput(f"[성공] RU 타입이 '{ru_type}'로 설정되었습니다.")
        if self.band_option:
            self.poutput(f"[참고] 밴드 옵션: {self.band_option}")

        # ===== 공통 파이프라인: RAT 상관없이 먼저 실행 =====
        if self.mode == "cell":
            self.do_dnload_bts_cfg_raw("")
            self.do_set_cfg_scf("genScf")
            self._set_du_type_from_smod()   # ← 여기서 self.du_type 확정
        else:
            self.perror(f"[오류] 알 수 없는 CLI 모드입니다: {self.mode}")
            return

        # ===== RAT별 처리 =====
        if self.rat_type == "4G":
            # 4G: 템플릿 로딩/적용 수행
            tmpl_name = f"nok_lte_ru_{ru_type}"
            if ru_type == "FHCG" and self.band_option:
                tmpl_name += f"_{self.band_option}"
            tmpl_name += ".cli"

            try:
                tmpl_text = load_from_server(tmpl_name, "text", purpose="ruTemplate")
                with tempfile.NamedTemporaryFile(delete=False, mode="w", encoding="utf-8", suffix=".cli") as tmp:
                    tmp.write(tmpl_text)
                    tmpl_file = tmp.name
            except Exception as e:
                self.perror(f"[오류] RU 템플릿 로딩 실패: {e}")
                return

            self._update_rulebook_from_template(tmpl_file)

        elif self.rat_type == "5G":
            # 5G: 템플릿 적용은 set-cell-type에서 수행
            self.poutput("[안내] 5G는 'set-cell-type ?'로 세부 타입을 선택/적용하세요.")
            return

        else:
            self.perror(f"[오류] 알 수 없는 RAT 타입입니다: {self.rat_type}")
            return


    def do_set_cell_type(self, arg):
        if self.rat_type != "5G":
            self.perror("set-cell-type는 5G에서만 사용 가능합니다.")
            return
        if not getattr(self, "ru_type", None):
            self.perror("먼저 set-ru-type 을 실행하세요.")
            return

        # du_type이 확정되어 있어야 목록/파일명이 맞음 (필요시 보장)
        if not getattr(self, "du_type", None):
            self.perror("DU 타입이 아직 결정되지 않았습니다. set-ru-type 후 다시 시도하세요.")
            return

        tokens = shlex.split(arg.strip()) if arg else []
        if not tokens:
            self.perror("사용법: set-cell-type <RUVAR> | set-cell-type ?")
            return

        if tokens[0] == "?":
            opts = self._list_cell_types_for_current_ru()
            if not opts:
                self.perror("해당 RU/DU 조합에 대한 cell-type 목록이 없습니다.")
                return
            for name in opts:
                self.poutput(name)
            return

        cell_type = tokens[0].upper()
        if not cell_type.startswith(self.ru_type + "_"):
            self.perror(f"[오류] 현재 RU({self.ru_type})와 불일치한 cell-type 입니다: {cell_type}")
            return

        self.cell_type = cell_type
        tmpl_name = f"nok_5G_{self.du_type}_ru_{cell_type}.cli"

        try:
            tmpl_text = load_from_server(tmpl_name, "text", purpose="ruTemplate")
            print("tmpl_text = ", tmpl_text)
            with tempfile.NamedTemporaryFile(delete=False, mode="w", encoding="utf-8", suffix=".cli") as tmp:
                tmp.write(tmpl_text)
                tmpl_file = tmp.name
        except Exception as e:
            self.perror(f"[오류] 셀 타입 템플릿 로딩 실패: {e}")
            return

        self._update_rulebook_from_template(tmpl_file)
        self.poutput(f"[OK] cell-type '{self.cell_type}' 적용 완료")

    def _list_cell_types_for_current_ru(self) -> list:
        ru = self.ru_type
        du = self.du_type
        if not ru or not du:
            return []

        # ru_templates 디렉토리 경로
        dirpath = get_path(self.env_type, "scripts", "ru_templates")

        filter_prefix = f"nok_5G_{du}_ru_{ru}_"  # 선택 대상을 RU로 제한
        slice_prefix  = f"nok_5G_{du}_ru_"       # ← 여기 길이로 슬라이스(ru 포함해서 남김)

        try:
            names = [
                fn[len(slice_prefix):-4]                     # ex) AEQY_4_2
                for fn in os.listdir(dirpath)
                if fn.startswith(filter_prefix) and fn.endswith(".cli")
            ]
            return sorted(set(names))
        except Exception as e:
            self.perror(f"[오류] cell-type 목록 조회 실패: {e}")
            return []

    def do_set_ru_para(self, arg):
        """
        RU 관련 파라미터를 설정합니다.
        사용법: set-ru-para sector_3 [true|false]
        기본은 false이며, sector_3 true일 경우 일부 RU에서 다른 템플릿이 사용됩니다.
        """
        parser = argparse.ArgumentParser(prog="set-ru-para", add_help=False)
        parser.add_argument("key", choices=["sector_3"], help="설정할 RU 파라미터 이름")
        parser.add_argument("value", nargs="?", choices=["true", "false"], help="true 또는 false (기본: true)")

        try:
            args = parser.parse_args(shlex.split(arg))
        except SystemExit:
            self.perror("사용법: set-ru-para sector_3 [true|false]")
            return

        if args.key == "sector_3":
            self.sector_3 = args.value == "true"  # 정확히 'true'일 때만 True, 나머지는 모두 False
            if is_debug:
                self.poutput(f"[성공] sector_3 = {self.sector_3}")

    def _update_rulebook_from_template(self, tmpl_file):
        try:
            template_dict = load_cli_template_as_rule(tmpl_file)

            if hasattr(self, "rulebook_param_dict"):
                for mo_class, param_map in template_dict.items():
                    if mo_class in self.rulebook_param_dict:
                        # rulebook 안의 모든 MO-ID("0", "000", "999", ...) 순회
                        for mo_id, param_dict in self.rulebook_param_dict[mo_class].items():
                            for key, meta in param_map.items():
                                old_val = param_dict.get(key, {}).get("value")
                                new_val = meta["value"]

                                if key in param_dict:
                                    if old_val != new_val:
                                        param_dict[key]["value"] = new_val
                                        if is_debug:
                                            print(f"[변경] {mo_class}.{mo_id}.{key}: '{old_val}' → '{new_val}'")
                                    else:
                                        if is_debug:
                                            print(f"[유지] {mo_class}.{mo_id}.{key}: '{old_val}' 그대로")
                                else:
                                    if is_debug:
                                        print(f"[스킵] {mo_class}.{mo_id}.{key} → 룰북에 없음")

            # 저장 파일명
            if self.mode not in {"cell", "bts"}:
                raise ValueError(f"지원되지 않는 mode: {self.mode}")

            filename = f"{self.rat_type}_{self.mo_version}_rulebook_{self.du_type.lower()}_{self.mode}.json"
            json_text = json.dumps(self.rulebook_param_dict, indent=2, ensure_ascii=False)

            # 1. 로컬 저장 (rulebook 폴더)
            rulebook_path = get_path(self.env_type, "rulebook", filename)
            os.makedirs(os.path.dirname(rulebook_path), exist_ok=True)

            with open(rulebook_path, "w", encoding="utf-8") as f:
                f.write(json_text)

            self.poutput(f"[성공] 룰북이 클라이언트에 저장되었습니다: {rulebook_path}")

            # 2. 서버 저장
            save_to_server(self, content=json_text, filename=filename, purpose="rulebook")
            self.poutput(f"[성공] 룰북이 서버에 저장되었습니다: {filename}")

        except Exception as e:
            self.perror(f"[오류] RU 템플릿 파싱 실패: {e}")

        finally:
            # 템플릿 임시 파일 삭제
            try:
                if os.path.exists(tmpl_file):
                    os.remove(tmpl_file)
                    if is_debug:
                        print(f"[정리] 임시 템플릿 파일 삭제됨: {tmpl_file}")
            except Exception as e:
                self.perror(f"[경고] 임시 파일 삭제 실패: {e}")

    def _execute_ru_template_script(self, tmpl_file):
        try:
            self.poutput(f"[INFO] RU 템플릿 실행 중: {tmpl_file}")
            self.do_exec_script("bts_du_10.cli")## 하드 코딩 수정 필요
            self.poutput(f"[성공] RU 템플릿 실행 완료")
        except Exception as e:
            self.perror(f"[오류] RU 템플릿 실행 실패: {e}")

    def do_set_cfg_tmpl(self, arg):
        """
        CLI 템플릿을 불러와 현재 XML 트리에 맞게 매핑 후 CLI로 실행합니다.
        사용법: set-cfg-tmpl <파일명>.cli
        """
        tokens = shlex.split(arg)
        if not tokens:
            self.perror("사용법: set-cfg-tmpl <파일명>.cli")
            return

        ref_filename = tokens[0]
        ref_basename = os.path.splitext(ref_filename)[0]

        try:
            # 1. CLI 템플릿 원본 텍스트 로드
            cli_text = load_from_server(ref_filename, filetype="text", purpose="cli")
            if is_debug:
                self.poutput(f"[템플릿] CLI 텍스트 로드 완료: {ref_filename}")

            # 2. distName 매핑 적용
            mapped_cli_text = apply_class_based_mapping(cli_text, self.xml_tree)
            if is_debug:
                self.poutput(f"[템플릿] distName 매핑 완료")
                print(mapped_cli_text)

            # 3. CLI 스크립트 저장
            script_filename = f"{ref_basename}__script.cli"

            # scripts 경로 가져오기 (DEV/PROD 자동 분기)
            script_path = get_path(self.env_type, "scripts", script_filename)
            os.makedirs(os.path.dirname(script_path), exist_ok=True)

            with open(script_path, "w", encoding="utf-8") as f:
                f.write(mapped_cli_text)

            self.poutput(f"[성공] CLI 스크립트 저장됨: {script_path}")

            if is_debug:
                self.poutput(f"[디버그] CLI 스크립트 저장 완료: {script_path}")

            # 4. CLI 스크립트 실행
            self.do_exec_script(script_filename)

        except Exception as e:
            self.perror(f"[클라] set-cfg-tmpl 실행 중 오류 발생: {e}")



    def _get_user_defined_lncel_ids(self):
        """user_inputs에서 사용자가 생성한 LNCEL ID들을 추출"""
        lncel_ids = []
        for entry in getattr(self, "user_inputs", []):
            if entry[0] == "MO-CREATE" and "LNCEL-" in entry[1]:
                for part in entry[1].split("/"):
                    if part.startswith("LNCEL-"):
                        lncel_ids.append(part.split("-")[1])  # '300', '350'
        return lncel_ids

    def _get_current_param_value(self, mo_class: str, dist_name: str, key: str) -> str:
        for mo in self.xml_tree.findall(".//{*}managedObject"):
            if mo.attrib.get("class", "").split(":")[-1] == mo_class and mo.attrib.get("distName") == dist_name:
                for p in mo.findall("{*}p"):
                    if p.attrib.get("name") == key:
                        return p.text or ""
        return None


    def _find_antl_dist(self, rmod_id: int, port_id: int) -> str:
        """
        XML에서 RMOD-{rmod_id} 하위의 ANTL-{port_id}의 distName을 찾아 반환
        """
        target_suffix = f"/RMOD-{rmod_id}/ANTL-{port_id}"
        for mo in self.xml_tree.findall(".//{*}managedObject"):
            if mo.attrib.get("class", "").endswith("ANTL"):
                dist = mo.attrib.get("distName", "")
                if dist.endswith(target_suffix):
                    return dist
        return None