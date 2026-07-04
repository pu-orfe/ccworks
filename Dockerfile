FROM mcr.microsoft.com/playwright/python:v1.60.0-jammy

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source and tests
COPY src/ ./src/
COPY tests/ ./tests/

# Command to run unit tests by default
# This will find and run all test_*.py files, including justification tests
CMD ["python", "-m", "unittest", "discover", "-s", "tests"]
