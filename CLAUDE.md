# url-shortener
mode: work
> 긴 URL을 줄이고 클릭 수를 집계하는 웹 서비스. 최신 IT 실무 중간고사 대체 과제(주제 3: ECS 배포)이자 포트폴리오용.

## 목적 / 범위
- 목표: 컨테이너 3개(frontend·backend·db)로 동작하고 ECS에 배포되어 URL로 접속된다. 2026-11-15(일) 23:59까지 보고서(PDF)+소스코드를 압축해 제출한다.
- Non-goals: 로그인·사용자별 링크, 커스텀 별칭, 만료 기능.

## 스택
| 영역 | 기술 | 선택 이유 |
|---|---|---|
| 프론트엔드 | Nginx + 정적 HTML/CSS/JS | 빌드 단계가 없고, Nginx가 API 프록시를 겸한다 |
| 백엔드 | FastAPI + PyMySQL | 주력 스택. 원시 SQL이라 보고서에서 설명하기 쉽다 |
| DB | MySQL 8.4 | 주력 스택 |
| 배포 | ECS Fargate, 단일 태스크 | 과제 요구사항. 컨테이너끼리 127.0.0.1로 통신한다 |

## 명령어
```bash
docker compose up --build -d --wait   # 실행 → http://localhost:8080
docker compose down                   # 중지 (-v 를 붙이면 DB 데이터도 삭제)
# 테스트: backend 폴더에서
docker run --rm -v "${PWD}:/src:ro" -w /src python:3.12-slim sh -c "pip install -q -r requirements-dev.txt && python -m pytest -q -p no:cacheprovider"
```

## 구조 (코드에서 안 보이는 것만)
- `frontend/nginx/default.conf.template`: 컨테이너 시작 시 `BACKEND_HOST`가 치환된다. 컴포즈는 `backend`, ECS는 `127.0.0.1`.
- `deploy/`: ECS 태스크 정의 예시와 배포 절차.

## 컨벤션 · 결정
- 단축 코드는 영문 대소문자+숫자 6자. 길이를 바꾸면 `services/links.py`, `routers/links.py`, Nginx 정규식 세 곳을 함께 바꾼다.
- DB 세션 시간대는 KST. 일별 통계가 한국 날짜 기준이다.
- 큰 결정은 `docs/decisions.md`.

## 함정 / 제약
- Git Bash의 `curl -d`로 한글을 보내면 UTF-8이 아니라서 400이 난다. 파일(`--data-binary @file`)로 보낸다.
- 로컬에 Python이 없다. 테스트는 컨테이너로 돌린다.
- 학교 실습 계정(925107452037, induk2024002667, 리전 ap-southeast-2)은 웹 콘솔 로그인만 된다. 제공된 액세스 키와 `aws login`은 거부되므로 배포는 콘솔에서 한다.
- 실습 계정의 `ecsTaskExecutionRole`에는 `logs:CreateLogGroup` 권한이 없다. 태스크 정의에 `awslogs-create-group`을 넣으면 태스크가 시작 전에 중지된다. 그래서 배포본에는 로그 설정이 없다.
- ECS는 Dockerfile의 HEALTHCHECK를 읽지 않는다. 태스크 정의의 `healthCheck`가 실제 기준이다.

## 현재 단계
- 지금: 2026-11-15 ECS 배포 완료. 클러스터 `induk2024002667-task-cluster`, 태스크 정의 `induk2024002667-task-definition:2`, 배포 URL http://54.79.45.89/ (태스크가 다시 뜨면 IP가 바뀐다). 보고서(https://claude.ai/artifact/GRTvzawobXTq7XAhkQcSzZ)에 배포 내용 반영 완료.
- 다음: 보고서에 스크린샷과 이름 채움 → PDF + 소스 압축 → 11-15 23:59까지 제출. 채점이 끝나면 태스크 중지와 클러스터 삭제.
