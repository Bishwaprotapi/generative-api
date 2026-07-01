# Use Python 3.13 image as the base
FROM python:3.13.0-slim

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Set the working directory inside the container
WORKDIR /app

# Install all system dependencies (LibreOffice, Poppler, and ODBC drivers)
RUN apt-get update -qq && \
    apt-get install -yq --no-install-recommends \
        libreoffice \
        libreoffice-writer \
        fonts-dejavu \
        fonts-liberation \
        poppler-utils \
        curl \
        gnupg \
        apt-transport-https \
        ca-certificates \
        unixodbc \
        unixodbc-dev \
        libsqliteodbc && \
    # Add Microsoft package repo for ODBC drivers
    curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | apt-key add - && \
    curl -fsSL https://packages.microsoft.com/config/ubuntu/20.04/prod.list \
        -o /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update -qq && \
    ACCEPT_EULA=Y apt-get install -yq msodbcsql17 && \
    # Clean up to reduce image size
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements file first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade "pip<24.1" && \
    pip install --no-cache-dir -r requirements.txt

# Copy all application files to the container
COPY . /app

# Expose port 80 for the application
EXPOSE 80
EXPOSE 443

# Command to run the application on port 80
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]
