
# Part 1
## admincli_commands
각 명령어는 admin-cli를 통해서 수행되거나 참고되는 함수들입니다.

### 🔹 `dnload-bts-cfg`

**설명**: BTS 설정 파일을 다운로드한 뒤, json-value → ui-value로 복원하여 환경 설정을 완료합니다.

**자동 수행 단계**:

1. `dnload-bts-cfg` (json-value 다운로드)
2. `set-cfg-scf genScf` (ref 설정)
3. `commit-all -t r` (json → ui-value 변환 저장)
4. `set-cfg-scf <ui-value.xml>` (ref 갱신)
5. `_set_du_type_from_smod()` 호출로 DU 타입 자동 설정

**사용법**:

```bash
dnload-bts-cfg
```

**Flags**: 없음

---

### 🔹 `apply-bts-cfg`

**설명**: 최근 커밋된 SCF 파일을 적용(commission)하되, 활성화(activation)는 하지 않습니다.

**사용법**:

```bash
apply-bts-cfg
```

**Flags**: 없음

---

### 🔹 `act-bts-cfg`

**설명**: 최근 커밋된 SCF 파일을 적용(commission)하고 즉시 활성화합니다.

**사용법**:

```bash
act-bts-cfg [--skip]
```

**Flags**:

* `--skip`: 유효성 검사를 생략합니다.

---

### 🔹 `apply-bts-cfg-commission`

**설명**: 커밋된 파일을 `commission` 명령어로 적용합니다. 내부적으로 `activate=False`로 지정되어 있어 활성화는 되지 않습니다.

**사용법**:

```bash
apply-bts-cfg-commission
```

**Flags**: 없음

---

### 🔹 `act-bts-cfg-commission`

**설명**: 커밋된 파일을 `commission` 명령어로 적용하고, `activate=True`로 설정하여 즉시 활성화까지 수행합니다.

**사용법**:

```bash
act-bts-cfg-commission [--skip]
```

**Flags**:

* `--skip`: 유효성 검사를 생략합니다.

---

### 🔹 `commission`

**설명**: 지정된 파일을 commission 처리합니다.

**사용법**:

```bash
commission <filename> [--skip] [--activate]
```

**Flags**:

* `--skip` (bool): 유효성 검사 생략 여부
* `--activate` (bool): 활성화 여부

---

### 🔹 `recommission`

**설명**: 기존의 설정 파일을 recommission합니다 (적용 방식은 `commission`과 유사하되 command는 다름).

**사용법**:

```bash
recommission <filename> [--skip] [--activate]
```

**Flags**:

* `--skip`: 유효성 검사 생략
* `--activate`: 활성화 여부

---

### 🔹 `activateplan`

**설명**: delta 파일을 기반으로 플랜을 활성화합니다.

**사용법**:

```bash
activateplan <deltaDN>
```

**Flags**: 없음

---

### 🔹 `gethwinfo`

**설명**: 서버로부터 하드웨어 정보를 가져옵니다.

**사용법**:

```bash
gethwinfo
```

**Flags**: 없음

---

### 🔹 내부 유틸: `prepare_dummy_flag`

**설명**: dummy MO가 존재하는지를 확인하는 최소 동작. `auto-comm gen-script`의 내부 준비 작업 전용입니다.

**사용법**:

```python
self.prepare_dummy_flag("130126")
```

**Flags**: 해당 없음 (내부 함수)

# Part 2
## autocomm_commands

각 명령어는 `auto-comm` 관련 CLI 흐름을 구성하기 위한 목적으로 사용됩니다. 특히 BTS / CELL / MOD의 스크립트 생성 및 실행, 상태 확인, 템플릿 적용 등 자동화에 필요한 주요 기능을 포함합니다.

---

## 📘 명령어 목록

### 🔹 `gen-script <엑셀파일명>`
**설명**: INIT-BTS / INIT-CELL / INIT-MOD CLI 스크립트를 엑셀에서 생성합니다.  
**사용법**:
```
gen-script DU정보.xlsx
```

---

### 🔹 `show-script-header <스크립트파일명>`
**설명**: 스크립트의 HEADER 영역(계층 이동 명령어들)을 출력합니다.  
**사용법**:
```
show-script-header 100.DU130120_initbts_pass.cli
```

---

### 🔹 `autocomm-run-script <스크립트파일명>`
**설명**: 스크립트 파일의 BODY 영역 명령어들을 실행합니다.  
**사용법**:
```
autocomm-run-script 100.DU130120_initbts_pass.cli
```

---

