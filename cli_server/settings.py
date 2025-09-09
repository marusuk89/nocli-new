import os
import sys
import argparse
from dotenv import load_dotenv

# ─── argparse로 --env 인자 처리 ───────────────
parser = argparse.ArgumentParser()
parser.add_argument("--env", type=str, default=".env", help="불러올 환경설정 파일 경로")
args, unknown = parser.parse_known_args()
env_file = args.env

# .env 파일 로드
load_dotenv(dotenv_path=env_file)

# argparse로 인해 sys.argv가 오염되지 않도록 원상복구
sys.argv = [sys.argv[0]] + unknown

# ─── 유틸 함수 ────────────────────────────────
def str2bool(s):
    return str(s).lower() in ("true", "1", "yes")

# ─── 환경 설정 ────────────────────────────────
ENV_TYPE = os.getenv("ENV_TYPE", "DEV").upper()
IS_PROD = ENV_TYPE == "PROD"
USE_TLS = str2bool(os.getenv("USE_TLS", "True"))
GRPC_BIND_ADDRESS = os.getenv("SERVER_GRPC_BIND_ADDRESS", "0.0.0.0:50051")

# ─── BASE_DIR 설정 (PyInstaller 대응) ─────────
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ─── 경로 설정 함수 ───────────────────────────
def get_env_path(dev_key: str, prod_key: str):
    return os.getenv(prod_key) if IS_PROD else os.getenv(dev_key)

# ─── 인증서 경로 처리 ─────────────────────────
cert_rel_path = get_env_path("SERVER_CERT_PATH", "PROD_SERVER_CERT_PATH")
key_rel_path = get_env_path("SERVER_KEY_PATH", "PROD_SERVER_KEY_PATH")

CERT_PATH = os.path.join(BASE_DIR, cert_rel_path)
KEY_PATH = os.path.join(BASE_DIR, key_rel_path)

# ─── TLS 파일 존재 검사 ──────────────────────
if USE_TLS:
    if not os.path.exists(CERT_PATH):
        raise FileNotFoundError(f"[서버] 인증서 파일 없음: {CERT_PATH}")
    if not os.path.exists(KEY_PATH):
        raise FileNotFoundError(f"[서버] 키 파일 없음: {KEY_PATH}")
