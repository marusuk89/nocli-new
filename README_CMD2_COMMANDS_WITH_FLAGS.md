# CMD2 CLI 명령어 요약


## 서버 설정

| 명령어 | 설명 | 예시 및 플래그 |
|--------|------|----------------|

| `dest-bts` | BTS 서버 대상 설정 |  |
| `dest-bts-ip` | BTS 서버 IP 확인 |  |
| `check-ping` | BTS와의 ping 연결 확인 |  |
| `update-sw-ver` | BTS 소프트웨어 버전 업데이트 | --no-activate, --no-override 플래그 사용 가능<br>예: `update-sw-ver 12345 --url http://10.1.1.1:443/path/ --no-activate` |
| `check-soam` | BTS 소프트웨어 상태 확인 |  |
| `check-ssh` | SSH 연결 확인 |  |
| `gethwinfo` | BTS 하드웨어 정보 확인 |  |

## 파일 처리

| 명령어 | 설명 | 예시 및 플래그 |
|--------|------|----------------|

| `dnload-bts-cfg` | BTS 설정 파일 다운로드부터 역변환 후 세팅까지 |  |
| `dnload-bts-cfg-raw` | 설정 파일 원본 다운로드 |  |
| `apply-bts-cfg` | 설정 파일 적용 (비활성화 상태) |  |
| `act-bts-cfg` | 설정 파일 적용 및 활성화 | --skip 플래그 사용 가능<br>예: `act-bts-cfg --skip` |
| `activateplan` | 지정된 delta plan 활성화 |  |
| `commission` | 초기 BTS 설정 적용 |  |
| `recommission` | 설정 파일 재적용 |  |

## 커밋

| 명령어 | 설명 | 예시 및 플래그 |
|--------|------|----------------|

| `commit-all` | 전체 XML 저장 및 CLI 스크립트 생성 | -m, -t 플래그 사용 가능<br>예: `commit-all -m "테스트" -t r` |
| `commit-diff` | 차이점만 저장 및 전송 | -m, -t 플래그 사용 가능<br>예: `commit-diff -m "셀 전용" -t 1` |
| `commit` | 2단계 공식 적용하여 커밋 | -m 플래그 사용 가능<br>예: `commit -m "최종"` |
| `show-key` | 현재 세션의 task key 출력 |  |

## 설정

| 명령어 | 설명 | 예시 및 플래그 |
|--------|------|----------------|

| `set-cfg-scf` | SCF XML 템플릿 로드 |  |
| `set-ru-type` | RU 타입 지정 |  |
| `set-cfg-tmpl` | 참조 템플릿 반영 및 적용 |  |

## 삭제

| 명령어 | 설명 | 예시 및 플래그 |
|--------|------|----------------|

| `no-mo` | MO 삭제 |  |
| `no-pa` | 파라미터 삭제 |  |
| `no-tgt-bts` | BTS 초기화 및 작업 취소 |  |

## 조회

| 명령어 | 설명 | 예시 및 플래그 |
|--------|------|----------------|

| `show-cfg` | 현재 또는 지정된 MO 파라미터 출력 | -a, -r, -o 옵션 사용 가능<br>예: `show-cfg -a` |
| `show-glb` | 서버 저장 파일 목록 확인 | --ext, --limit, --sort 사용 가능<br>예: `show-glb --ext xml --sort time` |
| `show-sib` | 형제 MO의 파라미터 확인 | -a, -r, -o 사용 가능<br>예: `show-sib 2 -r` |
| `show-can-mo` | 가능한 하위 MO 목록 확인 |  |
| `show-can-pa` | 현재 MO에서 가능한 파라미터 목록 | -a 플래그 사용 가능<br>예: `show-can_pa -a` |
| `show-user-input` | 사용자 입력 이력 출력 |  |

## 파라미터

| 명령어 | 설명 | 예시 및 플래그 |
|--------|------|----------------|

| `add-auto_pa` | MO에 파라미터 자동 추가 | -a 플래그 사용 가능<br>예: `add-auto_pa -a` |
| `list` | 리스트 파라미터 추가 또는 수정 |  |
| `auto-config` | RU 타입 기반 자동 MO 생성 | --rmod 옵션 사용 가능 (CHANNEL 전용)<br>예: `auto-config CHANNEL * --rmod 3` |

## 도구

| 명령어 | 설명 | 예시 및 플래그 |
|--------|------|----------------|

| `scf-to-txt` | XML을 CLI 스크립트(.txt)로 변환 저장 |  |
| `excel-to-dict-formula` | 엑셀로 formula dict 생성 |  |
| `excel-to-dict-mo` | 엑셀로 mo/파라미터 dict 생성 |  |
| `excel-to-dict-mo-1000` | 엑셀 dict 생성 (1000개 제한) | 1000개 제한 있음<br>예: `excel-to-dict-mo-1000 my.xlsx` |
| `run-script` | 스크립트 파일 실행 |  |

## 탐색

| 명령어 | 설명 | 예시 및 플래그 |
|--------|------|----------------|

| `exit` | 현재 계층에서 한 단계 위로 이동 |  |