import argparse
import shlex
from proto import message_pb2
from cli.settings import grpc_stub
from cli.settings import is_debug

class ShowCommandMixin:
    def do_show_user_input(self, arg):
        """사용자가 직접 입력한 명령만 출력합니다."""
        if not hasattr(self, "user_inputs") or not self.user_inputs:
            self.poutput("사용자 입력 기록이 없습니다.")
            return

        self.poutput("[사용자 입력 기록]")
        for entry in self.user_inputs:
            if entry[0] == "MO-CREATE":
                self.poutput(f"[MO 생성] {entry[1]}")
            elif entry[0] == "SET":
                _, mo_path, key, value = entry
                self.poutput(f"[PARAM 생성 or 수정] {mo_path} → {key} = {value}")
            elif entry[0] == "SET-LIST":
                _, mo_path, list_name, index, key, value = entry
                self.poutput(f"[PARAM-LIST 생성 or 수정] {mo_path} -> {list_name}[{index}] → {key} = {value}")

    def do_show_cfg(self, arg):
        """현재 계층 또는 지정된 MO 기준의 XML 파라미터 출력"""
        parser = argparse.ArgumentParser(prog="show-cfg", add_help=False)
        group = parser.add_mutually_exclusive_group()
        group.add_argument("-a", "--all", action="store_true", help="모든 파라미터 출력")
        group.add_argument("-r", "--required", action="store_true", help="필수 파라미터만 출력")
        parser.add_argument("-m", "--mo", type=str, help="특정 MO부터 하위까지 출력 (예: LNBTS-12345)")

        try:
            parsed_args = parser.parse_args(shlex.split(arg))
        except SystemExit:
            return

        # 기본은 -a와 동일하게 동작
        required_only = parsed_args.required

        if parsed_args.mo:
            self.show_mo_recursive(parsed_args.mo.strip(), required_only)
        else:
            self.show_mo_by_class(required_only)

    def show_mo_recursive(self, base_distname, required_only=False):
        if not hasattr(self, "xml_tree") or self.xml_tree is None:
            self.perror("XML이 아직 로드되지 않았습니다.")
            return

        mos = self.xml_tree.findall(".//{*}managedObject")
        base_level = None
        matched = []

        for mo in mos:
            dist = mo.attrib.get("distName", "")
            if base_distname in dist:
                parts = dist.split("/")
                if base_level is None:
                    for i, part in enumerate(parts):
                        if base_distname in part:
                            base_level = i
                            break
                matched.append((mo, parts))

        if not matched:
            self.perror(f"'{base_distname}' 를 포함하는 MO를 찾을 수 없습니다.")
            return

        for mo, parts in matched:
            level = len(parts) - (base_level + 1)
            indent = "  " * level
            dist = mo.attrib.get("distName", "")
            self.poutput(f"{indent}{dist}")
            self._print_mo_params(mo, indent, required_only)

                
    def show_mo_by_class(self, required_only=False):
        if not hasattr(self, "xml_tree") or self.xml_tree is None:
            self.perror("XML이 아직 로드되지 않았습니다.")
            return

        for mo in self.xml_tree.findall(".//{*}managedObject"):
            class_name = mo.attrib.get("class", "")
            dist_name = mo.attrib.get("distName", "")
            if class_name.endswith(self.mo_class) and dist_name.endswith(self.match_tail):
                self._print_mo_params(mo, "", required_only)
                return

        self.perror(f"{self.mo_class} {self.match_tail} not found in XML.")

    def _print_mo_params(self, mo, indent="", required_only=False):
        param_dict = self.mo_param_dict.get(self.mo_class, {}).get("params", {})

        # 일반 파라미터
        for p in mo.findall("{*}p"):
            name = p.attrib.get("name")
            value = p.text or ""
            meta = param_dict.get(name, {})
            if required_only and not meta.get("required", False):
                continue
            self.poutput(f"{indent}  {name}: {value}")

        # 리스트 파라미터
        for lst in mo.findall("{*}list"):
            list_name = lst.attrib.get("name")
            list_meta_children = param_dict.get(list_name, {}).get("children", {})

            # (A) <list> 바로 아래에 <p>가 있는 경우 (이 케이스가 지금 빠졌었음)
            direct_ps = lst.findall("{*}p")
            if direct_ps:
                for i, p in enumerate(direct_ps, 1):
                    pname = p.attrib.get("name")       # 존재할 수도, 없을 수도 있음
                    pval = p.text or ""

                    if pname:
                        # required_only라면 children 메타에서 required 여부 확인
                        if required_only and not (pname in list_meta_children and list_meta_children[pname].get("required", False)):
                            continue
                        self.poutput(f"{indent}  {list_name}[{i}]: {pname}={pval}")
                    else:
                        # name 없는 값형 리스트 항목 (예: targetDNList)
                        # required_only는 적용할 메타가 없으므로 그대로 출력
                        self.poutput(f"{indent}  {list_name}[{i}]: {pval}")

            # (B) <item> 기반 리스트
            items = lst.findall("{*}item")
            if items:
                for idx, item in enumerate(items, 1):
                    pair_strs = []
                    for p in item.findall("{*}p"):
                        k = p.attrib.get("name")
                        v = p.text or ""
                        if required_only:
                            if not (k in list_meta_children and list_meta_children[k].get("required", False)):
                                continue
                        # k가 없을 수도 있지만, item 하위는 보통 name이 있으므로 k 없는 경우도 방어
                        pair_strs.append(f"{k}={v}" if k else v)
                    if pair_strs:
                        self.poutput(f"{indent}  {list_name}[{idx}]: " + ", ".join(pair_strs))


    def do_show_glb(self, arg):
        """
        서버의 data/received 폴더에 있는 파일 목록을 확인합니다.
        사용법: show-glb [--ext xml|cli|all] [--limit N] [--sort time|name|key]
        ex : 
            # XML만, 시간순 정렬
            show-glb --ext xml --sort time
            # 스크립트(cli) 파일만, 이름순 정렬
            show-glb --ext cli --sort name
            # 유니크 키 기준 정렬
            show-glb --sort key --limit 10
        """
        parser = argparse.ArgumentParser(prog="show-glb", add_help=False)
        parser.add_argument("--ext", choices=["xml", "cli", "all"], default="all", help="확장자 필터링 (기본: all)")
        parser.add_argument("--limit", type=int, default=0, help="최대 표시 개수")
        parser.add_argument("--sort", choices=["time", "name", "key"], default="time", help="정렬 기준 (기본: time)")

        try:
            args = parser.parse_args(shlex.split(arg))
            payload = f"{args.ext}||{args.limit}||{args.sort}"

            request = message_pb2.Request(command="show-glb", payload=payload)
            response = self.stub.SendCommand(request)

            if response.success:
                self.poutput("[서버 저장된 파일 목록]")
                self.poutput(response.result)
            else:
                self.perror(f"[서버 오류] {response.result}")
        except SystemExit:
            return
        except Exception as e:
            self.perror(f"[클라이언트 오류] {e}")

    def do_show_key(self, arg):
        """현재 세션의 task key를 출력합니다."""
        if hasattr(self, "task_key"):
            self.poutput(f"현재 task key: {self.task_key}")
        else:
            self.poutput("task key가 아직 생성되지 않았습니다. (예: tgt-bts 명령어 실행 필요)")

    def do_show_sib(self, arg):
        """형제 MO 중 특정 ID의 정보를 출력합니다. (옵션: -r, -o, -a)"""
        parser = argparse.ArgumentParser(prog="show-sib", add_help=False)
        parser.add_argument("sibling_id", type=str)
        group = parser.add_mutually_exclusive_group()
        group.add_argument("-r", "--required", action="store_true", help="필수 입력 파라미터만 출력 (IREQ)")
        group.add_argument("-o", "--optional", action="store_true", help="선택 입력 파라미터만 출력 (OCLI)")
        group.add_argument("-a", "--all", action="store_true", help="모든 파라미터 출력")

        try:
            args = parser.parse_args(arg.split())
            if not args.sibling_id.isdigit():
                self.perror("사용법: show-sib <ID>")
                return

            if args.required:
                mode = "ireq"
            elif args.optional:
                mode = "ocli"
            elif args.all:
                mode = "all"
            else:
                mode = "default"

            self.show_sib_by_id(args.sibling_id, mode)

        except SystemExit:
            self.perror("사용법: show-sib <ID> [-r|-o|-a]")

    def show_sib_by_id(self, sibling_id: str, mode="default"):
        if not hasattr(self, "xml_tree") or self.xml_tree is None:
            self.perror("XML 트리가 로드되지 않았습니다.")
            return

        if not hasattr(self, "mo_class") or not hasattr(self, "match_tail"):
            self.perror("현재 계층 정보가 부족합니다.")
            return

        parent_tail = "/".join(self.match_tail.split("/")[:-1])
        target_dn = f"{parent_tail}/{self.mo_class}-{sibling_id}"

        found = False
        for mo in self.xml_tree.findall(".//{*}managedObject"):
            dn = mo.attrib.get("distName", "")
            if dn.endswith(target_dn):
                for p in mo.findall("{*}p"):
                    name = p.attrib.get("name", "")
                    value = (p.text or "").strip()
                    flag = p.attrib.get("flag", "").upper()

                    if mode == "default" and flag in ("IREQ", "OCLI"):
                        self.poutput(f"{name}: {value}")
                    elif mode == "ireq" and flag == "IREQ":
                        self.poutput(f"{name}: {value}")
                    elif mode == "ocli" and flag == "OCLI":
                        self.poutput(f"{name}: {value}")
                    elif mode == "all":
                        self.poutput(f"{name}: {value}")

                found = True
                break

        if not found:
            self.poutput(f"{target_dn} 경로에 해당하는 MO를 찾을 수 없습니다.")

    def do_show_can_mo(self, arg):
        """
        현재 MO 기준으로 가능한 하위 MO 목록을 출력합니다.
        사용법: show-can-mo
        """
        if not self.mo_class:
            self.perror("현재 위치한 MO가 없습니다.")
            return

        if self.mo_class not in self.mo_param_dict:
            self.perror(f"[오류] MO '{self.mo_class}'에 대한 정보가 사전에 등록되어 있지 않습니다.")
            return

        children = self.mo_param_dict[self.mo_class].get("children", [])
        if not children:
            self.poutput(f"[{self.mo_class}] 하위 MO가 정의되어 있지 않습니다.")
            return

        self.poutput(f"[{self.mo_class}] 입력 가능한 하위 MO 목록:")
        for child in children:
            self.poutput(f"  - {child}")

    def do_show_can_pa(self, arg):
        """
        현재 MO 기준으로 가능한 파라미터 목록을 출력합니다.
        사용법: show-can_pa [-r | -a]
        """
        if not self.mo_class:
            self.perror("현재 위치한 MO가 없습니다.")
            return

        if self.mo_class not in self.mo_param_dict:
            self.perror(f"[오류] MO '{self.mo_class}'에 대한 정보가 사전에 등록되어 있지 않습니다.")
            return

        args = shlex.split(arg)
        show_all = "-a" in args

        params = self.mo_param_dict[self.mo_class].get("params", {})
        if not params:
            self.poutput(f"[{self.mo_class}] 정의된 파라미터가 없습니다.")
            return

        filtered = {
            k: v for k, v in params.items()
        }

        if not filtered:
            self.poutput("[알림] 조건에 맞는 파라미터가 없습니다.")
            return

        self.poutput(f"[{self.mo_class}] 입력 가능한 파라미터 목록:")
        for name, info in filtered.items():
            type_str = info.get("type", "unknown")
            default = info.get("default", "null")
            required = "Y" if info.get("required", False) else "N"
            self.poutput(f"  - {name} (type: {type_str}, required: {required}, default: {default})")

    def do_show_para(self, arg):
        """
        특정 파라미터 이름이 설정된 MO들을 조회합니다.
        사용법: show-para <파라미터명>
        예시: show-para actCli
        """
        param_name = arg.strip()
        if not param_name:
            self.perror("사용법: show-para <파라미터명>")
            return

        if not hasattr(self, "xml_tree") or self.xml_tree is None:
            self.perror("XML이 로드되지 않았습니다.")
            return

        cmdata = self.xml_tree.find(".//{*}cmData")
        if cmdata is None:
            self.perror("cmData 노드를 찾을 수 없습니다.")
            return

        found = []
        for mo in cmdata.findall("{*}managedObject"):
            dist = mo.attrib.get("distName", "")
            for p in mo.findall("{*}p"):
                if p.attrib.get("name") == param_name:
                    found.append((dist, p.text or ""))

        if not found:
            self.poutput(f"[알림] '{param_name}' 파라미터가 설정된 MO를 찾을 수 없습니다.")
            return

        self.poutput(f"[조회 결과] 파라미터 '{param_name}' 값 목록:")
        for dist, val in found:
            self.poutput(f"  - {dist}: {val}")
