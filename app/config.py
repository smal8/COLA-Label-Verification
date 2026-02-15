import os

from fastapi.templating import Jinja2Templates

# Resolve paths relative to the project root (one level up from app/).
# This ensures templates and static files are found regardless of where uvicorn is invoked.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Shared Jinja2Templates instance used by route modules to render HTML.
# Loaded from the templates/ directory at the project root.
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
