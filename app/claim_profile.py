"""
Claimant Profile — schema + DynamoDB CRUD.

The profile is the single source of truth for everything we know about
a veteran: service history, claims, denials, appeal deadlines, benefits.
It is built incrementally as documents are processed.
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import Any

import boto3
from boto3.dynamodb.types import TypeDeserializer

_table = boto3.resource("dynamodb", region_name="us-east-1").Table("ValorAssist-ClaimantProfiles")

# ── Empty profile template ───────────────────────────────────────────

def empty_profile(user_id: str) -> dict:
    return {
        "user_id": user_id,
        "updated_at": int(time.time()),
        "personal": {},          # name, dob, ssn_last4, address, phone
        "service": [],           # [{branch, entry_date, sep_date, mos, discharge, deployments}]
        "claims": [],            # [{claim_number, filed_date, conditions, status, rating, decision_date, denial_reason}]
        "appeals": [],           # [{claim_number, denial_date, deadline, type, status, draft}]
        "benefits": {
            "awarded": [],       # [{name, amount, effective_date}]
            "available": [],     # [{name, eligibility, how_to_claim, cfr_cite}]
        },
        "documents": [],         # [{s3_key, filename, doc_type, processed_at}]
        "notes": "",             # free-form extracted notes
    }


# ── DynamoDB helpers ─────────────────────────────────────────────────

def get_profile(user_id: str) -> dict:
    item = _table.get_item(Key={"user_id": user_id}).get("Item")
    return item or empty_profile(user_id)


def save_profile(profile: dict) -> None:
    profile["updated_at"] = int(time.time())
    _table.put_item(Item=profile)


def merge_extracted(user_id: str, extracted: dict) -> dict:
    """
    Deep-merge extracted document data into the existing profile.
    Lists are appended (deduped by key fields); scalars overwrite if non-empty.
    """
    profile = get_profile(user_id)

    # Scalar sections — only overwrite if extracted value is non-empty
    for key in ("personal", "notes"):
        val = extracted.get(key)
        if val:
            if isinstance(val, dict):
                profile[key] = {**profile.get(key, {}), **{k: v for k, v in val.items() if v}}
            else:
                profile[key] = val

    # List sections — append new items, dedupe by natural key
    _merge_list(profile, extracted, "service",
                key_fn=lambda x: f"{x.get('branch','')}{x.get('entry_date','')}")
    _merge_list(profile, extracted, "claims",
                key_fn=lambda x: x.get("claim_number", ""))
    _merge_list(profile, extracted, "appeals",
                key_fn=lambda x: x.get("claim_number", ""))

    # Benefits sub-lists
    benefits = extracted.get("benefits", {})
    _merge_list(profile["benefits"], benefits, "awarded",
                key_fn=lambda x: x.get("name", ""))
    _merge_list(profile["benefits"], benefits, "available",
                key_fn=lambda x: x.get("name", ""))

    # Compute appeal deadlines for any denied claims missing a deadline
    _compute_appeal_deadlines(profile)

    save_profile(profile)
    return profile


def _merge_list(target: dict, source: dict, key: str, key_fn) -> None:
    existing = {key_fn(x): x for x in target.get(key, [])}
    for item in source.get(key, []):
        k = key_fn(item)
        if k and k in existing:
            existing[k].update({kk: vv for kk, vv in item.items() if vv})
        elif item:
            existing[k or str(len(existing))] = item
    target[key] = list(existing.values())


def _compute_appeal_deadlines(profile: dict) -> None:
    """Add/update appeal deadline for denied claims (1 year from decision date)."""
    appealed = {a.get("claim_number") for a in profile.get("appeals", [])}
    for claim in profile.get("claims", []):
        if claim.get("status") == "denied" and claim.get("claim_number") not in appealed:
            decision = claim.get("decision_date", "")
            deadline = ""
            if decision:
                try:
                    dt = datetime.strptime(decision, "%Y-%m-%d")
                    deadline = (dt + timedelta(days=365)).strftime("%Y-%m-%d")
                except ValueError:
                    pass
            profile["appeals"].append({
                "claim_number": claim.get("claim_number", ""),
                "denial_date": decision,
                "deadline": deadline,
                "type": "",
                "status": "not_filed",
                "draft": "",
            })


def update_field(user_id: str, field_path: str, value) -> dict:
    """
    Update a single field in the claimant profile using dot-notation path.
    Supports array indexing: e.g. "service[0].branch", "claims[1].status"
    Returns the updated profile.
    """
    import re

    profile = get_profile(user_id)

    def _set(obj, parts):
        if not parts:
            return
        part = parts[0]
        rest = parts[1:]

        # Array index: e.g. "service[0]"
        arr_match = re.match(r"^(\w+)\[(\d+)\]$", part)
        if arr_match:
            key, idx = arr_match.group(1), int(arr_match.group(2))
            if key not in obj or not isinstance(obj[key], list):
                obj[key] = []
            while len(obj[key]) <= idx:
                obj[key].append({})
            if rest:
                _set(obj[key][idx], rest)
            else:
                obj[key][idx] = value
        else:
            if rest:
                if part not in obj or not isinstance(obj[part], dict):
                    obj[part] = {}
                _set(obj[part], rest)
            else:
                obj[part] = value

    # Split path: "service[0].branch" → ["service[0]", "branch"]
    parts = re.split(r"\.", field_path)
    _set(profile, parts)
    save_profile(profile)
    return profile
