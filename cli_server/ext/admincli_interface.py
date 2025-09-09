import subprocess
import json
import os
import toml
import re
from cli_server.core.workspace.ws_manager import getWorkspace, WsManager

class AdminCliInterface:
    request_id = 1
    admincli_id = 'Nemuadmin'
    admincli_pw = 'Nokia1234!'
    bts_host_ip = None
    bts_host_port = 443
    delteDN = None
    admincli_result = None
    base_command = './bin/admincli/admin-cli.sh --bts-username={} --bts-password={} --bts-host={} --bts-port={} --format=human'
    command_ext = '--input-file={}'
    command_ext_output = '--output-file={}'
    command_data_simple_prefix = '--data='
    command_data_simple_dict = {"requestId":1, "parameters":{"name":''}}
    command_data_commission_dict = {"requestId":1,"parameters":{"name":"commission",\
                                                                  "parameters":{"skipParameterRelationErrors":False,\
                                                                                 "shouldBeActivated":False}}}
    command_data_recommission_dict = {"requestId":1,"parameters":{"name":"recommission",\
                                                                  "parameters":{"skipParameterRelationErrors":False,\
                                                                                 "shouldBeActivated":False}}}
    command_data_activateplan_dict = {"requestId":1,"parameters":{"name":"activatePlan",\
                                          "parameters":{"deltaDN":""}}}

    command_data_generatescf_dict = {"requestId":1,"parameters":{"name":"generateScf"}}

    command_data_softwareupdate_dict = {"requestId": 1,"parameters":{"name": "softwareUpdate",\
                                                                  "parameters": {"shouldActivate": False,\
                                                                                 "overrideIndependentRUSW": False}}}
    @property
    def bts_host_ip(self):
        ws = getWorkspace()
        return ws.get("bts_ip")

    def getHwInfo(self):
        command_data = ''
        command_new = self.base_command.format(self.admincli_id, self.admincli_pw, self.bts_host_ip, self.bts_host_port)
        command_data_ext = self.command_data_simple_dict
        command_data_ext['requestId'] = self.request_id
        command_data_ext['parameters']['name'] = 'getHwInfo'
        command_data = json.dumps(command_data_ext)
        command_final = command_new + ' ' + self.command_data_simple_prefix + '\'' + command_data + '\''
        print(command_final)
        self.request_id += 1
        ret = subprocess.run(command_final.split(), capture_output=True )
        ret_str = ret.stdout.decode()
        #self.admincli_result = AdminCliResult(ret_str)
        return ret_str

    def commission(self, file, skipParameterRelationErrors=False, shouldBeActivated=False):
        command_data = ''
        command_new = self.base_command.format(self.admincli_id, self.admincli_pw, self.bts_host_ip, self.bts_host_port)
        command_ext = self.command_ext.format(file)
        command_data_ext = self.command_data_commission_dict
        command_data_ext['requestId'] = self.request_id
        command_data_ext['parameters']['parameters']['skipParameterRelationErrors'] = skipParameterRelationErrors
        command_data_ext['parameters']['parameters']['shouldBeActivated'] = shouldBeActivated
        command_data = json.dumps(command_data_ext)
        command_final = command_new + ' ' + command_ext + ' ' +  self.command_data_simple_prefix + '\'' + command_data + '\''
        self.request_id += 1
        print(command_final)
        ret = subprocess.run(command_final, capture_output=True, shell=True)
        ret_str = ret.stdout.decode()
        print(ret_str)

        #self.admincli_result = AdminCliResult(ret_str)
        return ret_str

    def recommission(self, file, skipParameterRelationErrors=False, shouldBeActivated=False):
        command_data = ''
        command_new = self.base_command.format(self.admincli_id, self.admincli_pw, self.bts_host_ip, self.bts_host_port)
        command_ext = self.command_ext.format(file)
        command_data_ext = self.command_data_recommission_dict
        command_data_ext['requestId'] = self.request_id
        command_data_ext['parameters']['parameters']['skipParameterRelationErrors'] = skipParameterRelationErrors
        command_data_ext['parameters']['parameters']['shouldBeActivated'] = shouldBeActivated
        command_data = json.dumps(command_data_ext)
        command_final = command_new + ' ' + command_ext + ' ' +  self.command_data_simple_prefix + '\'' + command_data + '\''
        self.request_id += 1
        print(command_final)
        ret = subprocess.run(command_final, capture_output=True, shell=True)
        ret_str = ret.stdout.decode()
        print(ret_str)

        #self.admincli_result = AdminCliResult(ret_str)
        return ret_str

    def activatePlan(self, deltaDN):
        command_data = ''
        command_new = self.base_command.format(self.admincli_id, self.admincli_pw, self.bts_host_ip, self.bts_host_port)
        command_data_ext = self.command_data_activateplan_dict
        command_data_ext['requestId'] = self.request_id
        command_data_ext['parameters']['parameters']['deltaDN'] = deltaDN
        command_data = json.dumps(command_data_ext)
        command_final = command_new + ' ' + self.command_data_simple_prefix + '\'' + command_data + '\''
        self.request_id += 1
        print(command_final)
        ret = subprocess.run(command_final, capture_output=True, shell=True )
        ret_str = ret.stdout.decode()
        print(ret_str)

        #self.admincli_result = AdminCliResult(ret_str)
        return ret_str

    def generateScf(self, bts_id):
        folder_path = f'./cli_server/data/received/{bts_id}'
        os.makedirs(folder_path, exist_ok=True)
        file_path = os.path.join(folder_path, 'genScf.xml')
        
        command_data = ''
        command_new = self.base_command.format(self.admincli_id, self.admincli_pw, self.bts_host_ip, self.bts_host_port)
        command_ext = self.command_ext_output.format(file_path)
        print("command_ext : ", command_ext)
        
        command_data_ext = self.command_data_generatescf_dict
        command_data_ext['requestId'] = self.request_id
        command_data = json.dumps(command_data_ext)
        
        command_final = command_new + ' ' + command_ext + ' ' +  self.command_data_simple_prefix + '\'' + command_data + '\''
        self.request_id += 1
        
        print(json.dumps(command_final, indent=2))
        print("commnad_final : ", command_final)
        
        ret = subprocess.run(["bash", "-c", command_final], capture_output=True)
        ret_str = ret.stdout.decode()
        print("ret_str : ", ret_str)

        return ret_str

    def softwareUpdate(self, bts_id, input_file_path, shouldActivate=True, overrideIndependentRUSW=True):
        # 기본 명령어 조립
        command_new = self.base_command.format(self.admincli_id, self.admincli_pw, self.bts_host_ip, self.bts_host_port)
        # 실제 zip 파일 경로를 input-file에 넣음
        command_ext = self.command_ext.format(input_file_path)

        # dict 복사 후 값 주입
        command_data_ext = self.command_data_softwareupdate_dict.copy()
        command_data_ext["requestId"] = self.request_id
        command_data_ext["parameters"]["parameters"]["shouldActivate"] = shouldActivate
        command_data_ext["parameters"]["parameters"]["overrideIndependentRUSW"] = overrideIndependentRUSW

        self.request_id += 1
        # JSON 문자열로 변환
        command_data = json.dumps(command_data_ext)

        # 최종 명령어 조합
        command_final = f"{command_new} {command_ext} {self.command_data_simple_prefix}'{command_data}'"

        print("[AdminCLI] 실행 명령어:")
        print(command_final)

        ret = subprocess.run(command_final, capture_output=True, shell=True)
        stdout_str = ret.stdout.decode()
        stderr_str = ret.stderr.decode()

        print("[AdminCLI] 결과 (stdout):")
        print(stdout_str)

        if stderr_str:
            print("[AdminCLI] 오류 내용 (stderr):")
            print(stderr_str)

        return stdout_str + ("\n[stderr]\n" + stderr_str if stderr_str else "")

    def getBtsIpFromNaQuery(self, bts_id: str) -> str:
        try:
            bin_path = "./bin/na_query/na_query"
            config_path = os.getcwd() + "/bin/na_query/na_query.toml"

            print(f"[디버그] 실행 경로: {bin_path}")
            print(f"[디버그] 설정 파일: {config_path}")
            print(f"[디버그] bts id: {bts_id}")
            print(f"[디버그] 현재 경로: {os.getcwd()}")

            command_final = bin_path + " --config-file " + config_path + " get-bts-ip " + str(bts_id)
            print(command_final)

            ret = subprocess.run(command_final.split(), capture_output=True)
            ret_str = ret.stdout.decode()
            print(ret_str)

            nq_ret = NqQueryResult(ret_str)
            query = nq_ret.getValue("query")
            result = nq_ret.getValue("result")

            print(f"[디버그] na_query 결과: query={query}, result={result}")
            return result

        except Exception as e:
            print(f"[디버그] 예외 발생: {str(e)}")

            # 테스트용 임시 IP 반환
            return "4.5.13.5"
        
      # tomllib 대신 toml 사용 중인 경우

    def executeBtsIntegration(self, bts_id: str, ver: str, mr: str, ne_name: str, bts_ip: str) -> tuple[bool, str]:
        self.ws_manager = WsManager()
        try:
            bin_path = "./bin/na_query/na_query"
            config_path = os.path.join(os.getcwd(), "bin/na_query/na_query.toml")

            with open(config_path, "r", encoding="utf-8") as f:
                config_data = toml.load(f)

            ems_data = config_data.get("ems", [])[0] if config_data.get("ems") else None
            if not ems_data:
                return False, "[오류] na_query.toml 파일에 EMS 정보가 없습니다."

            ems = ems_data.get("alias", "")

            # na_query 실행 커맨드 구성 (사용자 예시와 동일 형태)
            command = [
                bin_path, "--config-file", config_path,
                "exe-bts-int",
                "--bts-id", bts_id,
                "--ver", ver,
                "--ems", ems,
                "--mr", mr,
                "--ne-ip", bts_ip,
                "--ne-name", ne_name
                # 필요 시 "--http", "8080", "--https", "8443" 추가 가능 (기본값이면 생략)
            ]

            print("[DEBUG] 실행 명령어:", " ".join(command))

            ret = subprocess.run(command, capture_output=True)
            output = ret.stdout.decode() + ret.stderr.decode()
            print("[DEBUG] 결과:", output)

            nq_ret = NqQueryResult(output)
            query = nq_ret.getValue("query")
            result = nq_ret.getValue("result")
            print(f"[디버그] na_query 결과: query={query}, result={result}")

            if query == "OK":
                return True, f"BTS {bts_id} integration 성공 → {result}"
            else:
                return False, f"BTS {bts_id} integration 실패 → {result}"

        except Exception as e:
            print(f"[예외] {e}")
            return False, f"예외 발생: {e}"
        
    def executeBtsDeintegration(self, bts_id: str) -> tuple[bool, str]:
        self.ws_manager = WsManager()
        try:
            bin_path = "./bin/na_query/na_query"
            config_path = os.path.join(os.getcwd(), "bin/na_query/na_query.toml")

            with open(config_path, "r", encoding="utf-8") as f:
                config_data = toml.load(f)

            ems_data = config_data.get("ems", [])[0] if config_data.get("ems") else None
            if not ems_data:
                return False, "[오류] na_query.toml 파일에 EMS 정보가 없습니다."

            ems = ems_data.get("alias", "")

            # na_query 실행 커맨드 구성 (deintegration 전용)
            command = [
                bin_path, "--config-file", config_path,
                "exe-bts-deint",
                "--bts-id", bts_id,
                "--ems", ems
            ]

            print("[DEBUG] 실행 명령어:", " ".join(command))

            ret = subprocess.run(command, capture_output=True)
            output = ret.stdout.decode() + ret.stderr.decode()
            print("[DEBUG] 결과:", output)

            nq_ret = NqQueryResult(output)
            query = nq_ret.getValue("query")
            result = nq_ret.getValue("result")
            print(f"[디버그] na_query 결과: query={query}, result={result}")

            if query == "OK":
                return True, f"BTS {bts_id} deinte 성공 → {result}"
            else:
                return False, f"BTS {bts_id} deinte 실패 → {result}"

        except Exception as e:
            print(f"[예외] {e}")
            return False, f"예외 발생: {e}"

