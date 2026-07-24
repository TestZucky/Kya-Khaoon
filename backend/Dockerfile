# Dev image: the source is bind-mounted over /app by compose, so uvicorn --reload
# picks up edits on the host. Only the dependency layer is baked in, which means
# a code change never triggers a rebuild.
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# psycopg[binary] ships wheels, so no libpq/gcc needed. Requirements are copied
# alone first so the (slow) install layer caches until requirements.txt changes.
COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
