# HBBS/1 server image. Build locally; this project never pushes an image.
# Runs `python -m hbbs` as an unprivileged user.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HBBS_DATA_DIR=/data

WORKDIR /app

RUN groupadd --system hbbs \
    && useradd --system --gid hbbs --home-dir /app --shell /usr/sbin/nologin hbbs \
    && mkdir -p /data \
    && chown -R hbbs:hbbs /data /app

COPY hbbs /app/hbbs
COPY README.md /app/README.md

USER hbbs
VOLUME ["/data"]
EXPOSE 8443

ENTRYPOINT ["python", "-m", "hbbs"]
