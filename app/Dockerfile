FROM python:latest
WORKDIR /app  
COPY ./requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt  
COPY . .  
EXPOSE 5000  
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "bugbox:create_app()"] 