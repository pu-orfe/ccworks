FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source and tests
COPY src/ ./src/
COPY tests/ ./tests/

# Command to run unit tests by default
CMD ["python", "-m", "unittest", "discover", "-s", "tests"]
