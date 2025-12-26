# Development stage
FROM python:3.12 AS dev
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
RUN pip install --upgrade pip
COPY ./requirements.txt .
RUN pip install -r requirements.txt
COPY ./entrypoint.sh .
RUN sed -i 's/\r$//g' /app/entrypoint.sh && chmod +x /app/entrypoint.sh
COPY . .
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# Production stage
FROM python:3.12 AS prod
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
RUN pip install --upgrade pip
COPY ./requirements.txt .
RUN pip install -r requirements.txt
COPY ./entrypoint.sh .
RUN sed -i 's/\r$//g' /app/entrypoint.sh && chmod +x /app/entrypoint.sh
COPY . .
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "task_management.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--threads", "8"]