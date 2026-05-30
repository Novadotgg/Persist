from prometheus_client import Counter, Histogram, Gauge

# Define Prometheus metrics for system observability
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total number of HTTP requests processed",
    ["method", "endpoint", "status_code"]
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request processing duration in seconds",
    ["method", "endpoint"]
)

AI_GENERATION_LATENCY_SECONDS = Histogram(
    "ai_generation_latency_seconds",
    "AI model generation latency in seconds",
    ["model", "provider"]
)

DRAMATIQ_QUEUE_DEPTH = Gauge(
    "dramatiq_queue_depth",
    "Current number of messages waiting in the Dramatiq queue",
    ["queue_name"]
)
