# ECS(Fargate) 배포 절차

태스크 하나에 컨테이너 3개(frontend, backend, db)를 넣는다. 같은 태스크의 컨테이너는 네트워크를 공유하므로 서로 `127.0.0.1`로 통신한다.

보고서에 넣을 스크린샷이 필요한 지점은 📸 로 표시했다.

## 1. 이미지를 Docker Hub에 올린다

AWS CLI 없이 콘솔만으로 진행할 수 있도록 Docker Hub(공개 저장소)를 쓴다. `<DOCKERHUB_ID>`는 본인 아이디로 바꾼다.

```bash
docker login
```

```bash
docker build -t <DOCKERHUB_ID>/url-shortener-backend:1.0 ./backend
```

```bash
docker build -t <DOCKERHUB_ID>/url-shortener-frontend:1.0 ./frontend
```

```bash
docker push <DOCKERHUB_ID>/url-shortener-backend:1.0
```

```bash
docker push <DOCKERHUB_ID>/url-shortener-frontend:1.0
```

📸 Docker Hub 저장소 목록 화면

## 2. 태스크 정의를 만든다

1. `ecs-task-definition.example.json`을 `ecs-task-definition.json`으로 복사한다. 이 파일은 `.gitignore`에 들어 있다.
2. 자리표시자를 바꾼다.
   - `<DOCKERHUB_ID>`: Docker Hub 아이디
   - `<REGION>`: 실습 계정 리전 (예: `ap-northeast-2`)
   - `<ACCOUNT_ID>`, `<EXECUTION_ROLE>`: 실습 계정에서 쓸 수 있는 태스크 실행 역할. 보통 `ecsTaskExecutionRole`이고, AWS Academy 계정이면 `LabRole`이다.
   - `<DB_PASSWORD>`: db와 backend 두 곳에 같은 값. `<DB_ROOT_PASSWORD>`: 다른 값.
3. ECS 콘솔 → 태스크 정의 → **JSON으로 새 태스크 정의 생성**에 붙여 넣는다.

📸 태스크 정의 생성 화면, 생성된 태스크 정의의 컨테이너 3개 목록

`awslogs-create-group` 때문에 권한 오류가 나면 CloudWatch에서 `/ecs/url-shortener` 로그 그룹을 직접 만들고 그 옵션 줄을 지운다.

## 3. 클러스터와 서비스를 만든다

1. ECS 콘솔 → 클러스터 생성 → 인프라는 **AWS Fargate**.
2. 클러스터 → 서비스 생성
   - 시작 유형 Fargate, 태스크 정의 `url-shortener`, 원하는 태스크 수 1
   - 네트워킹: 퍼블릭 서브넷, **퍼블릭 IP 켜기**
   - 보안 그룹: 인바운드 **HTTP 80**을 `0.0.0.0/0`에 허용. 3306과 8000은 열지 않는다.
3. 태스크가 `RUNNING`이고 컨테이너 3개가 모두 `HEALTHY`인지 확인한다.

📸 클러스터·서비스 생성 화면, 보안 그룹 인바운드 규칙, 태스크 실행 상태(컨테이너 3개 HEALTHY)

## 4. 배포를 확인한다

태스크 상세 → 네트워킹의 **퍼블릭 IP**가 배포 URL이다: `http://<퍼블릭 IP>/`

- 링크를 만들고, 단축 주소로 접속해 원본으로 이동하는지, 클릭 수가 오르는지 확인한다.
- `http://<퍼블릭 IP>/healthz` 는 `ok`를 돌려준다.

📸 배포 URL로 접속한 서비스 화면, CloudWatch 로그

## 알아 둘 점

- **퍼블릭 IP는 태스크가 다시 뜨면 바뀐다.** 보고서에 적은 URL이 채점 때까지 유효하도록 제출 후에는 서비스를 건드리지 않는다. 고정 주소가 필요하면 ALB를 앞에 둔다.
- **DB 데이터는 태스크가 다시 뜨면 사라진다.** Fargate 태스크의 저장소는 임시 저장소다. 실서비스라면 RDS나 EFS 볼륨을 쓴다.
- **비밀번호가 태스크 정의에 평문으로 들어간다.** 실습 범위의 타협이며, 실서비스라면 Secrets Manager의 `secrets` 항목으로 주입한다.
- Dockerfile의 `HEALTHCHECK`는 ECS가 읽지 않는다. 그래서 태스크 정의에 `healthCheck`를 따로 적었다.
- 채점이 끝나면 서비스 → 클러스터 순서로 삭제해 과금을 막는다.
