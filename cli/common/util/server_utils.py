import os
import base64
import json
import xml.etree.ElementTree as ET
from datetime import datetime

from cli.settings import grpc_stub
from proto import message_pb2
from cli.settings import is_debug

def save_to_server(self, output_path=None, content=None, filename=None, purpose=""):
    """
    서버에 파일 또는 문자열 데이터를 저장합니다.
    - command는 항상 'saveFile'로 고정
    - payload는 "purpose||filename||base64(content)" 형태
    """
    try:
        if output_path:
            if not os.path.exists(output_path):
                self.perror(f"[오류] 저장할 파일이 존재하지 않습니다: {output_path}")
                return
            filename = filename or os.path.basename(output_path)
            with open(output_path, "r", encoding="utf-8") as f:
                content = f.read()
        elif content and filename:
            pass
        else:
            self.perror("[오류] 저장할 파일(output_path) 또는 content+filename 조합이 필요합니다.")
            return

        encoded = base64.b64encode(content.encode("utf-8")).decode("utf-8")
        payload = f"{purpose}||{filename}||{encoded}"

        # if is_debug:
        #     print(f"[디버그] 서버 전송 준비 완료: purpose={purpose}, filename={filename}")

        request = message_pb2.Request(command="saveFile", payload=payload)
        response = grpc_stub.SendCommand(request)

        if response.success:
            if is_debug:
                self.poutput(f"[서버 저장 완료] ({purpose}) {filename} → {response.result}")
        else:
            self.perror(f"[서버 오류] ({purpose}) {filename} → {response.result}")

    except Exception as e:
        self.perror(f"[서버 전송 실패] ({purpose}) {filename} → {e}")



def load_from_server(filename: str, filetype: str = "json", purpose: str = "generic"):
    """
    서버에서 특정 목적(purpose)에 따라 파일을 읽어 base64 decode 후 파싱합니다.
    filetype: json, xml, text, binary
    purpose: prodmap, template, cli, log 등 (서버가 해석)
    """
    try:
        if is_debug:
            print("load = ", filename)
            print("purpose = ", purpose)
        payload = f"{purpose}::{filename}"
        request = message_pb2.Request(command="getFile", payload=payload)
        response = grpc_stub.SendCommand(request)

        if not response.success:
            print(f"[서버 오류] {response.result}")
            return None

        decoded = base64.b64decode(response.result.encode("utf-8"))

        if filetype == "json":
            return json.loads(decoded.decode("utf-8"))
        elif filetype == "xml":
            return ET.ElementTree(ET.fromstring(decoded.decode("utf-8")))
        elif filetype == "text":
            return decoded.decode("utf-8")
        elif filetype == "binary":
            return decoded
        else:
            print(f"[클라 경고] 지원하지 않는 파일 형식: {filetype}")
            return None
    except Exception as e:
        print(f"[클라 오류] load_from_server 실패: {e}")
        return None

def delete_from_server(self, filename=None, purpose=""):
    """
    서버에서 파일을 삭제합니다.
    - command는 'deleteFile'
    - payload는 "purpose||filename" 형태
    """
    try:
        if not filename:
            self.perror("[오류] 삭제할 파일명이 필요합니다.")
            return

        payload = f"{purpose}||{filename}"

        if is_debug:
            print(f"[디버그] 삭제 요청: purpose={purpose}, filename={filename}")

        request = message_pb2.Request(command="deleteFile", payload=payload)
        response = grpc_stub.SendCommand(request)

        if response.success:
            self.poutput(f"[서버 삭제 완료] ({purpose}) {filename} → {response.result}")
        else:
            self.perror(f"[서버 오류] ({purpose}) {filename} → {response.result}")

    except Exception as e:
        self.perror(f"[서버 삭제 실패] ({purpose}) {filename} → {e}")
