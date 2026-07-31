FROM mcr.microsoft.com/playwright/python:v1.61.0-jammy

WORKDIR /app

# Install the ccworks package (and its declared dependencies) editable so
# the source tree in /app is directly runnable as a module.
COPY pyproject.toml README.md LICENSE.md ./
COPY src/ ./src/
COPY tests/ ./tests/
RUN pip install --no-cache-dir -e .

# The base image ships browser binaries for its own pinned playwright version,
# but `playwright` is an open requirement (>=1.44) so pip may resolve a newer
# one whose binaries live under a different path. Install browsers for whatever
# version pip actually resolved; OS-level deps already come from the base image.
RUN playwright install chromium

# Skip the interactive chromium bootstrap in the container — the base image
# already ships Playwright browsers.
ENV CCWORKS_SKIP_BROWSER_BOOTSTRAP=1

# Default: run the mock unit tests
CMD ["python", "-m", "unittest", "discover", "-s", "tests"]
