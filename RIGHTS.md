# 권리 및 외부 자료

이 저장소는 비공식 한국어 패치의 제작 도구·기술 문서 공개용입니다. 원작 게임 「たんていぶ THE DETECTIVE CLUB -探偵と幽霊と怪盗と-」(PSP)와 그 텍스트·이미지·음성·영상·실행 코드의 권리는 원 권리자에게 있습니다. 원본 게임, 패치 적용 게임, 게임에서 추출한 실행 파일·텍스처·음성·글꼴은 배포하지 않으며, 릴리즈에는 원본 디스크 이미지가 있어야만 쓸 수 있는 차분 파일(xdelta)만 첨부합니다.

번역 대본(`work/ko/*.json`)·그림 글자 사양(`trans/images.json`)·실행 파일 문구(`trans/eboot.json`)는 저장소에 넣지 않았습니다. `tools/jtab.py`에는 게임 글꼴의 글자 배열표가 들어 있습니다.

저장소 공개 자체가 모든 파일에 동일한 오픈소스 라이선스를 부여한다는 뜻은 아닙니다. 자체 제작 코드에 대한 별도 포괄 라이선스는 현재 지정하지 않았습니다. `tools/isobuild.py`, `tools/ppsspp_rpc.py`, `tools/emu.py`, `tools/gim_tool.py` 등 일부 도구는 같은 제작자의 다른 한글패치 저장소에서 가져온 것입니다.

글꼴 파일은 배포하지 않습니다(`docs/FONT_CREDITS.md`). xdelta, PPSSPP, Python 라이브러리(Pillow, NumPy, capstone, websocket-client 등) 등 외부 도구는 각 프로젝트의 라이선스를 따르며 바이너리를 재배포하지 않습니다.
