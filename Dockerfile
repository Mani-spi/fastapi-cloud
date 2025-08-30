FROM python:3.11-slim

WORKDIR /code

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Alembic globally
RUN pip install alembic pymysql

# Copy all files in current folder (main.py, etc.)
COPY . .

# Ensure static folder
RUN mkdir -p static/images

# Expose port
EXPOSE 8000

# Run FastAPI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
