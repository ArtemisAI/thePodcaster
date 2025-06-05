from mangum import Mangum
from backend.app.main import app as fastapi_app

handler = Mangum(fastapi_app, lifespan="off")
