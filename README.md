# TaskFlow - 스마트 할 일 관리 웹 애플리케이션

Python Flask와 SQLite3 기반의 고성능 To-Do 관리 시스템입니다. 직관적인 UI, 실시간 대시보드 통계, RESTful API 및 다크/라이트 테마를 제공합니다.

---

## 🌟 주요 기능

- **할 일 전체 관리 (CRUD)**: 생성, 조회, 수정(모달), 상태 완료 토글, 개별 삭제 및 완료 항목 일괄 정리
- **실시간 대시보드 통계**: 전체 태스크 수, 진행 중, 완료 항목, 완료율(%) 프로그레스 바 및 기한 초과(Overdue) 배지
- **필터링 & 검색 & 다중 정렬**:
  - 상태 탭 필터 (전체 / 진행 중 / 완료됨)
  - 카테고리 필터 (업무, 개인, 공부, 쇼핑, 아이디어, 기타)
  - 우선순위 필터 (높음, 보통, 낮음)
  - 실시간 검색어 검색
  - 정렬 (최신순, 오래된순, 마감일순, 우선순위순)
- **모던 UI/UX**: 다크 모드 / 라이트 모드 전환 및 로컬 스토리지 연동, 글래스모피즘 디자인
- **RESTful API**: 표준 JSON REST API 지원으로 프론트엔드/외부 시스템과 유연하게 연동 가능
- **자동 DB 초기화**: 앱 최초 실행 시 SQLite 데이터베이스 및 기본 샘플 데이터 자동 생성

---

## 🛠 기술 스택

- **Backend**: Python 3, Flask 3.0+
- **Database**: SQLite3
- **Frontend**: HTML5, Vanilla CSS3 (Custom Design System), JavaScript (ES6+ Fetch API)
- **Testing**: pytest, unittest

---

## 🚀 시작하기

### 1. 의존성 패키지 설치

```bash
pip install -r requirements.txt
```

### 2. 애플리케이션 실행

```bash
python app.py
```

브라우저에서 `http://127.0.0.1:5000` 으로 접속합니다.

---

## 🧪 테스트 실행

```bash
pytest tests/
```

---

## 📡 REST API 안내

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/todos` | 필터 및 정렬 조건에 따른 할 일 목록 조회 |
| `POST` | `/api/todos` | 새 할 일 등록 |
| `GET` | `/api/todos/<id>` | 특정 할 일 상세 정보 조회 |
| `PUT` | `/api/todos/<id>` | 할 일 정보 전체 수정 |
| `PATCH` | `/api/todos/<id>/toggle` | 할 일 완료 여부 토글 |
| `DELETE` | `/api/todos/<id>` | 특정 할 일 삭제 |
| `DELETE` | `/api/todos/completed` | 완료된 모든 할 일 일괄 삭제 |
| `GET` | `/api/stats` | 대시보드 요약 통계 조회 |
