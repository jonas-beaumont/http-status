# HTTP-STATUS

This Python script is a prometheus_client monitoring tool designed to periodically check and report on the health and performance of specified HTTP endpoints. It measures HTTP request latencies, tracks response status codes, verifies SSL certificate validity and expiration, and optionally checks for specific strings in response bodies. 

## Getting started

The client requires a `config.yaml` file in the `app` dir. The file is a list of sites you wish to monitor.

| Key            | Description                          | Required | Example                      |
|----------------|--------------------------------------|----------|------------------------------|
| `url`          | The full website address to monitor  | True     | `"https://www.example.com"`  |
| `name`         | The name to the site                 | True     | `example.com`                |
| `search_string`| A string expected on the page        | False    | `example`                    |
| `check_ssl`    | Checks the SSL certificate is valid  | False    | `True` \| `False`            |


*Example*

```
sites:
  - url: "https://www.example.com"
    name: "example"
    search_string: "example"
    check_ssl: True
  - url: "https://demo.example.com"
    name: "demo"
    check_ssl: False
```

## Running the client

* Install requirements

```
python -m pip install --no-cache-dir -r requirements.txt
```

* Execute the script

```
python ./app/main.py
```


## Running the client in Docker

* Create the same  `config.yaml` in the `app` dir.
* Run docker build.

```
docker build -t http-status .
```

```
docker run -d -p 8000:8000 -v ./app/config.yaml:/usr/src/app/config.yaml http-status
```

## Running the client on Kubernetes

The minimum kubernetes resources are installed using the helm chart. The `config.yaml` is not required when running the client in kubernetes because the sites list resides in the `values.yaml` file.

*Example*

In this example the image is pulled from my DockerHub registry.

```
dockerImage: jonasbeaumont/http-status
dockerImageTag: stable
config:
  sites:
    - url: "https://www.example.com"
      name: "example"
      search_string: "example"
      check_ssl: True
    - url: "https://demo.example.com"
      name: "demo"
      check_ssl: False

```

* installing the helm chart

```
helm upgrade --install --namespace monitoring http-status ./helm
```

### Helm limitations

No ingress is provided with the Helm Chart because my use case doesn't require the client to be available output to the namespace. This is because the client is installed in the same kubernetes cluster and namespace as Prometheus.




## Output

## Metrics

| Name                                | Metric Type | Description                                      | Labels                           |
|-------------------------------------|-------------|--------------------------------------------------|----------------------------------|
| `http_request_duration_seconds`     | Gauge       | HTTP request latency in seconds                  | `["url", "name"]`                |
| `http_response_status_code`         | Gauge       | HTTP response status code                        | `["url", "name"]`                |
| `http_response_status_code_counter` | Counter     | Count of HTTP response status codes              | `["url", "name", "status_code"]` |
| `http_response_string_match`        | Gauge       | Indicates if a specific string is found in HTTP response | `["url", "name", "search_string"]` |
| `ssl_certificate_valid`             | Gauge       | Indicates if the SSL certificate is valid (1) or not (0) | `["url", "name"]`                |
| `ssl_certificate_expiry_days`       | Gauge       | Number of days until the SSL certificate expires | `["url", "name"]`                |

### raw output

