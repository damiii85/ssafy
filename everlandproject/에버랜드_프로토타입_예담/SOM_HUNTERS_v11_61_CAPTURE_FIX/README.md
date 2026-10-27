# SOM HUNTERS Prototype
에버랜드 공모전용 모바일 웹 프로토타입입니다.

## 실행
1. Node.js 설치
2. 이 폴더에서 터미널 실행
3. `npm install`
4. `npm run dev`
5. 표시되는 localhost 주소 접속

## 시연 동선
홈 → 길드 배정 → AI Quest → Quest 상세 → My Quest → Quest Map → SOM 발견 → AR 포획 → 포획 성공 → 길드전 → SOM Shop

## 구현
- React + Vite
- 모바일 UI
- 페이지 이동/하단 내비게이션
- SOM 포획 시 SOM 포인트 +20
- 포획 후 길드 기여도 변화
- Mock data 기반, 서버/DB 없음

`reference-ui.png`는 구현 참고용 원본 시안입니다.


## v3 mascot update
The app uses the user-provided transparent-background SOM mascot at `public/assets/lilac-som.png` throughout the prototype.

## v5 반영사항
- 레퍼런스 13개 흐름을 분리 구현: 홈 / 길드 배정 / Hunters Home / AI Quest / Quest Detail / My Quest / Quest Map / SOM 발견 / AR 포획 / 포획 성공 / Guild Battle / SOM 도감 / SOM Shop
- 홈 메인 비주얼을 에버랜드 성·정원 애니메이션풍 SVG 일러스트로 교체
- 길드 배정 전 Guild Battle은 '길드전 시작하기' 화면, 배정 후에는 실시간 랭킹보드/내 길드/기여도 화면으로 변경
- 기존 미션별 사진 업로드 / 현재 위치 공유 / 동행인 등록 모달 유지
- 투명 배경 라일락솜 PNG 유지
