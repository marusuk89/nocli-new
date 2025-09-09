from ping3 import ping

def check_ping(dest):
    try:
        response = ping(dest)
        if not response:
            return False, f"{dest} is down."
        else:
            return True, f"{dest} is up."
    except Exception as e:
        return False, f"Exception: {e}"

