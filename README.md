# 탐정부 THE DETECTIVE CLUB -탐정과 유령과 괴도와- (PSP) 비공식 한글패치

PSP 일본판 **たんていぶ THE DETECTIVE CLUB -探偵と幽霊と怪盗と- (탐정부 더 디텍티브 클럽, ULJM-05925)** 비공식 한국어 패치입니다. 이 저장소에는 제작 도구와 기술 문서만 있고, 패치 파일(xdelta)은 [Releases](../../releases)에서 받을 수 있습니다. 게임 원본·일본어 원문·번역 대본은 포함하지 않습니다.

## 적용 방법
1. 아래 해시와 일치하는 **원본 `.iso`** 를 준비합니다. (CSO·CHD 등으로 변환한 이미지에는 적용할 수 없습니다.)
   - PowerShell: `Get-FileHash -Algorithm MD5 -LiteralPath '.\Tanteibu - The Detective Club - Tantei to Yuurei to Kaitou to (Japan) (v1.01).iso'`
2. xdeltaUI 같은 도구로 원본 `.iso` 에 `Tanteibu_TheDetectiveClub_KO_v1.0.xdelta` 를 적용합니다. (Patch = xdelta, Source File = 원본 ISO, Output File = 새 파일명)
   - 명령줄: `xdelta3 -d -s "Tanteibu - The Detective Club - Tantei to Yuurei to Kaitou to (Japan) (v1.01).iso" Tanteibu_TheDetectiveClub_KO_v1.0.xdelta "Tanteibu - The Detective Club (Korean).iso"`
3. 만들어진 ISO를 PPSSPP 또는 커스텀 펌웨어(PSP·PS Vita Adrenaline 등)에서 실행합니다.

| 항목 | 값 |
| --- | --- |
| 원본 ISO 크기 | 539,459,584 바이트 |
| 원본 ISO MD5 | `122780f48ca200fc6281de8d410c175b` |
| 원본 ISO SHA-256 | `a2c2e9b3261229a55c76934699dd28e256be469d4bc89e0cbfb8f39a60408969` |
| xdelta SHA-256 | `4f7725c5531646805893c14361fa27400a41ccf428f60de06f952f949f7d627f` |
| 결과 ISO 크기 | 539,459,584 바이트 |
| 결과 ISO SHA-256 | `c43a5a45294af9fd18829232ef01f3177af3ce71cbd684d258e71da340c37512` |

## 주의
- 복호화한 실행 파일을 EBOOT로 넣었기 때문에 **PPSSPP·커스텀 펌웨어 전용**입니다. 정품 펌웨어에서는 부팅되지 않습니다.
- 메모리 부족으로 멈추는 문제를 막으려고 확장 메모리를 쓰므로, 실기는 **PSP-2000 이상**(또는 PS Vita)이 필요합니다. PSP-1000에서는 새 게임 시작 시 멈출 수 있습니다.
- 원본이나 다른 버전 패치에서 만든 **상태저장(세이브 스테이트)** 은 불러오지 마세요. 일반 세이브는 그대로 쓸 수 있습니다.

## 한글화 내용
- 본편 대본 74개 — 대사·선택지·나레이션·화자 이름 약 11,300줄 직접 번역
- 메시지 글꼴: 한글 2,350자 이상(13px 나눔스퀘어네오), 문장부호 반각 배치(실행 파일 글자 배치 코드 수정)
- 그림 글자 346장 — 타이틀 메뉴(강조 프레임 포함), 증거·추리 메뉴, 대화 상자, 게임 오버, 옵션·갤러리 등
- 실행 파일 시스템 메시지 — 세이브·로드 안내, 확인 문구 등
- 홈 메뉴 게임 제목

## 그대로 둔 것
- 음성, 타이틀 로고(たんていぶ), 영어 표기(THE DETECTIVE CLUB, Press START Button, NOW LOADING!), 세이브 데이터 제목(바꾸면 세이브가 손상 판정됨), 개발용 시험 대본

## 검증 범위
PPSSPP에서 첫 실행(시스템 데이터 생성)·타이틀·메뉴·새 게임 도입부 대사와 세이브·로드를 확인했습니다. 대본 전체를 줄 수·줄 길이·글자 검사로 확인했지만 전체 플레이는 검증하지 않았습니다. 문제를 발견하면 Issues에 알려 주세요.

## 문서
- [CHANGELOG.md](CHANGELOG.md) — 변경 기록
- [docs/TECHNICAL.md](docs/TECHNICAL.md) — 파일 형식과 한글화 방법
- [docs/BUILD.md](docs/BUILD.md) — 직접 빌드하는 방법
- [docs/FONT_CREDITS.md](docs/FONT_CREDITS.md) — 글꼴
- [RIGHTS.md](RIGHTS.md) — 권리 및 외부 자료
