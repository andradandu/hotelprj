FROM python:3.13

WORKDIR /hotelprj

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "scripts/pipeline.py"]
