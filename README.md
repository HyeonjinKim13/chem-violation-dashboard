# 생활화학제품 위반정보 분석 — Blue Edition

기존 Streamlit 대시보드의 **데이터 처리, 탭 구성, 차트 종류를 유지**하고, 가독성과 색상·폰트·그래프 스타일만 개선했습니다.

## 실행
```bash
pip install -r requirements.txt
streamlit run app.py
```

## GitHub/Streamlit 배포
기존 GitHub 저장소에서 다음 파일을 교체하세요.
- `app.py` (덮어쓰기)
- `.streamlit/config.toml` (숨김 폴더 내 파일 교체; 폴더가 없으면 생성)

`analysis_long.csv`는 원본과 동일합니다. `requirements.txt`의 Plotly 항목은 둥근 모서리 지원을 위해 최소 버전만 명시했습니다. 두 파일 모두 GitHub 저장소 루트에 두세요.

## 변경사항
- 흰색·아주 연한 하늘색 배경 / 선명한 파란색 헤더 / 블루 KPI 카드
- 명조체 제거, 한글 산세리프 폰트 설정 및 플랫폼별 폴백
- 트리맵·선버스트·생키·히트맵·막대·누적막대·꺾은선 팔레트 통일
- 막대 모서리 둥글게, 막대 간격, 라벨, 은은한 격자, 선형 그래프의 곡선·마커 개선
- **집계/분류 코드와 기존 6개 탭 및 필터, 차트 종류는 유지**

주의: Google Fonts 접속이 제한되는 환경에서는 OS에 설치된 한글 고딕 계열 폰트로 표시됩니다.