class AdminCliResult:
    retStr = None
    json_data = None
    recommission_keys = ["CLI LOG", "requestMessage", "commissioningResult", "activationResult", "indicationDistName"]
    commission_keys = ["CLI LOG", "requestMessage", "commissioningResult", "deltaDn"]

    def __init__(self, in_str):
        self.json_data = self.convertStrToJson(in_str)

    def convertStrToJson(self, in_str):

        json_objects = self.extract_json_blocks(in_str)
        # 결과 출력
        for i, obj in enumerate(json_objects, 1):
            print(f"--- JSON Object {i} ---")
            print(json.dumps(obj, indent=2))
        return json_objects

    def getValue(self, key):
        value = None
        for data in self.json_data:
            current = data
            for key in self.keys:
                value = current.get(key, {})
        return value

    def find_json_with_key(self, target_key, json_list=json_data):
        if json_list is None:
            json_list = self.json_data

        results = []
        for data in json_list:
            stack = [(data, [])]

            while stack:
                current, path = stack.pop()

                if isinstance(current, dict):
                    for key, value in current.items():
                        current_path = path + [key]
                        if key == target_key:
                            results.append((current_path, value))
                        stack.append((value, current_path))

                elif isinstance(current, list):
                    for idx, item in enumerate(current):
                        current_path = path + [f"[{idx}]"]
                        stack.append((item, current_path))

        return results

    def extract_json_blocks(self, text):
        blocks = []
        brace_level = 0
        buffer = ''
        in_json = False

        for line in text.splitlines():
            line = line.strip()
            if line.startswith('CLI LOG:'):
                line = line[len('CLI LOG:'):].strip()
            if '{' in line:
                in_json = True
            if in_json:
                buffer += line + '\n'
                brace_level += line.count('{') - line.count('}')
                if brace_level == 0:
                    try:
                        parsed = json.loads(buffer)
                        blocks.append(parsed)
                    except json.JSONDecodeError:
                        pass  # skip invalid JSON blocks
                    buffer = ''
                    in_json = False

        return blocks

