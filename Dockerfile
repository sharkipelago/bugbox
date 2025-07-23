FROM python:3.13-slim  
WORKDIR /app  

COPY requirements.txt ./
RUN pip install -r requirements.txt  

COPY . .  

# Expose port 5000 for Flask
EXPOSE 5000  

RUN flask --app bugbox init-db
CMD ["flask", "--app", "bugbox", "run", "--host=0.0.0.0"]