# CMD2 CLI 명령어 요약

이 문서는 CMD2 기반 CLI 프로젝트에서 사용되는 주요 명령어들을 카테고리별로 정리한 문서입니다.

## 📡 서버 설정
| 명령어 | 설명 |
|--------|------|
| `dest-bts` | BTS 서버 대상 설정 |
| `dest-bts-ip` | BTS 서버 IP 확인 |
| `check-ping` | BTS와의 ping 연결 확인 |
| `update-sw-ver` | BTS 소프트웨어 버전 업데이트 |
| `check-soam` | BTS 소프트웨어 상태 확인 |
| `check-ssh` | SSH 연결 확인 |
| `gethwinfo` | BTS 하드웨어 정보 확인 |

## 📂 파일 처리
| 명령어 | 설명 |
|--------|------|
| `dnload-bts-cfg` | BTS 설정 파일 다운로드부터 역변환 후 세팅까지 |
| `dnload-bts-cfg-raw` | 설정 파일 원본 다운로드 |
| `apply-bts-cfg` | 설정 파일 적용 (비활성화 상태) |
| `act-bts-cfg` | 설정 파일 적용 및 활성화 |
| `activateplan` | 지정된 delta plan 활성화 |
| `commission` | 초기 BTS 설정 적용 |
| `recommission` | 설정 파일 재적용 |

## 💾 커밋
| 명령어 | 설명 |
|--------|------|
| `commit-all` | 전체 XML 저장 및 CLI 스크립트 생성 |
| `commit-diff` | 차이점만 저장 및 전송 |
| `commit` | 2단계 공식 적용하여 커밋 |
| `show-key` | 현재 세션의 task key 출력 |

## ⚙️ 설정
| 명령어 | 설명 |
|--------|------|
| `set-cfg-scf` | SCF XML 템플릿 로드 |
| `set-ru-type` | RU 타입 지정 |
| `set-cfg-tmpl` | 참조 템플릿 반영 및 적용 |

## 🗑️ 삭제
| 명령어 | 설명 |
|--------|------|
| `no-mo` | MO 삭제 |
| `no-pa` | 파라미터 삭제 |
| `no-tgt-bts` | BTS 초기화 및 작업 취소 |

## 🔍 조회
| 명령어 | 설명 |
|--------|------|
| `show-cfg` | 현재 또는 지정된 MO 파라미터 출력 |
| `show-glb` | 서버 저장 파일 목록 확인 |
| `show-sib` | 형제 MO의 파라미터 확인 |
| `show-can-mo` | 가능한 하위 MO 목록 확인 |
| `show-can-pa` | 현재 MO에서 가능한 파라미터 목록 |
| `show-user-input` | 사용자 입력 이력 출력 |

## 🧩 파라미터 관련
| 명령어 | 설명 |
|--------|------|
| `add-auto_pa` | MO에 파라미터 자동 추가 |
| `list` | 리스트 파라미터 추가 또는 수정 |
| `auto-config` | RU 타입 기반 자동 MO 생성 |

## 🛠️ 도구
| 명령어 | 설명 |
|--------|------|
| `scf-to-txt` | XML을 CLI 스크립트(.txt)로 변환 저장 |
| `excel-to-dict-formula` | 엑셀로 formula dict 생성 |
| `excel-to-dict-mo` | 엑셀로 mo/파라미터 dict 생성 |
| `excel-to-dict-mo-1000` | 엑셀 dict 생성 (1000개 제한) |
| `run-script` | 스크립트 파일 실행 |

## ⬅️ 탐색
| 명령어 | 설명 |
|--------|------|
| `exit` | 현재 계층에서 한 단계 위로 이동 |