# Live Cyber Threat Map

## System Info

- OS
  - rhel 8.10
- Container Engine
  - podman

## Environments

 Envs | Example | Remarks
---------|----------|---------
 HOST_IP | 192.168.10.240 | 웹서버 구동 호스트 IP
 HOST_PORT | 5678 | 외부 접근 PORT
 CONTAINER_PORT | 6789 | 컨테이너 내부 애플리케이션 PORT
 REDIS_HOST | redis-server | 기본값
 REDIS_PORT | 6379 | 기본값
 SYSLOG_SOURCE_PORT | 5678 | HOST_PORT와 동일
 SYSLOG_SOURCE_IP | 192.168.10.111 | syslog 송신 SONAR IP

## Quick Start

- '.env' 수정

```shell
vi .env
```

- podman container image 로드

```shell
cd ${image 경로}
podman load -i cyber_threat_map.tar
podman load -i redis.tar
```

- podman container 구동

```shell
cd ${docker-compose 파일 경로}
podman compose up -d
```