### 🔹 `show-bts-entry <엑셀파일명>`
**설명**: 각 BTS의 현재 SCF 버전과 엑셀에 정의된 목표 버전을 비교하여 출력합니다.  
**사용법**:
```
show-bts-entry DU정보.xlsx
```

---

## 📌 비고

- `gen-script` 명령어는 내부적으로 `_parse_excel_rows_init_bts`, `_parse_excel_rows_init_cell`, `_parse_excel_rows_init_mod` 등을 통해 각 시트 정보를 해석합니다.
- 스크립트는 날짜별 디렉토리 (`data/autocomm/YYYYMMDD/`)에 자동 저장됩니다.
- `autocomm-run-script`는 RPA 자동화 실행에서 BODY 루프용으로만 사용되며, 계층 이동은 RPA가 직접 실행합니다.

# Part 3
## commit_commands

각 명령어는 commit 기반의 XML 저장 흐름을 제어하기 위한 목적을 가지고 있습니다.  
특히 full-commit, 변경사항 기반 commit, 파라미터 기반 commit을 구분하여 사용할 수 있습니다.

---

## 📘 명령어 목록

### 🔹 `commit-all [-t <TYPE>]`
**설명**: 현재 작업된 모든 MO를 XML 기준으로 저장(commit)합니다.  
**사용법**:
```
commit-all -t 1
```

**옵션**:
- `-t 1`: UI → JSON
- `-t 2`: UI → Internal
- `-t r`: Internal → UI (역변환)

---

### 🔹 `commit-diff [-t <TYPE>]`
**설명**: 현재 상태와 비교하여 변경된 MO만 저장(commit)합니다.  
**사용법**:
```
commit-diff -t 1
```

**옵션**:
- `-t 1`: UI → JSON
- `-t 2`: UI → Internal
- `-t r`: Internal → UI (역변환)

---

### 🔹 `commit-diff-para [-t <TYPE>]`
**설명**: 파라미터 변경을 포함한 diff 기반 commit입니다.  
create/update를 구분하여 변경된 파라미터만 저장합니다.  
**사용법**:
```
commit-diff-para -t 2
```

**옵션**:
- `-t 1`: UI → JSON
- `-t 2`: UI → Internal
- `-t r`: Internal → UI (역변환)

---

### 🔹 `show-commit`
**설명**: 현재 commit된 XML 파일의 경로를 출력합니다.  
**사용법**:
```
show-commit
```

---

### 🔹 `clear-commit`
**설명**: 현재 commit 상태를 모두 초기화합니다.  
**사용법**:
```
clear-commit
```

---

## 📌 비고

- `commit-diff-para`는 기존 `commit-diff`에서 파라미터 비교 로직을 추가한 확장 명령어입니다.
- `-t` 옵션을 통해 변환 단계를 명시하지 않으면 기본값이 적용될 수 있습니다.
- commit된 XML은 실제 장비 반영 전 확인 용도로도 활용됩니다.

# part 4
## set_commands

각 명령어는 `DU/RU 유형 설정`, `템플릿 적용`, `파라미터 지정` 등 장비 구성에 필요한 설정 작업을 수행하는 CLI 명령어들입니다.

---

## 📘 명령어 목록

### 🔹 `set-cfg-scf <파일명>`
**설명**: 서버에서 SCF 템플릿 XML 파일을 받아 로드하고 내부 XML 트리에 반영합니다.  
**사용법**:
```
set-cfg-scf genScf.xml
```

---

### 🔹 `set-du-type <DU10 | DU20>`
**설명**: DU 타입을 설정하고, 관련 파라미터 사전 및 룰북을 로드합니다.  
**사용법**:
```
set-du-type DU10
```

---

### 🔹 `set-ru-type <RU_TYPE> [--band <850|2100|2600>]`
**설명**: RU 타입을 설정하며, 필요 시 RU 전용 템플릿을 불러와 룰북을 업데이트합니다.  
**사용법**:
```
set-ru-type FHCG --band 850
```

---

### 🔹 `set-ru-para sector_3 [true|false]`
**설명**: RU 파라미터 중 sector_3 설정을 변경합니다. 기본값은 false이며 true 설정 시 다른 템플릿이 사용될 수 있습니다.  
**사용법**:
```
set-ru-para sector_3 true
```

---

### 🔹 `set-cfg-tmpl <파일명>.cli`
**설명**: CLI 템플릿 파일을 XML로 파싱한 뒤 현재 XML 트리에 맞게 매핑하고 실행합니다.  
**사용법**:
```
set-cfg-tmpl nok_lte_ru_DU10.cli
```

---

## 📌 비고

