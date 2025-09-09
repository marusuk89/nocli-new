from concurrent import futures
import grpc
import time
from proto import message_pb2_grpc
from cli_server.core.handler.command_handler import CommandServiceServicer
from cli_server import settings  # 서버 설정 가져오기

def cli_serve():
    try:
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        message_pb2_grpc.add_CommandServiceServicer_to_server(CommandServiceServicer(), server)

        if settings.USE_TLS:
            print("[Server] TLS 모드 활성화됨")
            with open(settings.KEY_PATH, "rb") as f:
                private_key = f.read()
            with open(settings.CERT_PATH, "rb") as f:
                certificate_chain = f.read()
            credentials = grpc.ssl_server_credentials(((private_key, certificate_chain),))
            server.add_secure_port(settings.GRPC_BIND_ADDRESS, credentials)
            print("[Server] gRPC (TLS) listening on", settings.GRPC_BIND_ADDRESS)
        else:
            server.add_insecure_port(settings.GRPC_BIND_ADDRESS)
            print("[Server] gRPC (insecure) listening on", settings.GRPC_BIND_ADDRESS)

        time.sleep(1)
        server.start()
        server.wait_for_termination()

    except Exception as e:
        print("[Server] 예외 발생:", e)

if __name__ == "__main__":
    cli_serve()