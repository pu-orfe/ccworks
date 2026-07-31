# Keep this tag in step with the `playwright` version pip resolves for the
# package (see pyproject.toml). When bumping, bump both together.
FROM mcr.microsoft.com/playwright/python:v1.62.0-jammy

WORKDIR /app

# Install the ccworks package (and its declared dependencies) editable so
# the source tree in /app is directly runnable as a module.
COPY pyproject.toml README.md LICENSE.md ./
COPY src/ ./src/
COPY tests/ ./tests/
RUN pip install --no-cache-dir -e .

# Safety net for version drift. `playwright` is an open requirement (>=1.44), so
# pip resolves whatever is newest at build time; when that outruns the base image
# tag above, the pre-installed browsers sit at a path the new lib does not look
# in and every test dies with "Executable doesn't exist at /ms-playwright/...".
# This installs browsers for the version pip actually resolved, and no-ops when
# they are already present. OS-level deps come from the base image.
RUN playwright install chromium

# Skip the interactive chromium bootstrap in the container — the base image
# already ships Playwright browsers.
ENV CCWORKS_SKIP_BROWSER_BOOTSTRAP=1

# Default: run the mock unit tests
CMD ["python", "-m", "unittest", "discover", "-s", "tests"]
