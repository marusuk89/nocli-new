from dotenv import load_dotenv
import os
import sys
import argparse
import grpc
from proto import message_pb2_grpc

# ─── .env 파일 선택 ──────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--env", type=str, help="불러올 환경설정 파일 경로")
args, unknown = parser.parse_known_args()

# exe 이름 확인 (PyInstaller 빌드 후 실행 파일 이름 기반)
exe_name = os.path.basename(sys.argv[0]).lower()

# 우선순위: 1) --env 옵션, 2) exe 이름 자동 분기
if args.env:
    env_file = args.env
else:
    if "5g" in exe_name:
        env_file = "5G.env"
    elif "4g" in exe_name:
        env_file = "4G.env"
    else:
        raise RuntimeError("환경 파일을 결정할 수 없습니다. --env 옵션을 지정하세요.")

# PyInstaller 실행 환경 고려
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
    ENV_DIR = BASE_DIR   # exe 옆에 env 있다고 가정
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))   # cli/ 기준
    ENV_DIR = os.path.abspath(os.path.join(BASE_DIR, "..")) # repo 루트 기준

env_file = os.path.join(ENV_DIR, env_file)
load_dotenv(dotenv_path=env_file)

# cmd2 등에서 argv 충돌 방지
sys.argv = [sys.argv[0]] + unknown

# ─── 유틸 함수 ──────────────────────────────
def str2bool(s):
    return str(s).lower() in ("true", "1", "yes")

# ─── 환경 변수 파싱 ──────────────────────────
ENV_TYPE = os.getenv("ENV_TYPE", "DEV").upper()
IS_PROD = ENV_TYPE == "PROD"
is_debug = str2bool(os.getenv("IS_DEBUG", "False"))
IS_LOCAL = str2bool(os.getenv("IS_LOCAL", "False"))
USE_TLS = str2bool(os.getenv("USE_TLS", "True"))

# ─── 주소/포트 설정 ──────────────────────────
host = os.getenv("GRPC_HOST", "localhost")
port = os.getenv("GRPC_PORT", "50051")
GRPC_TARGET = f"{host}:{port}" if not IS_LOCAL else f"localhost:{port}"

# ─── 인증서 경로 처리 ────────────────────────
def get_env_path(dev_key: str, prod_key: str):
    return os.getenv(prod_key) if IS_PROD else os.getenv(dev_key)

cert_rel_path = get_env_path("CERT_PATH", "PROD_CERT_PATH")
CERT_PATH = os.path.join(BASE_DIR, cert_rel_path)

# ─── gRPC 채널 생성 ──────────────────────────
if USE_TLS:
    if not os.path.exists(CERT_PATH):
        raise FileNotFoundError(f"[클라] 인증서 파일 없음: {CERT_PATH}")
    with open(CERT_PATH, "rb") as f:
        trusted_certs = f.read()
    credentials = grpc.ssl_channel_credentials(root_certificates=trusted_certs)
    channel = grpc.secure_channel(GRPC_TARGET, credentials)
else:
    channel = grpc.insecure_channel(GRPC_TARGET)

grpc_stub = message_pb2_grpc.CommandServiceStub(channel)