- `set-du-type`을 설정하면 DU 유형 기반으로 파라미터 사전이 로드됩니다.
- `set-ru-type`은 내부적으로 템플릿 파일을 불러와 `rulebook`을 자동 갱신하며, `FHCG` 타입만 밴드 옵션 사용이 가능합니다.
- `set-cfg-tmpl`은 CLI 템플릿 파싱 후 MO-ID 매핑과 누락된 상위 경로 보정까지 수행한 뒤 CLI 명령어로 실행됩니다.
- 모든 설정 명령어는 내부적으로 디버그 모드에서 출력 로그를 제공합니다 (`is_debug = True` 시).

# part 5
## setup_commands

각 명령어는 `setup` 관련 CLI 초기 설정 및 연결 상태 확인을 위한 목적으로 사용됩니다. 특히 dest-bts IP 연결, ping 체크, SSH/소프트웨어 상태 확인 및 버전 업데이트 등 기본 통신 및 상태 점검에 활용됩니다.

---

## 📘 명령어 목록

### 🔹 `dest-bts <BTS_ID>`
**설명**: BTS ID로 서버와 연결 시도 후 IP 조회 및 설정을 수행합니다.  
**사용법**:
```
dest-bts 130126
```

---

### 🔹 `dest-bts-ip <IP주소>`
**설명**: 수동으로 BTS의 IP 주소를 설정합니다.  
**사용법**:
```
dest-bts-ip 4.5.12.92
```

---

### 🔹 `check-ping <BTS_ID>`
**설명**: 지정된 BTS ID에 대해 ping 테스트를 수행합니다.  
**사용법**:
```
check-ping 130126
```

---

### 🔹 `update-sw-ver <BTS_ID> --file <파일명> [--no-activate] [--no-override]`
**설명**: BTS의 소프트웨어를 지정된 ZIP 파일로 업데이트합니다.  
**플래그 설명**:
- `--file`: 업로드할 ZIP 파일명 (필수)
- `--no-activate`: 업데이트 후 활성화를 생략합니다.
- `--no-override`: 독립된 RU SW를 무시하지 않도록 설정합니다.  
**사용법**:
```
update-sw-ver 130126 --file swfile.zip --no-activate
```

---

### 🔹 `check-soam <BTS_ID>`
**설명**: 대상 BTS의 SOAM (운영 및 유지관리 상태)을 확인합니다.  
**사용법**:
```
check-soam 130126
```

---

### 🔹 `check-ssh <BTS_ID>`
**설명**: 대상 BTS의 SSH 접근성 및 연결 상태를 확인합니다.  
**사용법**:
```
check-ssh 130126
```

---

## 📌 비고

- `dest-bts`, `check-ping`은 사전 통신 확인 및 연결상태 점검을 위한 선행 명령어입니다.
- `update-sw-ver`는 병렬 처리 가능성이 있는 멀티 업데이트 작업의 기반 명령어입니다.

# part 6
## show_commands

`show-*` 계열 명령어는 현재 XML 기반 구성 상태, 파라미터, 하위 MO, 스크립트 헤더 등을 시각적으로 점검하거나 확인하는 데 사용됩니다.  
SCF 상태나 사용자가 입력한 명령 이력을 직접 점검할 수 있도록 지원합니다.

---

## 📘 명령어 목록

### 🔹 `show-user-input`
**설명**: 사용자가 직접 입력한 명령 이력을 확인합니다.  
**사용법**:
```
show-user-input
```

---

### 🔹 `show-cfg [-a | -r] [-m <MO>]`
**설명**: 현재 계층 또는 지정된 MO 기준으로 XML에 설정된 파라미터 값을 출력합니다.  
**옵션**:
- `-a`, `--all`: 모든 파라미터 출력 (기본)
- `-r`, `--required`: 필수 파라미터만 출력
- `-m`, `--mo <MO>`: 특정 MO부터 하위까지 출력

---

### 🔹 `show-glb [--ext xml|cli|all] [--limit N] [--sort time|name|key]`
**설명**: 서버의 `data/received/`에 저장된 파일 목록을 출력합니다.  
**옵션**:
- `--ext`: 확장자 필터링 (기본: all)
- `--limit`: 출력 개수 제한
- `--sort`: 정렬 기준 지정

---

### 🔹 `show-key`
**설명**: 현재 세션의 task key를 출력합니다.  
**사용법**:
```
show-key
```

---

### 🔹 `show-sib <ID> [-r|-o|-a]`
**설명**: 형제 MO 중 특정 ID를 갖는 MO의 파라미터를 출력합니다.  
**옵션**:
- `-r`: 필수 파라미터만 출력
- `-o`: 선택 파라미터만 출력
- `-a`: 모든 파라미터 출력

