FROM --platform=amd64 mcr.microsoft.com/playwright/python:v1.40.0-jammy

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PIP_DEFAULT_TIMEOUT=100
ENV POETRY_VIRTUALENVS_CREATE=false

# Upgrade pip
RUN python3 -m pip install --upgrade pip

# Install Poetry
RUN pip install poetry && poetry --version

# Set the working directory in the container
WORKDIR /app

# Copy the project code
COPY . .

# Copy the pyproject.toml and poetry.lock files
COPY poetry.lock pyproject.toml ./

# Install project dependencies with Poetry 
RUN poetry config virtualenvs.in-project true && \
    poetry install --no-interaction --no-ansi

# Copy the sample environment file
RUN mv .env.sample .env

# Run Playwright installation commands
RUN playwright install --with-deps chromium
