FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && \
    apt-get install -y \
    sudo \
    wget \
    vim \
    xvfb \
    x11-utils && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Upgrade pip and install Python dependencies
RUN pip install --upgrade pip
COPY ./requirements.txt /requirements.txt
RUN pip install -r /requirements.txt

# Set up working directory and add files
WORKDIR /work
COPY ./start.sh /start.sh
RUN chmod +x /start.sh

# Remove carriage return characters from start.sh (for Windows compatibility)
RUN sed -i 's/\r$//' /start.sh

# Run the start script
CMD ["/start.sh"]