class NqQueryResult:
    def __init__(self, in_str: str):
        self.orgStr = in_str
        self.query, self.result = self.extract_query_result(in_str)

    def getValue(self, key: str):
        if key == 'query':
            return self.query
        elif key == 'result':
            return self.result
        return None

    def extract_query_result(self, text: str):
        # $QUERY / $RESULT 형식 시도
        query_match = re.search(r"\$QUERY\s*=\s*(\S+)", text)
        result_match = re.search(r"\$RESULT\s*=\s*(\S+)", text)

        query_value = query_match.group(1).strip(" ;") if query_match else None
        result_value = result_match.group(1).strip(" ;") if result_match else None

        # 둘 다 없으면 fallback: 그냥 IP 한 줄일 경우
        if not result_value:
            fallback = text.strip()
            if re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", fallback):
                result_value = fallback

        return query_value, result_value

def main():
    ws_mgr = WsManager()
    ws_mgr.setActive(20000)
    ws = getWorkspace()
    ws.set("bts_ip", "8.8.8.8")

    ad_interface = AdminCliInterface()
    ad_interface.getBtsIpFromNaQuery('1234')
 #   ad_interface.generateScf()

    file_path = '/home/cloai/admincli_commission_log'

    #with open(file_path, 'r') as file:
    #    file_content = file.read()

    #ret = AdminCliResult(file_content)
    #obj = ret.find_json_with_key("distName")

    ret = NqQueryResult("08:51:01.951  ERROR    $QUERY = OK;  $RESULT = 10.10.10.10  for BTS-1234        ")
    print(ret.getValue('query'), ret.getValue('result'))
    #print(obj)


if __name__ == "__main__":
    main()
