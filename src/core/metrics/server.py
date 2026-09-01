from prometheus_client import start_http_server

from core.logger import logger


def start_metrics_server(port: int, app_name: str) -> None:
    """Starts the Prometheus HTTP server in a background thread.

    Args:
        port (int): The network port to expose the /metrics endpoint.
        app_name (str): Identifier for logging (e.g., 'bot', 'worker').
    """
    try:
        start_http_server(port)
        logger.info(f"[{app_name}] Prometheus metrics server started on port {port}")
    except Exception:
        logger.exception(
            f"[{app_name}] Failed to start Prometheus metrics server on port {port}"
        )
