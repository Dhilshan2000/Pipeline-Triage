import json
import logging
from fastapi import APIRouter, Request, HTTPException, Header, Depends
from redis import Redis
from rq import Queue
from app.config import settings
from app.database import get_async_db
from app.adapters.registry import adapter_registry
from app.models.event import FailureRef, RunStat

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/webhooks", tags=["Webhooks"])

def get_redis_queue():
    try:
        r = Redis.from_url(settings.REDIS_URL)
        return Queue("failures", connection=r)
    except Exception as e:
        logger.warning(f"Could not connect to Redis: {e}")
        return None

@router.post("/gitlab")
async def gitlab_webhook(request: Request):
    """
    Step 1: Ingests GitLab pipeline, build, and merge request webhooks.
    Verifies secret, stores delivery under unique key, pushes to Redis queue, answers 200 immediately.
    """
    body = await request.body()
    headers = dict(request.headers)
    adapter = adapter_registry.get("gitlab")

    # 1. Secret verification
    if not adapter.verify(headers, body, settings.GITLAB_WEBHOOK_SECRET):
        raise HTTPException(status_code=401, detail="Invalid GitLab webhook secret token")

    parsed = adapter.parse(headers, body)
    if not parsed:
        return {"status": "ignored", "reason": "Not an event of interest"}

    db = get_async_db()

    # 2. If it's a successful run or merged MR -> record light run_stat
    if isinstance(parsed, RunStat):
        await db.run_stats.insert_one(parsed.model_dump())
        return {"status": "counted", "kind": parsed.kind}

    # 3. If it's a failure event -> dedupe on event_key & queue background worker
    if isinstance(parsed, FailureRef):
        existing_delivery = await db.deliveries.find_one({"event_key": parsed.event_key})
        if existing_delivery:
            logger.info(f"Duplicate delivery ignored for {parsed.event_key}")
            return {"status": "duplicate_delivery_ignored", "event_key": parsed.event_key}

        # Save delivery
        await db.deliveries.insert_one({
            "event_key": parsed.event_key,
            "platform": parsed.platform,
            "project": parsed.project,
            "pipeline_id": parsed.pipeline_id,
            "job_id": parsed.job_id,
            "created_at": parsed.raw_payload.get("created_at")
        })

        # Enqueue background job (RQ)
        q = get_redis_queue()
        job_payload = {
            "platform": parsed.platform,
            "event_key": parsed.event_key,
            "project": parsed.project,
            "pipeline_id": parsed.pipeline_id,
            "job_id": parsed.job_id,
            "raw_payload": parsed.raw_payload
        }

        if q:
            from app.worker import process_failure_job
            q.enqueue(process_failure_job, job_payload)
            logger.info(f"Enqueued job to Redis for {parsed.event_key}")
        else:
            # Inline fallback if redis not present during local testing
            from app.worker import process_failure_job
            process_failure_job(job_payload)

        return {"status": "enqueued", "event_key": parsed.event_key}

@router.post("/github")
async def github_webhook(request: Request):
    """
    Step 1: Ingests GitHub Actions workflow_run and workflow_job webhooks.
    Verifies HMAC-SHA256 signature, stores delivery, enqueues to Redis queue.
    """
    body = await request.body()
    headers = dict(request.headers)
    adapter = adapter_registry.get("github")

    if not adapter.verify(headers, body, settings.GITHUB_WEBHOOK_SECRET):
        raise HTTPException(status_code=401, detail="Invalid GitHub HMAC-SHA256 signature")

    parsed = adapter.parse(headers, body)
    if not parsed:
        return {"status": "ignored"}

    db = get_async_db()

    if isinstance(parsed, RunStat):
        await db.run_stats.insert_one(parsed.model_dump())
        return {"status": "counted"}

    if isinstance(parsed, FailureRef):
        existing = await db.deliveries.find_one({"event_key": parsed.event_key})
        if existing:
            return {"status": "duplicate_delivery_ignored", "event_key": parsed.event_key}

        await db.deliveries.insert_one({
            "event_key": parsed.event_key,
            "platform": parsed.platform,
            "project": parsed.project,
            "pipeline_id": parsed.pipeline_id,
            "job_id": parsed.job_id
        })

        q = get_redis_queue()
        job_payload = {
            "platform": parsed.platform,
            "event_key": parsed.event_key,
            "project": parsed.project,
            "pipeline_id": parsed.pipeline_id,
            "job_id": parsed.job_id,
            "raw_payload": parsed.raw_payload
        }
        if q:
            from app.worker import process_failure_job
            q.enqueue(process_failure_job, job_payload)
        else:
            from app.worker import process_failure_job
            process_failure_job(job_payload)

        return {"status": "enqueued", "event_key": parsed.event_key}