---

### 🔹 `show-can-mo`
**설명**: 현재 MO에서 생성 가능한 하위 MO 목록을 출력합니다.  
**사용법**:
```
show-can-mo
```

---

### 🔹 `show-can-pa [-a|-r]`
**설명**: 현재 MO 기준으로 입력 가능한 파라미터 목록을 출력합니다.  
**옵션**:
- `-a`: 전체 파라미터
- `-r`: 필수 파라미터

---

### 🔹 `show-para <파라미터명>`
**설명**: 특정 파라미터를 가진 MO들을 distName 기준으로 조회합니다.  
**사용법**:
```
show-para actCli
```

---

## 📌 비고

- `show-cfg`는 XML에서 직접 값을 추출하며, 계층 또는 dist 기준으로 검색됩니다.
- `show-user-input`은 CLI 작업 중 사용자 직접 입력을 기록한 목록을 보여줍니다.
- `show-glb`는 서버와 연동되어 파일 목록을 반환하며, CLI/SCF 관리에 유용합니다.

# part 7
## tool_commands

각 명령어는 CLI 툴 기능을 담당하며, 주요 스크립트 실행, XML-CLI 변환, 엑셀 파싱 등의 도구 명령어를 포함합니다.

---

## 📘 명령어 목록

### 🔹 `exec-script <스크립트파일명>`
**설명**: CLI 명령어가 담긴 스크립트 파일을 로드하여 자동 실행합니다.  
**사용법**:
```
exec-script 100.DU130120_initbts_pass.cli
```

---

### 🔹 `scf-to-cli <xml파일명>`
**설명**: SCF XML 파일을 CLI 명령어 스크립트로 변환합니다.  
**사용법**:
```
scf-to-cli 2403BTS130120.xml
```

---

### 🔹 `excel-to-dict-formula <엑셀파일명>`
**설명**: 엑셀로부터 파라미터 변환 공식 dict(json)을 생성합니다.  
**사용법**:
```
excel-to-dict-formula 2403_param.xlsx
```

---

### 🔹 `excel-to-dict-mo <엑셀파일명>`
**설명**: 엑셀로부터 MO 및 파라미터 구조 dict(json)을 생성합니다.  
**사용법**:
```
excel-to-dict-mo 2403_param.xlsx
```

---

### 🔹 `rulebook-to-dict <XML파일명>`
**설명**: SCF 룰북 XML 파일을 기반으로 파라미터 dict(json)을 생성합니다.  
**사용법**:
```
rulebook-to-dict DU130120_Rulebook.xml
```

---

### 🔹 `compare-scf <파일A>.xml <파일B>.xml`
**설명**: 두 SCF XML 파일 간의 차이점(MO 존재/변경)을 비교합니다.  
**사용법**:
```
compare-scf A.xml B.xml
```

---

## 📌 비고

- `exec-script`는 내부적으로 커맨드를 파싱하여 자동 실행하며, 오류 로그는 별도로 저장됩니다.
- `excel-to-dict-*` 명령어는 Parameter List 시트를 기반으로 dict(json)을 생성하며, 공식 / MO 구조 추출 목적입니다.
- `compare-scf`는 `data/generated/` 내 XML 파일만 비교 가능합니다.

# part 8
## tree_commands

각 명령어는 CLI에서 MO 트리 구조를 탐색하고, 부모-자식 간 계층 및 경로 추적 기능을 제공합니다.

---

## 📘 명령어 목록

### 🔹 `show-mo-tree <MO명>`
**설명**: 특정 MO의 자식 MO 트리를 시각적으로 출력합니다.  
**사용법**:
```
show-mo-tree RMOD
```

---

### 🔹 `show-parent <MO명>`
**설명**: 주어진 MO가 어떤 부모 MO 계층에 포함되는지를 출력합니다.  
**사용법**:
```
show-parent ANTL
```

---

### 🔹 `show-path <MO명>`
**설명**: 해당 MO의 전체 경로를 distName 형식으로 출력합니다.  
**사용법**:
```
show-path ANTL
```

---

### 🔹 `show-path-by <MO명> <기준MO>`
**설명**: 기준 MO에서 특정 MO까지의 경로를 추적합니다.  
**사용법**:
```
show-path-by ANTL RMOD
```

---

## 📌 비고

- `show-mo-tree`는 계층 구조를 재귀적으로 탐색하여 출력합니다.
- `show-parent`는 내부 구조 정보(`mo_class_parent_map`)에 기반해 결정됩니다.
- `show-path` 및 `show-path-by`는 CLI 구조 내에서 경로 탐색 시 유용합니다.