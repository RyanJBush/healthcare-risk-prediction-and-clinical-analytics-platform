# HIPAA-Adjacent Design Notes (Synthetic Demo)

> Cerberus operates on synthetic data today. This document outlines production-oriented controls for protected health information (PHI)-adjacent workflows.

## 1) PHI inventory and de-identification

Potential PHI-like fields in a production migration:
- `full_name`
- medical-record-style identifiers
- timestamps tied to individual encounters
- quasi-identifiers (age, geolocation, rare condition combinations)

De-identification strategy:
- **Tokenization:** replace direct identifiers with irreversible or vault-backed tokens before model features are generated.
- **k-anonymity policy:** enforce minimum cohort size (`k>=11`) on exported analytics; generalize/suppress quasi-identifiers when bins are too sparse.
- **Date shifting/windowing:** convert exact event timestamps to coarse bins for non-clinical analytics.

## 2) Audit log design

Recommended table:

```sql
CREATE TABLE audit_log (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NULL,
  action VARCHAR(128) NOT NULL,
  record_id VARCHAR(128) NULL,
  timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  ip_address INET NULL
);
```

Guidance:
- Log all create/update/view/export/auth events.
- Forward immutable logs to SIEM/WORM storage.
- Add correlation/request IDs for forensic tracing.

## 3) Encryption controls

- **At rest:** AES-256 disk encryption for database volumes, cloud KMS-managed keys, and rotation policies.
- **In transit:** TLS 1.2+ for client/API and service/service traffic; mTLS between internal services where feasible.
- **Secrets:** credentials in a secrets manager; no plaintext keys in source control.

## 4) Access control roles and permissions

- **Clinician:** view assigned patients, add notes/observations, run risk workflows.
- **Admin:** all clinician permissions plus user provisioning, threshold/config changes, and access grants.
- **Auditor:** read-only access to logs, model cards, and compliance reports; no clinical record mutation.

Operational practices:
- Enforce least privilege.
- Use short-lived JWTs and refresh policies.
- Require reason-for-access and periodic entitlement review.
