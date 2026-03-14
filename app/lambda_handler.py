from mangum import Mangum
from app.server import app

handler = Mangum(app, lifespan="auto")
