"""
Battle Buddy async worker.
Invoked directly by Lambda (InvocationType=Event) — not through API Gateway.
Runs the claude-opus-4-5 extended-thinking call and writes the result to DynamoDB.
"""
import logging
import boto3

logger = logging.getLogger(__name__)
_dynamo = boto3.resource("dynamodb", region_name="us-east-1")
_table = _dynamo.Table("ValorAssist-BattleBuddyJobs")


def process_job(job: dict) -> None:
    job_id = job["job_id"]
    question = job["question"]
    history = job.get("conversation_history") or []

    try:
        from app.rag_chain import RAGChain
        result = RAGChain().battle_buddy(question=question, conversation_history=history)
        _table.update_item(
            Key={"job_id": job_id},
            UpdateExpression="SET #s = :s, answer = :a, model = :m",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":s": "done", ":a": result.answer, ":m": result.model},
        )
        logger.info("Battle Buddy job %s complete", job_id)
    except Exception as exc:
        logger.exception("Battle Buddy job %s failed", job_id)
        _table.update_item(
            Key={"job_id": job_id},
            UpdateExpression="SET #s = :s, #e = :e",
            ExpressionAttributeNames={"#s": "status", "#e": "error"},
            ExpressionAttributeValues={":s": "error", ":e": str(exc)},
        )
