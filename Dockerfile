# Use official Python image as base
FROM python:3.11-slim

# Install Tkinter dependencies
RUN apt-get update && apt-get install -y \
	tk \
	libtk8.6 \
	libtcl8.6 \
	libgl1 \
	libglib2.0-0 \
	&& rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements.txt if exists, else skip
COPY requirements.txt ./

# Install dependencies if requirements.txt exists
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

# Copy project files
COPY . .

# Set default command to run your script
CMD ["python", "360foto.py"]
