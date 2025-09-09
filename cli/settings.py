from dotenv import load_dotenv
import os
import sys
import argparse
import grpc
from proto import message_pb2_grpc

# ─── .env 파일 선택 ──────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--env", type=str, default=".env", help="불러올 환경설정 파일 경로")
args, unknown = parser.parse_known_args()

# 지정한 .env 파일을 로드
env_file = args.env
load_dotenv(dotenv_path=env_file)

# cmd2에서 헷갈리지 않게 argv 정리
sys.argv = [sys.argv[0]] + unknown

def str2bool(s):
    return str(s).lower() in ("true", "1", "yes")

# ─── 환경 설정 ───────────────────────
ENV_TYPE = os.getenv("ENV_TYPE", "DEV").upper()
IS_PROD = ENV_TYPE == "PROD"
is_debug = str2bool(os.getenv("IS_DEBUG", "False"))
IS_LOCAL = str2bool(os.getenv("IS_LOCAL", "False"))
USE_TLS = str2bool(os.getenv("USE_TLS", "True"))

# ─── 주소/포트 설정 ─────────────────
host = os.getenv("GRPC_HOST", "localhost")
port = os.getenv("GRPC_PORT", "50051")
GRPC_TARGET = f"{host}:{port}" if not IS_LOCAL else f"localhost:{port}"

# ─── BASE_DIR 설정 (PyInstaller 외부 경로 대응) ─
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ─── 경로 설정 함수 ─────────────────
def get_env_path(dev_key: str, prod_key: str):
    return os.getenv(prod_key) if IS_PROD else os.getenv(dev_key)

# ─── 인증서 경로 처리 ────────────────
cert_rel_path = get_env_path("CERT_PATH", "PROD_CERT_PATH")
CERT_PATH = os.path.join(BASE_DIR, cert_rel_path)

# ─── gRPC 채널 생성 ─────────────────
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
