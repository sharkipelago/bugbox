FROM python:latest
WORKDIR /app  
COPY ./requirements.txt .
RUN pip install -r requirements.txt  
COPY . .  
EXPOSE 5000  
CMD ["flask", "--app", "bugbox", "run", "--host=0.0.0.0", "--port=5000"]  