```
curl http://localhost:8000/

# HELP python_gc_objects_collected_total Objects collected during gc
# TYPE python_gc_objects_collected_total counter
python_gc_objects_collected_total{generation="0"} 497.0
python_gc_objects_collected_total{generation="1"} 124.0
python_gc_objects_collected_total{generation="2"} 0.0
# HELP python_gc_objects_uncollectable_total Uncollectable objects found during GC
# TYPE python_gc_objects_uncollectable_total counter
python_gc_objects_uncollectable_total{generation="0"} 0.0
python_gc_objects_uncollectable_total{generation="1"} 0.0
python_gc_objects_uncollectable_total{generation="2"} 0.0
# HELP python_gc_collections_total Number of times this generation was collected
# TYPE python_gc_collections_total counter
python_gc_collections_total{generation="0"} 55.0
python_gc_collections_total{generation="1"} 5.0
python_gc_collections_total{generation="2"} 0.0
# HELP python_info Python platform information
# TYPE python_info gauge
python_info{implementation="CPython",major="3",minor="11",patchlevel="4",version="3.11.4"} 1.0
# HELP http_request_duration_seconds HTTP request latency in seconds
# TYPE http_request_duration_seconds gauge
http_request_duration_seconds{name="ci",url="https://ci.example.com"} 0.338411
http_request_duration_seconds{name="demo",url="https://demo.example.com"} 0.111639
# HELP http_response_status_code HTTP response status code
# TYPE http_response_status_code gauge
http_response_status_code{name="ci",url="https://ci.example.com"} 200.0
http_response_status_code{name="demo",url="https://demo.example.com"} 200.0
# HELP http_response_status_code_counter_total Count of HTTP response status codes
# TYPE http_response_status_code_counter_total counter
http_response_status_code_counter_total{name="ci",status_code="200",url="https://ci.example.com"} 1.0
http_response_status_code_counter_total{name="demo",status_code="200",url="https://demo.example.com"} 1.0
# HELP http_response_status_code_counter_created Count of HTTP response status codes
# TYPE http_response_status_code_counter_created gauge
http_response_status_code_counter_created{name="ci",status_code="200",url="https://ci.example.com"} 1.706202691873745e+09
http_response_status_code_counter_created{name="demo",status_code="200",url="https://demo.example.com"} 1.7062026920534751e+09
# HELP http_response_string_match Indicates if a specific string is found in the HTTP response
# TYPE http_response_string_match gauge
http_response_string_match{name="ci",search_string="ci",url="https://ci.example.com"} 1.0
# HELP ssl_certificate_valid Indicates if the SSL certificate is valid (1) or not (0)
# TYPE ssl_certificate_valid gauge
ssl_certificate_valid{name="ci",url="https://ci.example.com"} 1.0
ssl_certificate_valid{name="demo",url="https://demo.example.com"} 1.0
# HELP ssl_certificate_expiry_days Number of days until the SSL certificate expires
# TYPE ssl_certificate_expiry_days gauge
ssl_certificate_expiry_days{name="ci",url="https://ci.example.com"} 369.0
ssl_certificate_expiry_days{name="demo",url="https://demo.example.com"} 369.0
```

## Example prometheus config

### Scrape Configs

```
- job_name: "http-status"
  scrape_interval: 30s
  static_configs:
    - targets: [http-status]
```

### Prometheus rules


```
- name: http-status
  rules:
    ##############################################################################################
    # Check if the status code has changed in 5 minutes
    ##############################################################################################
    - alert: HTTPStatusCodeChange
    expr: changes(http_response_status_code[5m]) > 0
    for: 5m
    labels:
        severity: warning
    annotations:
        summary: "HTTP status code change detected"
        description: "HTTP status code for {{ $labels.url }} has changed in the last 5 minutes"

    ##############################################################################################
    # Check if string is not found
    # The check applies only to app1 and app2. If 
    ##############################################################################################
    - alert: HTTPResponseStringMatchFalse
    expr: http_response_string_match{name=~"app1|app2"} != 1
    for: 5m
    labels:
        severity: warning
    annotations:
        summary: "HTTP body string match false"
        description: "HTTP body for {{ $labels.url }} does not contain {{ $labels.search_string }}"

    ##############################################################################################
    # Check if string is found
    # The check excludes app1 and app2
    ##############################################################################################
    - alert: HTTPResponseStringMatchTrue
    expr: http_response_string_match{name!~"app1|app2"} != 0
    for: 5m
    labels:
        severity: warning
    annotations:
        summary: "HTTP body string match true"
        description: "HTTP body for {{ $labels.url }} does contain {{ $labels.search_string }}"

    ##############################################################################################
    # Check if the SSL certificate is valid
    ##############################################################################################
    - alert: SSLCertificateNotValid
    expr: ssl_certificate_valid{} != 1
    for: 5m
    labels:
        severity: warning
    annotations:
        summary: "Invalid SSL certificate detected"
        description: "SSL certificate for {{ $labels.url }} is invalid"

    ##############################################################################################
    # Check if SSL certificate is due to expire in the next 61 to 90 days
    ##############################################################################################
    - alert: SSLCertificateExpiryDays90
    expr: ssl_certificate_expiry_days{} <= 90 and ssl_certificate_expiry_days{} > 60
    for: 5m
    labels:
        severity: info
    annotations:
        summary: "SSL certificate expirying"
        description: "SSL certificate for {{ $labels.url }} expirying in less than 90 days"

    ##############################################################################################
    # Check if SSL certificate is due to expire in the next 31 to 60 days
    ##############################################################################################
    - alert: SSLCertificateExpiryDays60
    expr: ssl_certificate_expiry_days{} <= 60 and ssl_certificate_expiry_days{} > 30
    for: 5m
    labels:
        severity: warning
    annotations:
        summary: "SSL certificate expirying"
        description: "SSL certificate for {{ $labels.url }} expirying in less than 60 days"

    ##############################################################################################
    # Check if SSL certificate is due to expire in the next 30 days
    ##############################################################################################
    - alert: SSLCertificateExpiryDays30
    expr: ssl_certificate_expiry_days{} <= 30
    for: 5m
    labels:
        severity: critical
    annotations:
        summary: "SSL certificate expirying"
        description: "SSL certificate for {{ $labels.url }} expirying in less than 30 days"
```