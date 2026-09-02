FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Les dependances d'abord: cette couche est mise en cache tant que
# pyproject.toml ne change pas.
COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install .

COPY . .
# Reinstallation en editable pour que le bind mount de dev soit pris en compte
RUN pip install --no-deps -e .

EXPOSE 8000
CMD ["uvicorn", "ananas.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
