from mangum import Mangum
from app.server import app

_mangum = Mangum(app, lifespan="auto")


def handler(event, context):
    # Direct async invocation for Battle Buddy jobs (not from API Gateway)
    if "battle_buddy_job" in event:
        from app.battle_buddy_worker import process_job
        process_job(event["battle_buddy_job"])
        return
    return _mangum(event, context)
