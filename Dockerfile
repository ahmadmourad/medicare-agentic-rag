FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY Frontend ./Frontend

RUN mkdir -p /app/data && chmod 777 /app/data

ENV PORT=7860
ENV HF_SPACE=1
ENV LLM_PROVIDER=auto
ENV MEDLINEPLUS_ENABLED=true

EXPOSE 7860

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
