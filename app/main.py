from datetime import datetime
import logging
import os
import socket
import ssl
import sys
import time

from prometheus_client import Counter, Gauge, start_http_server
import requests
import yaml

# Get log level from environment variable
log_level_name = os.getenv("LOG_LEVEL", "ERROR")  # Default to 'ERROR' if not set

# Convert the log level name to a logging level
log_level = getattr(logging, log_level_name.upper(), logging.ERROR)


# Setup logging to a file with INFO level and a specific format
logging.basicConfig(
    stream=sys.stdout,
    level=log_level,
    format="%(asctime)s %(levelname)s:%(message)s",
)


# Gauge for measuring HTTP request latency
http_requests_gauge = Gauge(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["url", "region", "name"],
)

# Gauge for HTTP status code
# In Prometheus, gauges are typically used for values that can go up and down, like temperatures or memory usage
http_status_gauge = Gauge(
    "http_response_status_code",
    "HTTP response status code",
    ["url", "region", "name"],
)

# Counter to track HTTP response status codes
http_status_counter = Counter(
    "http_response_status_code_counter",
    "Count of HTTP response status codes",
    ["url", "region", "name", "status_code"],
)


# Gauge for checking if a specific string is found in the HTTP response
string_match_gauge = Gauge(
    "http_response_string_match",
    "Indicates if a specific string is found in the HTTP response",
    ["url", "region", "name", "search_string"],
)

# Gauge for checking if the SSL certificate is valid
ssl_valid_gauge = Gauge(
    "ssl_certificate_valid",
    "Indicates if the SSL certificate is valid (1) or not (0)",
    ["url", "region", "name"],
)

# Gauge for counting the number of days until SSL certificate expiration
ssl_expiry_gauge = Gauge(
    "ssl_certificate_expiry_days",
    "Number of days until the SSL certificate expires",
    ["url", "region", "name"],
)


# Function to perform various checks on a given URL
def check_url(
    url, name, check_ssl=False, search_string=None, http_status_region="London"
):
    try:
        http_status_region
        # Perform an HTTP get request
        response = requests.get(url, timeout=10, allow_redirects=False)
        # Update HTTP request latency gauge
        http_requests_gauge.labels(url=url, region=http_status_region, name=name).set(
            response.elapsed.total_seconds()
        )

        logging.info(f"{name} url: {url}")
        logging.info(f"{name} status_code: {response.status_code}")

        # Increment the counter for the received status code
        http_status_counter.labels(
            url=url,
            region=http_status_region,
            name=name,
            status_code=response.status_code,
        ).inc()

        # Set the HTTP status code gauge
        http_status_gauge.labels(url=url, region=http_status_region, name=name).set(
            response.status_code
        )

        # If a search string is provided, check for its presence in the response
        if search_string:
            match_found = search_string in response.text
            string_match_gauge.labels(
                url=url,
                region=http_status_region,
                name=name,
                search_string=search_string,
            ).set(1 if match_found else 0)

            logging.info(f"{name} body: {response.text}")

        # Check SSL certificate if required and the URL is HTTPS
        if check_ssl and url.startswith("https://"):
            ssl_valid, days_until_expiry = check_ssl_certificate(url)
            ssl_valid_gauge.labels(url=url, region=http_status_region, name=name).set(
                1 if ssl_valid else 0
            )
            ssl_expiry_gauge.labels(url=url, region=http_status_region, name=name).set(
                days_until_expiry
            )

        return

    # Handle specific exceptions and log them
    except requests.exceptions.Timeout:
        logging.warning(f"Timeout occurred while fetching {url}")
        # Handle timeout specific logic here
    except requests.exceptions.ConnectionError:
        logging.error(f"Connection error occurred while fetching {url}")
        # Handle connection error specific logic here
    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP error occurred while fetching {url}: {e}")
        # Handle HTTP error specific logic here
    except requests.exceptions.TooManyRedirects:
        logging.error(f"Too many redirects occurred while fetching {url}")
        # Handle redirect error specific logic here
    except requests.exceptions.RequestException as e:
        logging.error(f"General error occurred while fetching {url}: {e}")
        # Handle other request exceptions here
    # Set gauges to a default error value in case of an exception
    http_requests_gauge.labels(url=url, region=http_status_region, name=name).set(-1)
    http_status_counter.labels(
        url=url, region=http_status_region, name=name, status_code="error"
    ).inc()
    http_status_gauge.labels(url=url, region=http_status_region, name=name).set(-1)


# Function to check the SSL certificate of a URL
def check_ssl_certificate(url):
    try:
        # Extract hostname from URL
        hostname = url.split("//")[-1].split("/")[0]
        # Establish a context for SSL
        context = ssl.create_default_context()
        with socket.create_connection((hostname, 443)) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                # Get SSL certificate
                cert = ssock.getpeercert()

        # Calculate the number of days until the certificate expires
        expiry_date = datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z")
        days_until_expiry = (expiry_date - datetime.now()).days
        return True, days_until_expiry
    except Exception as e:
        logging.error(f"SSL certificate validation error for {url}: {e}")
        return False, -1.0


# Function to load configuration from a YAML file
def load_config(filename):
    # Open and read the YAML file
    with open(filename, "r") as file:
        # Parse the YAML file and return the content
        return yaml.safe_load(file)


# Main execution block
if __name__ == "__main__":
    # Start a server to expose the metrics
    start_http_server(8000)

    # Get the directory in which the script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Construct the absolute path for config.yaml
    config_path = os.path.join(script_dir, "config.yaml")

    # Load configuration from the specified YAML file
    config = load_config(config_path)

    # Extract the 'urls_to_monitor' list from the loaded configuration
    urls_to_monitor = config["sites"]

    # Extract the 'region' loaded configuration
    http_status_region = config.get("region", "London")

    # Main loop to continuously check the URLs
    while True:
        # Iterate over each site in the list
        for site in urls_to_monitor:
            # Ensure mandatory fields 'url' and 'name' are present
            url = site.get("url")
            name = site.get("name")
            if not url or not name:
                logging.error(
                    f"'url' and 'name' are mandatory. Missing in entry: {site}"
                )
                continue

            # Perform checks on the URL
            check_url(
                url,
                name,
                site.get(
                    "check_ssl", False
                ),  # Get 'check_ssl', default to False if not present
                site.get(
                    "search_string", None
                ),  # Get 'search_string', default to None if not present
                http_status_region,
            )
        # Wait for 60 seconds before the next iteration of the loop
        time.sleep(config.get("sleep", 60))
