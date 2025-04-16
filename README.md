# 실시간 사이버 위협 지도

실시간으로 사이버 위협 정보를 수집하고 지도에 시각화하는 애플리케이션입니다.

## 시스템 요구사항

- **OS**: RHEL 8.10 또는 최신 리눅스 배포판
- **컨테이너 엔진**: Podman (Docker 호환)
- **Python**: 3.8 이상

## 환경 변수 설정

프로젝트 루트에 `.env` 파일을 생성하고 다음 환경 변수를 설정합니다:

| 환경 변수 | 예시 | 설명 |
|---------|----------|---------| 
| HOST_IP | 192.168.10.240 | 웹서버 구동 호스트 IP |
| HOST_PORT | 5678 | 외부 접근 PORT |
| CONTAINER_PORT | 6789 | 컨테이너 내부 애플리케이션 PORT |
| REDIS_HOST | redis-server | Redis 서버 호스트명 |
| REDIS_PORT | 6379 | Redis 서버 포트 |
| SYSLOG_SOURCE_PORT | 5678 | 시스로그 수신 포트 (HOST_PORT와 동일) |
| SYSLOG_SOURCE_IP | 192.168.10.111 | 시스로그 송신 SONAR IP |
| ENV | PROD | 실행 환경 (LOCAL/PROD) |

## 빠른 시작

### 1. 환경 설정

`.env` 파일을 필요에 맞게 수정합니다:

```bash
vi .env
```

### 2. 컨테이너 이미지 준비

이미지 파일이 있는 경우:

```bash
cd ${이미지_경로}
podman load -i cyber_threat_map.tar
podman load -i redis.tar
```

직접 빌드하는 경우:

```bash
podman build -t cyber_threat_map:latest .
```

### 3. 컨테이너 실행

```bash
podman compose up -d
```

### 4. 웹 인터페이스 접속

브라우저에서 다음 주소로 접속:
```
http://<HOST_IP>:<HOST_PORT>
```

## 프로젝트 구조

```
cyber_threat_map/
├── DB/                  # 위협 정보 및 GeoIP 데이터베이스
├── data_server/         # 데이터 수집 및 처리 서버
│   ├── data_server.py   # 메인 데이터 서버
│   ├── syslog_receiver.py  # 시스로그 수신기
│   └── country_coordinates.py  # 국가 좌표 정보
├── map_server/          # 웹 서버 및 시각화 관련 코드
│   ├── map_server.py    # 메인 웹 서버
│   ├── index.html       # 메인 페이지
│   └── static/          # 정적 파일 (JS, CSS, 이미지)
├── utils/               # 유틸리티 도구
│   └── logger.py        # 로깅 설정
├── .env                 # 환경 변수 설정
├── docker-compose.yml   # 컨테이너 구성
├── dockerfile           # 컨테이너 빌드 스크립트
├── requirements.txt     # Python 의존성 패키지
├── start.sh             # 시작 스크립트
└── stop.sh              # 중지 스크립트
```

## 로그 확인

로그는 `logs/` 디렉토리에 저장됩니다:

```bash
tail -f logs/mapserver.log
```

## 문제 해결

- Redis 연결 문제: `.env` 파일의 `REDIS_HOST` 설정 확인
- 데이터가 표시되지 않음: 시스로그 소스 설정 및 네트워크 연결 확인
- 컨테이너 문제: `podman logs cyber_threat_map` 명령으로 로그 확인
