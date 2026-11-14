# ECS(Fargate) 배포 절차

태스크 하나에 컨테이너 3개(frontend, backend, db)를 넣는다. 같은 태스크의 컨테이너는 네트워크를 공유하므로 서로 `127.0.0.1`로 통신한다.

## 1. 이미지를 Docker Hub에 올린다

```bash
docker login
docker build -t skywith628/url-shortener-backend:1.0 ./backend
docker build -t skywith628/url-shortener-frontend:1.0 ./frontend
docker push skywith628/url-shortener-backend:1.0
docker push skywith628/url-shortener-frontend:1.0
```

DB는 ECR Public의 MySQL 공식 이미지(`public.ecr.aws/docker/library/mysql:8.4`)를 그대로 쓴다.

## 2. 태스크 정의를 등록한다

1. `ecs-task-definition.example.json`을 복사해 `<DB_PASSWORD>`(db와 backend 두 곳에 같은 값)와 `<DB_ROOT_PASSWORD>`를 채운다. 채운 파일은 `.gitignore`에 들어 있다.
2. ECS 콘솔 → 태스크 정의 → **JSON으로 새 태스크 정의 생성**에 붙여 넣는다.

## 3. 클러스터를 만들고 태스크를 실행한다

1. ECS 콘솔 → 클러스터 생성 → 인프라는 **Fargate 전용**.
2. 클러스터 → 태스크 탭 → **새 태스크 실행**
   - 태스크 정의 `induk2024002667-task-definition`, 태스크 수 1
   - 네트워킹: 기본 VPC와 기본 보안 그룹, **퍼블릭 IP 켜기**
3. 태스크가 `실행 중`이고 컨테이너 3개가 모두 `정상`인지 확인한다.

## 4. 배포를 확인한다

태스크 상세 화면의 **퍼블릭 IP**가 배포 URL이다: `http://<퍼블릭 IP>/`

- 링크를 만들고, 단축 주소로 접속해 원본으로 이동하는지, 클릭 수가 오르는지 확인한다.
- `http://<퍼블릭 IP>/healthz` 는 `ok`를 돌려준다.

## 알아 둘 점

- **로그 설정이 없다.** 실습 계정의 `ecsTaskExecutionRole`에는 `logs:CreateLogGroup` 권한이 없어서, `awslogs-create-group`을 넣으면 태스크가 시작 전에 `ResourceInitializationError`로 중지된다. 그래서 `logConfiguration`을 뺐다.
- **퍼블릭 IP는 태스크가 다시 뜨면 바뀐다.** 고정 주소가 필요하면 ALB를 앞에 둔다.
- **DB 데이터는 태스크가 다시 뜨면 사라진다.** Fargate 태스크의 저장소는 임시 저장소다. 실서비스라면 RDS나 EFS 볼륨을 쓴다.
- **비밀번호가 태스크 정의에 평문으로 들어간다.** 실습 범위의 타협이며, 실서비스라면 Secrets Manager의 `secrets` 항목으로 주입한다.
- Dockerfile의 `HEALTHCHECK`는 ECS가 읽지 않는다. 그래서 태스크 정의에 `healthCheck`를 따로 적었다.
