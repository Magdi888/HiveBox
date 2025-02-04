FROM python:3.12.8-alpine3.21@sha256:ba13ef990f6e5d13014e9e8d04c02a8fdb0fe53d6dccf6e19147f316e6cc3a84 AS builder

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.12.8-alpine3.21@sha256:ba13ef990f6e5d13014e9e8d04c02a8fdb0fe53d6dccf6e19147f316e6cc3a84

WORKDIR /app

RUN addgroup --system py-app && adduser --system py-app -G py-app
COPY --from=builder /app /app
COPY --from=builder /usr/local/lib/python3.12/site-packages/ /usr/local/lib/python3.12/site-packages/

EXPOSE 8000
USER py-app
CMD ["python", "main.py"]
