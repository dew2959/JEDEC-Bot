FROM python:3.11

WORKDIR /app

COPY requirements.txt .

# pip 업그레이드 후 라이브러리 설치 (캐시 없이 가볍게)
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

ENTRYPOINT [ "streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0" ]
