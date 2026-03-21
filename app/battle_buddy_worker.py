"""
Battle Buddy async worker.
Invoked directly by Lambda (InvocationType=Event).
Loads the claimant's profile, injects it as context, runs claude-opus-4-5
with extended thinking, writes result to DynamoDB.
"""
import json
import logging
import boto3

logger = logging.getLogger(__name__)
_dynamo = boto3.resource("dynamodb", region_name="us-east-1")
_table = _dynamo.Table("ValorAssist-BattleBuddyJobs")


def _profile_context(user_id: str) -> str:
    """Serialize the claimant profile into a compact context block."""
    try:
        from app.claim_profile import get_profile
        p = get_profile(user_id)
        if not p.get("service") and not p.get("claims"):
            return ""
        return f"<claimant_profile>\n{json.dumps(p, default=str, indent=2)}\n</claimant_profile>"
    except Exception as e:
        logger.warning("Could not load profile for %s: %s", user_id, e)
        return ""


def process_job(job: dict) -> None:
    job_id = job["job_id"]
    question = job["question"]
    history = job.get("conversation_history") or []
    user_id = job.get("user_id", "")

    try:
        from app.rag_chain import RAGChain
        profile_ctx = _profile_context(user_id)
        result = RAGChain().battle_buddy(
            question=question,
            conversation_history=history,
            profile_context=profile_ctx,
        )
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
