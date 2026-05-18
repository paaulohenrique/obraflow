from config.celery import app


@app.task
def send_welcome_email(user_id: str):
    """Placeholder — implement email sending when notifications app is ready."""
    pass
