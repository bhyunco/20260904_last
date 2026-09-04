# VIBE RPA - 교육기업 시장 반응 실시간 분석 대시보드 (20260904_last)

네이버 카페 크롤링, OpenAI LLM 감성 분석, 교차 집계 통계 및 자동 비즈니스 메일링을 지원하는 종합 RPA 분석 대시보드입니다. Supabase 클라우드 데이터베이스와 연동되어 실시간 시장 반응 및 기사 목록을 보관하며, Vercel Serverless에 프로덕션 배포되어 있습니다.

---

## 🌐 라이브 배포 및 저장소 정보

- **Vercel 프로덕션 URL**: [https://20260904last.vercel.app](https://20260904last.vercel.app)
- **GitHub 저장소**: [https://github.com/bhyunco/20260904_last](https://github.com/bhyunco/20260904_last)
- **클라우드 데이터베이스**: Supabase PostgreSQL (`todos` 실시간 동기화)
- **프로젝트 및 저장소 명칭**: `20260904_last`

---

## 🌟 핵심 기능

1. **앱 비밀번호 기억 체크박스 (Requirement 1)**:
   - UI에 "앱 비밀번호 기억하기" 커스텀 체크박스 제공 (브라우저 `localStorage` 연동)
   - 새로고침 또는 재접속 시에도 안전하게 저장된 비밀번호 자동 유지/복원 및 숨김/보기(눈 아이콘) 토글

2. **실시간 % 진행률 및 로그 스트리밍 (Requirement 2)**:
   - **SSE(Server-Sent Events)** 기반 실시간 스트리밍
   - 대형 네온 퍼센트 카운터(`0%` ~ `100%`)와 프로그레스 바
   - 4단계 프로세스 스텝 트래커 (크롤링 → LLM 감성 분석 → 통계 집계 → 비즈니스 메일링)
   - 터미널 스타일 실시간 실행 로그 콘솔

3. **현업 비즈니스 메일 디자인 업그레이드 (Requirement 3)**:
   - **Market Intelligence Report** 반응형 HTML 이메일 템플릿
   - Executive Summary 카드 (총 분석 건수, 긍정 반응 수, 평균 긍정 비율)
   - 기업별 교차 집계 표 (컬러 뱃지 및 비율 포함)
   - `DE.xlsx` 첨부파일 및 Gmail SMTP 발송

4. **기존 코드 기능 및 비밀키 100% 보존 (Requirement 4)**:
   - OpenAI Key 및 모델(`gpt-5.6-luna`), 프롬프트 완전 보존
   - 크롬드라이버(`c:/chromedriver.exe`) 및 네이버 카페 크롤링 로직 완전 보존
   - 파일 저장 로직(`naver_cafe_article.xlsx`, `naver_cafe_article_yn.xlsx`, `DE.xlsx`) 완전 보존

5. **기업별 긍/부정 원형 그래프 반응형 대시보드 (Requirement 5)**:
   - Chart.js 기반 전체 시장 반응 도넛/파이 차트
   - 기업별(멀티캠퍼스, 바이브코딩스쿨, 패스트캠퍼스 등) 개별 도넛 차트 그리드
   - 기업별 비교 바 차트 및 crosstab 요약 테이블
   - 네이버 카페 원본 게시글 검색 및 바로가기 링크 지원

6. **Supabase 클라우드 데이터베이스 연동**:
   - 실시간 분석 통계 및 기사 데이터를 Supabase 클라우드에 자동 동기화하여 서버리스 환경에서도 영구 보존 및 초고속 렌더링

---

## 🛠 기술 스택

- **Backend**: Python 3, Flask 3.0+
- **RPA & Scraping**: Selenium WebDriver (Chrome)
- **AI / LLM**: OpenAI API (`gpt-5.6-luna` / Developer & User Reasoning System)
- **Database**: Supabase (PostgreSQL Cloud) + Local Excel Fallback
- **Cloud & Deployment**: Vercel Serverless (Python 3.12 Runtime), GitHub
- **Frontend**: HTML5, Vanilla CSS3 (Custom Glassmorphism), JavaScript (ES6+), Chart.js
