"""Module-level ASGI app for hosts that do not call the factory themselves."""

from app.main import create_app

app = create_app()
