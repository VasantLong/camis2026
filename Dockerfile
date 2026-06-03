FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

RUN playwright install chromium --with-deps

COPY app/ ./app/
COPY migrations/ ./migrations/
COPY alembic.ini .

COPY gunicorn.conf.py .

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && gunicorn app.main:app -c gunicorn.conf.py"]
