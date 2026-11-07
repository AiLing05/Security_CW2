# Baseline observations and provenance

Baseline: GitHub `main` commit `3f90043` (before Ruth's permission fixes). The existing application already contained Admin/Editor/Viewer roles, assets, versions, JWT authentication, an approval UI, audit logging and file validation. Those features are not claimed as Ruth's original implementation.

The first isolated run in this work session used Django's runner and three tests subsequently retained in `assets/tests/test_authorization.py`. All three failed because requests that should have been denied succeeded:

| Test | Observed before | Expected after |
|---|---|---|
| Editor PATCH to another uploader's asset | HTTP 200 | HTTP 403; asset unchanged |
| Viewer DELETE tag | HTTP 204 | HTTP 403; tag retained |
| Viewer DELETE version | HTTP 204 | HTTP 403; version retained |

Command used:

```powershell
python manage.py test assets.tests.test_authorization --settings=dam_backend.settings_test --verbosity=1
```

Recorded terminal summary: `Ran 3 tests`, `FAILED (failures=3)`. This note transcribes that actual session output; it is not an original screenshot or a claim that the final source still reproduces the weakness. The tests checked response status first, so baseline persistence is not asserted here; successful HTTP responses were directly observed. Final regression tests also assert unchanged database state on denial.

Further source review found unfiltered pending-version metadata, staff-based user management, an unrestricted legacy parent-upload path, and direct editor updates that bypassed the approval UI. They were treated as investigation items until covered by post-fix tests. A separate pre-fix exploit run for each of these was not captured; do not claim otherwise in the report.

The original audit integration run had four failures and one error because upload fixtures omitted the required category. The fixtures now provide a category and version-submission fixtures use the asset's actual editor owner. No logging features were reimplemented or attributed to Ruth.

Final execution results are in the accompanying XML files and verification summary. Screenshots must be captured separately during the manual demonstration.
