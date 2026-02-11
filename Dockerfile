FROM python:3.10-slim

WORKDIR /app

# 3. 필수 시스템 패키지 설치
# cv2(opencv), pdfplumber 등이 시스템 라이브러리를 필요로 할 수 있음
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# pip 업그레이드 후 라이브러리 설치 (캐시 없이 가볍게)
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

ENTRYPOINT [ "streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0" ]
