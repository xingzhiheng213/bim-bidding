"""Demo Celery task for phase 0.1 acceptance."""
from celery_app import app


@app.task
def hello(name: str = "world") -> dict:
    """Return a greeting message."""
    return {"message": f"Hello, {name}!"}
