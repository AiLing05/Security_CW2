# Ruth — viva and manual verification

Use the local demo accounts documented in README. Passwords are in ignored `.env.ruth-demo`; do not show that file in recordings or screenshots. Log out between accounts, or use separate browser profiles. Record the actual result for every step. The following is a demonstration script, not a claim that browser screenshots have already been captured.

## Five-minute demonstration script

1. **Explain the policy (30 seconds).** “The application already had three roles. My contribution enforces them consistently and adds ownership and approval-state checks. Approved assets are shared. Editors can propose changes only to their own assets.” Show the matrix.
2. **Legitimate editor action (60 seconds).** Sign in as `ruth_demo_editor`. Open that user's labelled asset. Change its title/description without choosing an image. Save. Show the pending version and the unchanged approved title/file. Capture `01-editor-pending.png`.
3. **Admin approval (45 seconds).** Sign in as `ruth_demo_admin`. Review the pending request and approve it. Reopen the asset and show the new metadata with the same image. Capture `02-admin-approved.png`.
4. **Ownership restriction (45 seconds).** Sign in as `ruth_demo_other`. Open the first editor's approved asset. Show that the Edit button is absent. Explain that hiding the button is usability; backend tests also attempt direct PUT/PATCH/request_update and expect denial. Capture `03-other-editor.png`.
5. **Read-only access (30 seconds).** Sign in as `ruth_demo_viewer`. Show an approved asset and download/preview it. Show that edit/upload/admin actions are unavailable. Capture `04-viewer.png`.
6. **API security evidence (60 seconds).** Run the Ruth test command below. Show cross-owner denials, role-management restrictions, pending-version filtering and successful metadata-only tests. Explain which responses are 401, 403, 404 or 405. Capture `05-test-results.png` without credentials.
7. **Limits (30 seconds).** “Approved assets are shared by design. There is no private-sharing feature. Local HTTP is a preview configuration. The team must integrate and retest before submission.”

```powershell
python -m pytest assets/tests/test_authorization.py assets/tests/test_metadata_updates.py assets/tests/test_rbac_security.py -v
```

## Manual test record template

| ID | Actor and action | Expected result | Actual result / screenshot |
|---|---|---|---|
| M01 | Owner editor changes metadata without image | Pending version; approved asset/file unchanged | Fill during demonstration |
| M02 | Admin approves M01 | New metadata published; existing image kept | Fill during demonstration |
| M03 | Other editor opens owner's shared approved asset | Read allowed; edit button absent | Fill during demonstration |
| M04 | Viewer opens and previews/downloads approved asset | Read succeeds; write/admin actions absent | Fill during demonstration |
| M05 | Direct cross-owner PUT/PATCH/request_update | 403 and no asset change | Automated tests plus optional API capture |
| M06 | Viewer reads another user's pending/rejected version or file | 404; draft absent from lists/nested versions | Automated tests plus optional API capture |
| M07 | Editor/viewer attempts role change, including staff editor | 403; target role unchanged | Automated tests plus optional API capture |
| M08 | Viewer attempts tag/version deletion | 403; record retained | Automated tests; baseline had 204 |
| M09 | Existing admin token after database demotion | No admin API access | Automated test |

## Questions to prepare

- **Authentication versus authorization?** Authentication identifies the user; authorization decides whether that identified user can perform a specific action on a specific object.
- **Horizontal versus vertical bypass?** Editing another editor's asset is horizontal; a viewer deleting versions or changing roles is vertical.
- **Why not just hide buttons?** A user can send requests independently of the frontend. The backend must enforce every rule.
- **Why filter querysets and nested versions?** Detail checks alone do not hide list results or related draft metadata.
- **Why trust `uploaded_by`?** It is assigned from the authenticated server-side user. Requests cannot transfer ownership.
- **Why not trust the JWT role?** Tokens can outlive role changes. The policy reads the current database role.
- **Why optional file?** Metadata changes do not require replacing stored content. Keeping the current file preserves the editor approval workflow and avoids unnecessary uploads.
- **What is still the team's responsibility?** Review policy and PR, integrate other modules, run the secure deployment and group vulnerability scan, assemble the final report, and perform the individual viva.

Before submission, add genuine screenshots and your own explanations. Never label planned manual steps as completed evidence.
