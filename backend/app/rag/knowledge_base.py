import uuid
import logging
from typing import List, Dict, Any, Optional
from qdrant_client.http import models as qmodels
from app.rag.qdrant_client import get_qdrant_client, COLLECTION_NAME
from app.rag.embeddings import compute_local_embedding

logger = logging.getLogger(__name__)

SEED_KNOWLEDGE_CHUNKS = [
    {
        "source_type": "runbook",
        "title": "Resolving Disk Space and No space left on device in CI/CD Runners",
        "category": "Deployment / server",
        "text": (
            "When deploy jobs fail with 'No space left on device', the docker runner host has exhausted inodes or disk blocks. "
            "Remediation: 1. Run 'docker system prune -af --volumes' on the target server. "
            "2. Set up a daily cron cleanup job for old containers and dangling images. "
            "3. Increase the server disk volume size and alert when usage exceeds 85%."
        ),
        "reference": "runbooks/devops/disk-cleanup.md"
    },
    {
        "source_type": "runbook",
        "title": "Resolving Docker Registry Authentication and Denied Errors",
        "category": "Docker registry",
        "text": (
            "When image push jobs fail with 'denied: access forbidden' or 'unauthorized: authentication required', "
            "the CI credentials have expired or the registry token secret is outdated. "
            "Remediation: 1. Rotate the registry service account token in GitLab/GitHub CI/CD Variables. "
            "2. Verify 'docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY' succeeds. "
            "3. Ensure the service account has push permissions to the target repository namespace."
        ),
        "reference": "runbooks/devops/registry-auth.md"
    },
    {
        "source_type": "runbook",
        "title": "Resolving Dependency Version Conflicts and Lockfile Errors",
        "category": "Dependency problem",
        "text": (
            "When npm or pip fails with 'ERESOLVE unable to resolve dependency tree' or 'No matching distribution found', "
            "transitive dependencies conflict with pinned top-level versions. "
            "Remediation: 1. Inspect package.json or requirements.txt for incompatible version constraints. "
            "2. Run 'npm install --package-lock-only' or regenerate the lockfile locally with clean cache. "
            "3. Commit the updated lockfile (package-lock.json or poetry.lock)."
        ),
        "reference": "runbooks/engineering/dependency-conflicts.md"
    },
    {
        "source_type": "sonar_rule",
        "title": "SonarQube Quality Gate Coverage and New Issues Requirements",
        "category": "SonarQube quality gate",
        "text": (
            "Trainee quality gate requires Coverage on New Code >= 80% and New Issues = 0. "
            "When the gate fails: 1. Inspect the SonarQube web dashboard for uncovered lines and highlighted bugs/vulnerabilities. "
            "2. Write unit tests targeting the new code paths until coverage exceeds 80%. "
            "3. Fix all reported code smells, bugs, and security hotspots before re-running the pipeline."
        ),
        "reference": "sonarqube/rules/trainee-gate.md"
    },
    {
        "source_type": "runbook",
        "title": "Remediating Security Scan Secrets and Vulnerabilities",
        "category": "Security scan",
        "text": (
            "When Gitleaks, Trivy, or Snyk fails the pipeline due to a detected secret or vulnerable dependency: "
            "1. Immediately rotate the compromised credential in the external service (AWS, GitHub, API key). "
            "2. Use git-filter-repo or BFG Repo-Cleaner to completely scrub the secret from git commit history. "
            "3. If a CVE is detected, upgrade the affected package to the patched upstream version."
        ),
        "reference": "runbooks/security/secret-rotation.md"
    }
]

class KnowledgeBase:
    def __init__(self):
        self._seeded = False

    def seed_knowledge(self):
        """Seeds initial runbooks and documentation into Qdrant if empty."""
        client = get_qdrant_client()
        if not client or self._seeded:
            return

        try:
            count = client.count(collection_name=COLLECTION_NAME).count
            if count == 0:
                logger.info("Seeding initial runbooks and Sonar rules into Qdrant...")
                points = []
                for chunk in SEED_KNOWLEDGE_CHUNKS:
                    point_id = str(uuid.uuid4())
                    vec = compute_local_embedding(f"{chunk['title']} {chunk['category']} {chunk['text']}")
                    points.append(
                        qmodels.PointStruct(
                            id=point_id,
                            vector=vec,
                            payload=chunk
                        )
                    )
                client.upsert(collection_name=COLLECTION_NAME, points=points)
                logger.info(f"Successfully seeded {len(points)} knowledge chunks.")
            self._seeded = True
        except Exception as e:
            logger.warning(f"Could not seed Qdrant knowledge base: {e}")

    def search(self, query: str, category: Optional[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
        """Hybrid RAG retrieval returning relevant runbooks, docs, and past fixes."""
        client = get_qdrant_client()
        if not client:
            # Fallback to local filtering of seed chunks if Qdrant container is not reachable
            return [c for c in SEED_KNOWLEDGE_CHUNKS if not category or c.get("category") == category][:limit]

        query_vec = compute_local_embedding(query)
        try:
            filter_query = None
            if category and category != "needs review":
                filter_query = qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="category",
                            match=qmodels.MatchValue(value=category)
                        )
                    ]
                )

            results = client.search(
                collection_name=COLLECTION_NAME,
                query_vector=query_vec,
                query_filter=filter_query,
                limit=limit
            )
            return [hit.payload for hit in results if hit.payload]
        except Exception as e:
            logger.warning(f"Qdrant vector search failed, using memory fallback: {e}")
            return [c for c in SEED_KNOWLEDGE_CHUNKS if not category or c.get("category") == category][:limit]

    def add_resolved_fix(self, issue_id: str, title: str, category: str, resolution_notes: str):
        """Adds a resolved failure back into Qdrant so the system continuously learns."""
        client = get_qdrant_client()
        if not client:
            return

        try:
            chunk = {
                "source_type": "resolved_failure",
                "title": f"Past Resolved Failure: {title}",
                "category": category,
                "text": resolution_notes,
                "reference": f"issue://{issue_id}"
            }
            point_id = str(uuid.uuid4())
            vec = compute_local_embedding(f"{title} {category} {resolution_notes}")
            client.upsert(
                collection_name=COLLECTION_NAME,
                points=[qmodels.PointStruct(id=point_id, vector=vec, payload=chunk)]
            )
            logger.info(f"Learned resolved fix for issue {issue_id} and stored in Qdrant.")
        except Exception as e:
            logger.warning(f"Failed to record resolved fix in Qdrant: {e}")

knowledge_base = KnowledgeBase()
