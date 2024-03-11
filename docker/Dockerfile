FROM python:latest
WORKDIR /genai
COPY ../src .
RUN pip install -I -r ../src/requirements.txt
EXPOSE 8080
CMD ["python", "/genai/main.py"]