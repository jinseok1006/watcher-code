# 베이스 이미지 설정
FROM python:3.12-slim

# 작업 디렉토리 설정
WORKDIR /app

# 필요한 파이썬 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY ./src ./src

# 환경 변수 설정
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 실행 명령어
CMD ["python", "-m", "src.app"]
