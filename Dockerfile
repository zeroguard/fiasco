# Development Docker container configuration
# hadolint ignore=DL3007
FROM python:3.7.5-slim-buster

ENV DEBIAN_FRONTEND=noninteractive \
    LC_ALL=C.UTF-8 \
    LANG=C.UTF-8 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    SHELL=/bin/bash

# hadolint ignore=DL3008,DL3009
# hadolint ignore=DL3008
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        gcc \
        make \
        sudo && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# hadolint ignore=DL3013
# Install project dependencies
RUN pip3 install pipenv==2018.11.26

# Create non-root run user
RUN adduser app --disabled-password --gecos "" && \
    mkdir /app && \
    chown app:app /app

# Copy files necessary to install project dependencies
COPY --chown=app:app Pipfile Pipfile.lock /app/
WORKDIR /app

# Install packages using pipenv
RUN pipenv install --sequential --ignore-pipfile --system

# Copy an entrypoint script
COPY ./entrypoint.sh /tmp/entrypoint.sh
RUN chmod +x /tmp/entrypoint.sh
ENTRYPOINT ["/tmp/entrypoint.sh"]

# Set working directory and run user
WORKDIR /app
USER app
