# 빌드 방법

번역 대본·원문은 저장소에 없으므로, 아래는 자신이 가진 원본과 번역 파일로 다시 빌드하는 절차입니다.

## 준비물
- 원본 ISO `Tanteibu - The Detective Club - Tantei to Yuurei to Kaitou to (Japan) (v1.01).iso` (MD5 `122780f48ca200fc6281de8d410c175b`)
- Python 3.12+ : `pip install pillow numpy capstone websocket-client`
- 글꼴: `NanumSquareNeo-*.ttf`, `SeoulHangang*.ttf` (작업 폴더), `Galmuri9.ttf`·`Galmuri11.ttf` (`fonts/`)

## 폴더 구성
```
<작업 폴더>/
  Tanteibu - ... (Japan) (v1.01).iso
  *.ttf, fonts/
  tools/          (이 저장소의 tools)
  trans/          eboot.json, images.json  (번역 — 저장소 미포함)
  work/iso/       ISO를 풀어 둔 폴더
  work/jp/        대본 원문 JSON (tools/blt.py + jtab.py로 추출)
  work/ko/        번역 대본 JSON (저장소 미포함)
  work/eboot/EBOOT.dec  복호화한 EBOOT
```

## 순서
1. ISO 풀기: `python tools/extract_iso.py` → `work/iso/`
2. EBOOT 복호화 → `work/eboot/EBOOT.dec`
3. 대본 원문 추출: `tools/blt.py`의 `parse()`와 `tools/jtab.py`의 `decode()`로 `USRDIR/Script/*.blt` → `work/jp/*.json`
4. 번역 작성
   - `work/ko/<대본>.json` = 원문과 같은 길이의 문자열 배열 — `python tools/check_ko.py`로 줄 수·줄 길이(27자)·태그·글자 검사
   - `trans/eboot.json` = 실행 파일 문구 `{off, jp, ko, keep}` (세이브 제목 문구는 `keep`)
   - `trans/images.json` = 그림별 글자 상자 사양
5. 빌드: `python tools/build.py` → `Tanteibu - The Detective Club (Korean).iso`
6. 차분: `xdelta3 -f -e -s 원본.iso 한글.iso 패치.xdelta`

PPSSPP 원격 디버거로 자동 확인할 때는 `python tools/emu.py start <ISO>` / `shot` / `press` / `seq` 를 씁니다.
