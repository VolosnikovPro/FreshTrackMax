FROM python:3.14-alpine
WORKDIR /code
#RUN apk add --no-cache gcc musl-dev
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENTRYPOINT ["python", "-u", "main.py"]
