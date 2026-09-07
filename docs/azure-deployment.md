# Production and Azure Deployment Guide

**Status:** deployment procedure complete; Azure deployment not performed  
**Recommended topology:** Azure Static Web Apps + Azure Container Apps + Azure
Database for PostgreSQL Flexible Server

This is the intentionally small production topology for the existing modular
monolith:

```text
browser
  -> Azure Static Web Apps (React/Vite dist)
  -> Azure Container Apps (FastAPI, public read API)
       -> Azure Database for PostgreSQL Flexible Server
       -> Azure Container Apps Job (migration and scheduled collection)
```

It does not add Kubernetes, Redis, Celery, or a second backend service. Azure
Container Apps jobs are used for finite migration/collection commands; the API
container remains a continuously running HTTP service.

## 1. Credentials and values you need

| Value | Where it comes from | Secret? |
|---|---|---|
| Azure subscription ID | Azure account/subscription | No |
| Resource group and region | Chosen during setup | No |
| Container Registry name/login server | Azure Container Registry | No |
| PostgreSQL server FQDN/database/admin user | PostgreSQL Flexible Server | User is sensitive operational data |
| PostgreSQL password | Generated once and stored in a password manager/Key Vault | Yes |
| `DATABASE_URL` | Built from PostgreSQL values with TLS verification | Yes |
| `ADMIN_TOKEN` | Random high-entropy value | Yes |
| `DUFFEL_ACCESS_TOKEN` | Duffel production account, only when approved | Yes |
| web-source permission reference/profile | Your written permission and reviewed profile | Sensitive operational config |
| Static Web Apps deployment token or CI identity | Azure/GitHub deployment setup | Yes |

You need an active Azure subscription for hosted resources. Local Docker and
PostgreSQL do not require an Azure subscription.

## 2. Production prerequisites

- Azure CLI signed in to the intended tenant and subscription;
- Docker or an Azure build path;
- a globally unique registry/server naming prefix;
- a real production frontend origin;
- a PostgreSQL password and independent random admin token;
- a cost budget/alert before resource creation;
- an approved source contract before any `LIVE` collection.

Use explicit task variables rather than shell-wide system names:

```bash
export APIX_RESOURCE_GROUP=airfare-apix-prod
export APIX_LOCATION=centralindia
export APIX_REGISTRY=replacewithuniqueacrname
export APIX_CONTAINER_ENV=airfare-apix-env
export APIX_BACKEND_APP=airfare-apix-api
export APIX_MIGRATION_JOB=airfare-apix-migrate
export APIX_COLLECTION_JOB=airfare-apix-collect
export APIX_PG_SERVER=replacewithuniquepgname
export APIX_PG_DATABASE=airfare_apix
export APIX_PG_ADMIN=apix_admin
```

Do not paste passwords or provider tokens into shell history. Enter them through
the Azure portal, Key Vault, protected CI secrets, or a non-echoing prompt.

## 3. Provision the resource boundary

```bash
az login
az account set --subscription replace-with-subscription-id
az extension add --name containerapp --upgrade
az group create --name "$APIX_RESOURCE_GROUP" --location "$APIX_LOCATION"
az acr create --resource-group "$APIX_RESOURCE_GROUP" \
  --name "$APIX_REGISTRY" --sku Basic
az containerapp env create --resource-group "$APIX_RESOURCE_GROUP" \
  --name "$APIX_CONTAINER_ENV" --location "$APIX_LOCATION"
```

Create PostgreSQL Flexible Server through the Azure portal or current CLI, then
create the `airfare_apix` database. Prefer private networking when the hosting
environment and your experience allow it. If public access is used for an MVP,
allow only the smallest required network scope—never `0.0.0.0/0` as a permanent
rule.

The SQLAlchemy URL shape is:

```text
postgresql+psycopg://USER:PERCENT_ENCODED_PASSWORD@SERVER.postgres.database.azure.com:5432/airfare_apix?sslmode=verify-full
```

Azure PostgreSQL requires encrypted connections. Use `verify-full` and the
recommended trusted root-certificate configuration; use `require` only as a
temporary diagnostic if certificate verification is being repaired.

## 4. Build and publish the backend image

The existing `backend/Dockerfile` is the image source. Tag every release with a
unique immutable identifier rather than relying on `latest`:

```bash
export APIX_RELEASE_TAG=2026-09-06.1
az acr build --registry "$APIX_REGISTRY" \
  --image "airfare-apix-backend:$APIX_RELEASE_TAG" backend
```

Before deployment, scan the repository and image inputs for `.env` files,
tokens, credentials, exports containing restricted raw payloads, and local
database dumps.

## 5. Store configuration and secrets

Create these Container Apps secrets (prefer Key Vault references where
available):

- `database-url` -> production `DATABASE_URL`;
- `admin-token` -> random production `ADMIN_TOKEN`;
- `duffel-access-token` -> only if the production source is approved.

Non-secret environment values:

```text
APP_ENV=production
COLLECTION_TIMEZONE=Asia/Kolkata
SCHEDULER_ENABLED=false
SCHEDULED_SOURCE=fixture
CORS_ORIGINS=["https://replace-with-frontend-host"]
DUFFEL_SOURCE_ENABLED=false
DUFFEL_SOURCE_APPROVED=false
WEB_SOURCE_ENABLED=false
WEB_SOURCE_APPROVED=false
```

