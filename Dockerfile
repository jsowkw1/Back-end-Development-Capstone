FROM python:3.9.16-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# This app uses SQLite and does not invoke netcat in its entrypoint.

ENV APP=/app

WORKDIR ${APP}

COPY requirements.txt ${APP}/requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY . ${APP}

EXPOSE 8000

RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/bin/bash","/app/entrypoint.sh"]

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

