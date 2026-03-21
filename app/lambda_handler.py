from mangum import Mangum
from app.server import app

_mangum = Mangum(app, lifespan="auto")


def handler(event, context):
    # Async Battle Buddy chat job
    if "battle_buddy_job" in event:
        from app.battle_buddy_worker import process_job
        process_job(event["battle_buddy_job"])
        return
    # Async document processing job
    if "doc_process_job" in event:
        from app.doc_processor import process_document
        import boto3, os
        job = event["doc_process_job"]
        table = boto3.resource("dynamodb", region_name="us-east-1").Table("ValorAssist-BattleBuddyJobs")
        try:
            process_document(job["user_id"], job["s3_key"], job["filename"])
            table.update_item(
                Key={"job_id": job["job_id"]},
                UpdateExpression="SET #s = :s",
                ExpressionAttributeNames={"#s": "status"},
                ExpressionAttributeValues={":s": "done"},
            )
        except Exception as exc:
            table.update_item(
                Key={"job_id": job["job_id"]},
                UpdateExpression="SET #s = :s, #e = :e",
                ExpressionAttributeNames={"#s": "status", "#e": "error"},
                ExpressionAttributeValues={":s": "error", ":e": str(exc)},
            )
        return
    return _mangum(event, context)
