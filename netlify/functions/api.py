import sys
import os

# During build, backend/ is copied into this directory
_backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
if os.path.isdir(_backend_dir):
    sys.path.insert(0, _backend_dir)

from mangum import Mangum
from main import app

handler = Mangum(app)
