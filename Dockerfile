FROM python:3.12-slim-bookworm

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

CMD [ "uvicorn", "main:app", "--reload", "--port=8000", "--host=0.0.0.0" ]
