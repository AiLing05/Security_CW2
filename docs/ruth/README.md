# Ruth — authorization contribution

Branch: `feature/rbac-security`. Scope: DAM roles, ownership, approval, protected asset/version reads, and role management. Shared approved assets and owner-only editor changes were selected by Ruth on 7 November 2026. The team should review this policy in the pull request.

## Role-permission matrix

| Action | Admin | Editor | Viewer | Anonymous / inactive / unknown role |
|---|---|---|---|---|
| Read/download approved assets and versions | Yes | Yes | Yes | Deny |
| Read pending/rejected versions | All | Own assets only | Deny | Deny |
| Read assets without an approved version | All | Own only | Deny | Deny |
| Upload new asset with initial file | Yes | Yes; server sets owner | Deny | Deny |
| Edit asset fields or replace its file | Any asset; publish immediately | Own only; pending approval | Deny | Deny |
| Edit metadata without replacement file | Yes | Own only; pending approval | Deny | Deny |
| Delete asset | Yes | Deny | Deny | Deny |
| Submit version | Any asset | Own asset only | Deny | Deny |
| Approve/reject pending version | Yes | Deny | Deny | Deny |
| Overwrite submitted version with PUT / create directly with POST | Deny; use submission workflow | Deny | Deny | Deny |
| Delete version | Yes | Deny | Deny | Deny |
| Read category/tag dictionary | Yes | Yes | Yes | Deny |
| Create/change/delete category/tag dictionary | Yes | Deny | Deny | Deny |
| Assign existing category/tags | Yes | Own assets | Deny | Deny |
| Manage users and application roles | Yes | Deny, including staff editors | Deny | Deny |
| Change Django system privileges through REST | Deny | Deny | Deny | Deny |

An application admin cannot remove their own access via REST or modify a superuser unless they are a superuser. Django admin additionally requires Django staff/model permissions and the application admin role. Approved assets intentionally have shared visibility; there is no per-asset private/share field. JSON `metadata` and `parent` changes are not supported through editor version requests; title, description, category, tags and optional file are supported.

## Run tests

In the project folder (PowerShell execution policy does not affect these commands):

```powershell
python -m pytest assets/tests/test_authorization.py assets/tests/test_metadata_updates.py assets/tests/test_rbac_security.py -v
python -m pytest assets/tests audit/tests dam_backend/test_infrastructure.py -q
python -m pytest assets/tests audit/tests dam_backend/test_infrastructure.py --ds=dam_backend.settings_test_postgres -q
```

SQLite tests are isolated from `.env` and the application DB. PostgreSQL tests use `.env` credentials and create/destroy only `test_ruth_authorization`; keep this name reserved for tests. The PostgreSQL role must be able to create test databases. Do not run simultaneous PostgreSQL test suites against that same test database.

If scripts are enabled, `./test-ruth.ps1`, `./test-ruth.ps1 -Full`, and `./test-ruth.ps1 -Full -Postgres` also save JUnit XML to `evidence/`.

Frontend verification:

```powershell
cd dam_frontend
npm run test:auth
npm run build
```

Stop the development server before the production build: both use `.next`.

## Local demonstration

```powershell
docker compose -f compose.local.yaml up -d --wait
python manage.py migrate
python manage.py seed_ruth_demo
python manage.py runserver 127.0.0.1:8000
```

In a second terminal:

```powershell
cd dam_frontend
npm run dev
```

Open `http://localhost:3000/login` (use `localhost`, matching the frontend CSRF origin). Generated demo passwords are in the ignored `.env.ruth-demo` file. Demo usernames: `ruth_demo_admin`, `ruth_demo_editor`, `ruth_demo_other`, `ruth_demo_viewer`. Seeding never resets existing accounts or overwrites user assets. The separate labelled demo assets can remain for the viva. Never submit `.env`, `.env.ruth-demo`, cookies or JWTs.

The local Docker database listens only on `127.0.0.1:5433`. Local preview uses HTTP. Member 4's HTTPS configuration must be used for the secure demonstration; do not describe this local preview as HTTPS deployment evidence.

## Files to review

- `assets/permissions.py`: role gates, ownership and read visibility.
- `assets/views.py`: user-management protections, version workflow and protected file routes.
- `assets/serializers.py`: filtered nested versions, reduced uploader details, immutable ownership and required initial upload.
- `assets/admin.py`: prevent staff editors bypassing REST through Django admin.
- `assets/tests/test_authorization.py`, `test_metadata_updates.py`, `test_rbac_security.py`: positive/negative security tests.
- `dam_frontend/pages/assets/[id].js`: own-asset edit action and optional replacement file.
- `dam_frontend/pages/assets.js`: available category choices for editors.
- `audit/tests/`: integration fixtures updated for category validation and owner-only submissions. Logging implementation is Member 5's existing work.

`report-section.md` is a report contribution draft to review and incorporate into the group's report. `viva-and-manual-tests.md` gives the individual demonstration and screenshot checklist. No ZAP results, screenshots, lecturer approval or group submission are fabricated by these documents.
