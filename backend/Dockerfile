FROM python:3.12-slim

# Install GDAL and spatial libraries for GeoDjango
RUN apt-get update && apt-get install -y \
    gdal-bin \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    binutils \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

# Install GDAL Python binding pinned to the system GDAL version
RUN pip install --no-cache-dir GDAL==$(gdal-config --version) && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
