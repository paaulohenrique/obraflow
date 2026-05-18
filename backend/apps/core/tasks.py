from config.celery import app


@app.task(bind=True, max_retries=3, default_retry_delay=60)
def example_core_task(self):
    """Placeholder — replace with real core tasks as needed."""
    pass