Keep the in-process scheduler off in the HTTP app. A scheduled Container Apps
job provides one execution boundary and avoids duplicate schedules when the API
scales beyond one replica.

## 6. Run migrations as a finite job

Create a manual Container Apps job using the same backend image, secret-backed
`DATABASE_URL`, one replica, zero parallelism beyond that replica, and command:

```text
alembic -c alembic.ini upgrade head
```

Start it once for each release, inspect its exit status/logs, and only then
update the API revision. Never let several API replicas race database
migrations during startup.

Required acceptance evidence:

```text
migration job completed with exit code 0
alembic current reports the repository head
```

## 7. Deploy the FastAPI container

Deploy the immutable backend image to Azure Container Apps with:

- external ingress enabled;
- target port `8000`;
- at least one replica for judging/demo availability;
- secret references for `DATABASE_URL` and `ADMIN_TOKEN`;
- startup and liveness probes on `/health`;
- readiness probe on `/ready`;
- HTTPS only;
- administrative endpoints protected at the application and perimeter layer.

The production command should omit development reload:

```text
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

If a custom API domain is used, bind an Azure managed certificate after DNS is
correct. Record the final API origin for the frontend build.

## 8. Schedule collection separately

Create a scheduled Container Apps job from the same image with one replica,
retry limit matching the application's bounded policy, and a command that runs
one intended source/date collection and exits. Before switching from fixture to
a real source:

1. attach the approved source review and credential/permission reference;
2. run one manual job with `RECORDED_DEMO` or the explicitly intended class;
3. verify raw quote, normalized observation, source health, and index exclusion
   or inclusion status;
4. enable the schedule;
5. verify two consecutive scheduled executions without overlap.

Do not label a run `LIVE` merely because it ran in Azure.

## 9. Deploy React without Next.js

The frontend stays React + Vite. Build-time configuration must contain the
final HTTPS API origin:

```bash
VITE_API_BASE_URL=https://replace-with-api-host npm --prefix frontend run build
```

Deploy `frontend/dist` to Azure Static Web Apps. Configure its build as:

```text
app_location: frontend
output_location: dist
app_build_command: npm run build
```

Add a Static Web Apps navigation fallback so `/routes`, `/provenance`, and
`/operations` serve `index.html` on direct refresh. Set the exact frontend URL
in backend `CORS_ORIGINS`; do not use `*` with administrative access.

## 10. Deployment acceptance

Run these checks against the production URLs:

```bash
export APIX_PUBLIC_API=https://replace-with-api-host
curl -fsS "$APIX_PUBLIC_API/health"
curl -fsS "$APIX_PUBLIC_API/ready"
curl -fsS "$APIX_PUBLIC_API/api/v1/routes"
curl -fsS "$APIX_PUBLIC_API/api/v1/index/current?data_class=SYNTHETIC"
```

Then verify:

- HTTPS certificate and hostname validation succeed;
- direct refresh works on all four React routes;
- browser console has no CORS, mixed-content, or API errors;
- admin request without a token is rejected;
- admin token is absent from frontend assets and network requests;
- migration head matches the release;
- database and source failures change `/ready`/operations evidence honestly;
- scheduled job has exactly one run for one intended date/source;
- logs contain no secrets or unrestricted raw payload dumps;
- the selected backup retention is recorded and a restore drill is scheduled.

## 11. Backups, rollback, and cost control

Azure PostgreSQL Flexible Server provides automatic backups and point-in-time
restore within the configured retention window. Choose retention and redundancy
deliberately, document them, and test a restore into a separate server before
claiming disaster recovery readiness. Use `pg_dump` as an additional portable
export when policy permits.

Rollback order:

1. stop the scheduled collection job;
2. route the API to the previous immutable container revision when schema
   compatibility permits;
3. investigate rather than automatically downgrading Alembic migrations;
4. restore PostgreSQL to a new server only for confirmed data loss/corruption;
5. rebind the secret-backed connection string and repeat readiness checks.

Configure Azure cost alerts and remove unused test resource groups after
validation. Never assume the free tier or pricing remains unchanged; verify the
current Azure pricing page before provisioning.

## 12. Honest current status

- ✅ Local Docker + PostgreSQL deployment is running and verified.
- ✅ The code has production-compatible environment boundaries and health URLs.
- ✅ This Azure procedure is complete and uses the current modular architecture.
- ⬜ Azure resources have not been created.
- ⬜ Azure connectivity, TLS, backup restore, and hosted browser acceptance are
  therefore unverified.
- ⬜ Genuine `LIVE` collection remains blocked by the separate Phase 4 external
  credential/permission gate.

## Official operational references

- [Azure Container Apps containers](https://learn.microsoft.com/en-us/azure/container-apps/containers)
- [Azure Container Apps jobs](https://learn.microsoft.com/en-us/azure/container-apps/jobs)
- [Container Apps health probes](https://learn.microsoft.com/en-us/azure/container-apps/health-probes)
- [Container Apps secret management](https://learn.microsoft.com/en-us/azure/container-apps/manage-secrets)
- [Deploy a React app to Static Web Apps](https://learn.microsoft.com/en-us/azure/static-web-apps/deploy-react)
- [Azure PostgreSQL TLS configuration](https://learn.microsoft.com/en-us/azure/postgresql/security/security-tls-how-to-connect)
- [Azure PostgreSQL backup and restore](https://learn.microsoft.com/en-us/azure/postgresql/backup-restore/concepts-backup-restore)

