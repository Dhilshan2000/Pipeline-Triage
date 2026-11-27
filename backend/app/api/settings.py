from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from app.database import get_async_db
from app.security.crypto import encrypt_credential, decrypt_credential

router = APIRouter(prefix="/api/settings", tags=["Settings"])

class AdapterSettingsUpdate(BaseModel):
    key: str # 'gitlab' | 'github'
    enabled: bool
    config: Dict[str, Any]

class ConnectorSettingsUpdate(BaseModel):
    type: str # 'mcp' | 'rest' | 'email'
    name: str # 'kanvaro' | 'slack' | 'jira'
    enabled: bool
    config: Dict[str, Any]

@router.get("/adapters")
async def list_adapters():
    db = get_async_db()
    adapters = await db.adapter_settings.find({}).to_list(length=10)
    for a in adapters:
        a["id"] = str(a.pop("_id"))
        # Mask secrets in UI response
        if "credentials" in a:
            for k in a["credentials"]:
                a["credentials"][k] = "••••••••••••"
    return {"adapters": adapters}

@router.post("/adapters")
async def save_adapter_settings(req: AdapterSettingsUpdate):
    db = get_async_db()
    # Encrypt secret values before persisting
    encrypted_creds = {}
    for k, v in req.config.items():
        if "token" in k or "secret" in k:
            encrypted_creds[k] = encrypt_credential(str(v))

    doc = {
        "key": req.key,
        "enabled": req.enabled,
        "config": req.config,
        "encrypted_credentials": encrypted_creds
    }
    await db.adapter_settings.update_one({"key": req.key}, {"$set": doc}, upsert=True)
    return {"status": "saved", "key": req.key}

@router.get("/connectors")
async def list_connectors():
    db = get_async_db()
    connectors = await db.connector_settings.find({}).to_list(length=20)
    for c in connectors:
        c["id"] = str(c.pop("_id"))
        if "encrypted_credentials" in c:
            c["has_credentials"] = True
            c.pop("encrypted_credentials", None)
    return {"connectors": connectors}

@router.post("/connectors")
async def save_connector_settings(req: ConnectorSettingsUpdate):
    db = get_async_db()
    encrypted_creds = {}
    clean_config = {}
    for k, v in req.config.items():
        if any(s in k.lower() for s in ("token", "secret", "password", "webhook_url")):
            encrypted_creds[k] = encrypt_credential(str(v))
            clean_config[k] = "••••••••" if v else ""
        else:
            clean_config[k] = v

    doc = {
        "type": req.type,
        "name": req.name.lower().strip(),
        "enabled": req.enabled,
        "config": clean_config,
        "encrypted_credentials": encrypted_creds
    }
    await db.connector_settings.update_one({"name": doc["name"]}, {"$set": doc}, upsert=True)
    return {"status": "saved", "name": doc["name"]}

@router.delete("/connectors/{name}")
async def delete_connector_settings(name: str):
    db = get_async_db()
    await db.connector_settings.delete_one({"name": name.lower().strip()})
    return {"status": "deleted", "name": name}

@router.get("/users")
async def list_users():
    db = get_async_db()
    users = await db.users.find({}, {"password_hash": 0}).to_list(length=50)
    for u in users:
        u["id"] = str(u.pop("_id"))
    return {"users": users}
