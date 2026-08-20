FROM python:3.14-alpine
RUN apk add --no-cache git
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENTRYPOINT ["python", "-u", "main.py"]