# Step 1: Use an official lightweight Python base image
FROM python:3.12-slim

# Step 2: Set the working directory inside the container
WORKDIR /app

# Step 3: Install system dependencies required by your project
# psycopg2-binary needs postgresql-client for database connectivity
RUN apt-get update && apt-get install -y postgresql-client && rm -rf /var/lib/apt/lists/*

# Step 4: Copy the requirements file and install Python packages
# This is done in a separate step to leverage Docker's build cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Step 5: Copy the rest of your application's code into the container
COPY . .

# Step 6: Make the startup script executable
RUN chmod +x ./entrypoint.sh

# Step 7: Set the entrypoint for the container
ENTRYPOINT ["./entrypoint.sh"]
