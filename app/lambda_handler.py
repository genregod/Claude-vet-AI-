from mangum import Mangum
from app.server import app

# lifespan="off": Lambda does not support persistent ASGI lifespan events.
# Using "auto" risks 502s if startup handlers raise during cold starts.
_mangum = Mangum(app, lifespan="off")


def handler(event, context):
    # ── Async Battle Buddy chat job ──────────────────────────────────
    if "battle_buddy_job" in event:
        from app.battle_buddy_worker import process_job
        process_job(event["battle_buddy_job"])
        return

    # ── Async document processing job ───────────────────────────────
    if "doc_process_job" in event:
        import boto3
        job = event["doc_process_job"]
        table = boto3.resource("dynamodb", region_name="us-east-1").Table(
            "ValorAssist-BattleBuddyJobs"
        )
        try:
            from app.doc_processor import process_document
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

    # ── Async profile verification turn ─────────────────────────────
    if "verify_job" in event:
        import json
        import time
        import boto3
        job = event["verify_job"]
        table = boto3.resource("dynamodb", region_name="us-east-1").Table(
            "ValorAssist-BattleBuddyJobs"
        )
        try:
            from app.claim_profile import get_profile
            from app.rag_chain import RAGChain

            profile = get_profile(job["user_id"])

            # Retry up to 3 times on rate limit (429)
            last_exc = None
            for attempt in range(3):
                try:
                    result = RAGChain().verify_profile(
                        profile=profile,
                        conversation_history=job.get("conversation_history", []),
                        confirmed_fields=job.get("confirmed_fields", []),
                        skipped_fields=job.get("skipped_fields", []),
                        corrections=job.get("corrections", {}),
                    )
                    last_exc = None
                    break
                except Exception as e:
                    last_exc = e
                    if "429" in str(e) and attempt < 2:
                        time.sleep(15 * (attempt + 1))  # 15s, 30s
                    else:
                        raise

            if last_exc:
                raise last_exc

            # If the AI returned profile_update, apply it immediately
            if result.get("profile_update"):
                from app.claim_profile import update_field
                for field_path, value in result["profile_update"].items():
                    try:
                        update_field(job["user_id"], field_path, value)
                    except Exception as e:
                        import logging
                        logging.getLogger(__name__).warning(
                            "Field update failed %s: %s", field_path, e
                        )

            table.update_item(
                Key={"job_id": job["job_id"]},
                UpdateExpression="SET #s = :s, verify_result = :r",
                ExpressionAttributeNames={"#s": "status"},
                ExpressionAttributeValues={
                    ":s": "done",
                    ":r": json.dumps(result, default=str),
                },
            )
        except Exception as exc:
            import logging
            logging.getLogger(__name__).exception("verify_job %s failed", job["job_id"])
            table.update_item(
                Key={"job_id": job["job_id"]},
                UpdateExpression="SET #s = :s, #e = :e",
                ExpressionAttributeNames={"#s": "status", "#e": "error"},
                ExpressionAttributeValues={":s": "error", ":e": str(exc)},
            )
        return

    # ── HTTP requests via API Gateway ────────────────────────────────
    return _mangum(event, context)
