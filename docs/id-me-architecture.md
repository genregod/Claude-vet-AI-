# id.me Integration Architecture

## Overview

id.me provides NIST IAL2-compliant identity verification for veterans. This document outlines how id.me will operate alongside the existing AWS Cognito User Pool.

**Scope:** Identity proofing only. Authentication (sign-in) remains with Cognito. id.me is invoked post-login to elevate a verified veteran's trust level.

---

## Flow

```
User signs in (Cognito/GitHub OAuth)
        │
        ▼
/dashboard loads → checks Cognito attribute custom:idme_verified
        │
        ├─ "true"  → full access
        │
        └─ missing → banner: "Verify your veteran status with id.me"
                            │
                            ▼
                    GET /auth/idme/start
                            │
                            ▼
                    id.me OAuth2 authorization URL
                    (scope: http://idmanagement.gov/ns/assurance/ial/2)
                            │
                            ▼
                    Veteran completes id.me verification
                            │
                            ▼
                    GET /auth/idme/callback?code=...
                            │
                            ▼
                    FastAPI exchanges code → id.me token
                    Validates IAL level ≥ 2
                    Sets Cognito attribute: custom:idme_verified = "true"
                            │
                            ▼
                    Redirect → /dashboard (full access)
```

---

## OAuth 2.0 Authorization Code Flow

### 1. Authorization Request

```
GET https://api.id.me/oauth/authorize
  ?client_id=<IDME_CLIENT_ID>
  &redirect_uri=https://main.dnfalf4ttkc7b.amplifyapp.com/auth/idme/callback
  &response_type=code
  &scope=openid+http://idmanagement.gov/ns/assurance/ial/2
  &state=<csrf_token>
```

### 2. Token Exchange (FastAPI `/auth/idme/callback`)

```python
POST https://api.id.me/oauth/token
  grant_type=authorization_code
  &code=<code>
  &redirect_uri=<redirect_uri>
  &client_id=<IDME_CLIENT_ID>
  &client_secret=<IDME_CLIENT_SECRET>
```

### 3. UserInfo Validation

```python
GET https://api.id.me/api/public/v3/attributes.json
Authorization: Bearer <access_token>
```

Validate response contains `ial` ≥ 2 before setting the Cognito attribute.

---

## Cognito Integration

id.me does **not** replace Cognito. It adds a verified attribute to the existing user.

### Required Cognito User Pool Changes

1. Add custom attribute `custom:idme_verified` (String, mutable, max 5 chars)
2. App Client must have write permission for `custom:idme_verified`

### Setting the Attribute (FastAPI)

```python
cognito_client.admin_update_user_attributes(
    UserPoolId=settings.cognito_user_pool_id,
    Username=user_sub,
    UserAttributes=[{"Name": "custom:idme_verified", "Value": "true"}]
)
```

---

## Environment Variables Required

| Variable | Description |
|---|---|
| `IDME_CLIENT_ID` | id.me OAuth app client ID |
| `IDME_CLIENT_SECRET` | id.me OAuth app client secret (SSM SecureString) |
| `IDME_REDIRECT_URI` | Must match registered callback in id.me dashboard |

---

## IAM Requirements

The `ValorAssist-API` Lambda role needs:

```json
{
  "Action": "cognito-idp:AdminUpdateUserAttributes",
  "Resource": "arn:aws:cognito-idp:us-east-1:973028704465:userpool/us-east-1_2Ec6BMJsE"
}
```

---

## Sandbox vs Production

- **Sandbox:** `https://api.id.me` — use test credentials, no real verification
- **Production:** Requires id.me partnership agreement and security review
- Scope changes: sandbox uses `military` scope; production uses full IAL2 scope

---

## Out of Scope (This Sprint)

- id.me Group verification (VSO membership)
- MFA via id.me (Cognito handles MFA)
- Attribute sharing beyond IAL level and veteran status
