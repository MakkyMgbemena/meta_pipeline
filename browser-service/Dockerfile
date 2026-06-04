# 1. Use the official Selenium image to fix the "no such file" binary error
FROM selenium/standalone-chrome:latest

# 2. Switch to root to install Python and your logic
USER root
RUN apt-get update && apt-get install -y python3 python3-pip

WORKDIR /app

# 3. Use your tweak to ensure pip installs requirements without system blocks
COPY requirements.txt .
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

# 4. Copy the rest of your agent code
COPY . .

# 5. Selenium standalone uses port 4444, matching your Cloud Run health check
EXPOSE 4444

# 6. Start the Selenium Server using the official entry point
CMD ["/opt/bin/entry_point.sh"]