FROM nginx:1.27-alpine
# 컴포즈 기본값. ECS 단일 태스크에서는 BACKEND_HOST=127.0.0.1 로 덮어쓴다.
ENV BACKEND_HOST=backend \
    BACKEND_PORT=8000
# /etc/nginx/templates/*.template 은 컨테이너 시작 시 환경변수가 치환되어 conf.d 로 들어간다.
COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY public /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=5 \
    CMD wget -q -O /dev/null http://127.0.0.1/healthz || exit 1
