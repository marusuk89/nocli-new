# 작업 기록 요약 (2025-05-02)

## 1. Commit Formula 적용 방식 개선

- 사용자가 CLI에서 입력하는 값을 실제 장비에서 사용하는 내부값으로 변환하기 위한 `formula` 구조 반영.
- `param_dict.json`에 정의된 수식을 적용하여 변환.
- 다음과 같은 `-t` 옵션을 통해 공식 적용 방식 제어:
  - `-t 1`: formula 1회 적용 (e.g., json → xml 변환)
  - `-t 2`: formula 2회 적용 (e.g., ui → json → xml)
  - `-t r`: formula 역변환 적용 (e.g., xml → json)
- `commit` 및 `commit-cell` 명령어에 모두 적용됨.
- 변환된 translated XML은 서버에도 저장됨.

---

## 2. Init-stp 계열 명령어 추가 및 구성

### `do_dest_bts`
- BTS ID 설정과 동시에 `na_query` 명령어를 실행하여 BTS IP 자동 조회 및 설정.
- 설정 성공/실패 여부를 결과로 응답.

### `do_check_ssh`
- 설정된 BTS IP로 SSH 접속이 가능한지 확인.
- `subprocess.run()`을 통해 실제 접속 시도하며, 패스워드 없이 가능한 설정이 필요함.
- 로컬 환경에서 정상 테스트 완료.

### `do_update_sw_ver`
- NetAct 서버 URL을 기반으로 장비에 SW 업데이트 요청.
- 파라미터: `--url`, `--no-activate`, `--override`.

### `do_check_soam`
- SOAM 상태 확인 명령 전송 구조 구축.
- 명령 구조는 완료, 실제 admin-cli 연동은 후속 구현 예정.

---

## 3. 명령어 히스토리 저장 기능 강화

- 모든 `do_*()` 명령어 실행 시 기록 자동 저장.
- 저장 포맷: `[시간] | [프롬프트] | [입력한 명령어] | RESULT: OK/NOK`
- 파일 위치: `data/history/command_history.log`
- `onecmd_plus_hooks()` 함수 내에서 자동 감지 및 저장 처리.

---

## 4. `commit-cell` 사용 제한 기능 도입

- 특정 CLI 진입점에서는 `commit-cell` 명령어를 제한하기 위해 인자 도입:
  - `allow_commit_diff=False`일 경우 해당 명령어 차단.
- 설정 예시:
  ```python
  cli = InitCLI(allow_commit_diff=True)  # 허용
  cli = InitCLI(allow_commit_diff=False) # 제한
  ```
- 기본값은 `False`로 제한됨. `config/init-cell`에서만 `True`.

---

## 5. MO 중복 생성 방지

- `_enter_or_create_mo()`에서 이미 존재하는 `distName`인 경우에는 `생성됨` 로그 출력 생략.
- XML 구조상 중복 생성 방지 처리.

---
