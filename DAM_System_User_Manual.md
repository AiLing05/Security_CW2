# Secure Digital Asset Management (DAM) System
## User Manual

**Project repository:** [Security_CW2](https://github.com/AiLing05/Security_CW2)

---

## 1. Introduction

The Digital Asset Management (DAM) System is a web application for uploading, organising, searching and managing digital files. Assets can be stored with information such as titles, descriptions, categories and tags.

The system has three user roles: **Administrator**, **Editor** and **Viewer**. Each role has different permissions.

This manual explains how to use the main features available in the application.

## 2. Accessing the System

1. Open the DAM System website in a web browser.
2. Enter your username and password on the login page.
3. Select **Sign In**.
4. After a successful login, the system opens the Dashboard.

If you do not have an account, contact the system administrator.

### Logging out

1. Select **Logout** on the navigation bar.
2. Wait until the system returns to the login page.

Always log out when using a shared computer.

## 3. User Roles

| Function | Administrator | Editor | Viewer |
|---|---:|---:|---:|
| View assets permitted by the system | Yes | Yes | Yes |
| Upload assets | Yes | Yes | No |
| Edit assets | All assets | Own assets | No |
| Delete assets | Yes | No | No |
| Submit asset updates | Yes | Own assets | No |
| Approve or reject submitted versions | Yes | No | No |
| Manage user accounts | Yes | No | No |
| Create or modify categories and tags | Yes | No | No |
| View security monitoring | Yes | No | No |

Editors can also access their own unpublished assets and versions. Viewers are limited to approved assets.

## 4. Dashboard

After signing in, the Dashboard provides an overview of the DAM System.

It includes:
- Total Assets
- Categories
- Tags
- Recent Uploads
- Quick Actions

The available Quick Actions depend on the signed-in user's role.

Use the navigation bar to move between **Dashboard**, **Assets** and **Metadata**. Administrators also have links to **Update Requests**, **Manage Users** and **Security**.

## 5. Managing Assets

### 5.1 Viewing assets

1. Select **Assets** from the navigation bar.
2. Browse the assets available to your account.
3. Select **View Details** on an asset to open its details page.

The assets shown depend on your role and the asset's approval status.

### 5.2 Uploading an asset

Uploading is available to Administrators and Editors.

1. Open the **Assets** page.
2. Find the **Upload New Asset** section.
3. Enter an asset title.
4. Add a description if required.
5. Select a category.
6. Add a tag if required.
7. Choose a file or drag it into the upload area.
8. Submit the upload.
9. Wait for the success or error message.

The application validates uploaded files. The frontend recognises these file types for preview:

- **Images:** JPG, JPEG, PNG, WEBP, GIF, BMP and SVG
- **Videos:** MP4 and WEBM
- **Documents:** PDF
- **3D models:** GLB, GLTF and USDZ

The backend also performs file validation. A file that fails validation will not be accepted.

### 5.3 Previewing an asset

1. Find the asset on the Assets page.
2. Select **Preview**.
3. The file opens using the available preview method.

Image, video, PDF and supported 3D model files have preview support. For a 3D model, use the viewer controls to rotate and inspect the model.

### 5.4 Viewing and downloading a file

1. Open the asset using **View Details**.
2. Locate the file and its available controls.
3. Select **Download** where the option is displayed.

File access is handled through protected endpoints. You must be signed in and have permission to access the asset.

## 6. Searching Asset Metadata

The **Metadata** page allows users to search for assets.

1. Select **Metadata** from the navigation bar.
2. Enter a title or description in the search field.
3. Choose a category or tag if required.
4. Enter a **Date From** or **Date To** value if you want to filter by upload date.
5. Select **Search**.
6. Review the results.

Search results can be browsed using the pagination controls. Open an asset with **View Details** to see more information or use the available preview and download options.

## 7. Asset Details and Versions

### 7.1 Viewing asset details

1. Open an asset using **View Details**.
2. Review its title, description, category and tags.
3. Scroll to the version history to see the available versions and their statuses.

### 7.2 Editing asset information

Administrators can edit assets. Editors can edit assets they own.

1. Open the asset details page.
2. Select **Edit Metadata**.
3. Update the available information.
4. If you want to replace the file, select a new file. Leave the file field empty if you only want to change metadata.
5. Save or submit the changes.

An Editor's update is submitted for administrator review. Administrators can make permitted changes directly.

### 7.3 Submitting and reviewing versions

When an Editor submits an update to an asset they own, the change is kept as a pending version for review.

Administrators can review pending versions from the **Update Requests** page or the asset's version history.

Version statuses are:

- **Pending:** Waiting for administrator review.
- **Approved:** Accepted by an administrator.
- **Rejected:** Not accepted by an administrator.

## 8. Administrator Functions

### 8.1 Reviewing update requests

1. Sign in with an Administrator account.
2. Select **Update Requests**.
3. Choose the **Pending** filter to view requests awaiting review.
4. Select **View Asset** to inspect the related asset.
5. Preview the submitted changes if needed.
6. Select **Approve** or **Reject**.

The **Approved** and **Rejected** filters can be used to review requests that have already been processed.

### 8.2 Managing users

1. Select **Manage Users**.
2. Use the form to create a new user or edit an existing user.
3. Enter the required account details.
4. Select the user's role: Admin, Editor or Viewer.
5. Save the changes.

Administrators can also delete user accounts. The system prevents an administrator from deleting their own account or removing their own administrator access through the user-management functions.

### 8.3 Managing categories and tags

Administrators can create or modify categories and tags used to organise assets. Use the relevant category or tag controls in the application and save the changes.

## 9. Security Monitoring

The **Security** page is available to Administrators.

1. Sign in with an Administrator account.
2. Select **Security** from the navigation bar.
3. Review the security summary and recorded events.

The dashboard includes information such as:
- Successful logins
- Failed logins
- Security activity trends
- IP addresses associated with failed login attempts
- Usernames associated with failed login attempts
- Recorded security events

Administrators can filter events by category, severity and actor. Use the pagination controls to view additional records.

## 10. Troubleshooting

| Problem | Possible reason | What to do |
|---|---|---|
| Login fails | Username or password is incorrect | Check your login details and try again. |
| Login attempts are restricted | Too many login attempts were made | Wait before trying again. |
| File upload is rejected | File type or file content did not pass validation | Check the file and try a supported format. |
| Cannot edit an asset | Your role does not allow the action, or you do not own the asset | Contact the administrator if you need access. |
| An asset or version cannot be found | It may not be visible to your role or may be unavailable | Check your permissions and the asset status. |
| An update is still pending | An administrator has not reviewed it yet | Wait for the administrator to review the request. |
| User Management is unavailable | The account is not an Administrator | Contact the system administrator. |
| Security page is unavailable | The account is not an Administrator | Contact the system administrator. |
| A file preview does not open | The file may be unavailable or access may be restricted | Refresh the page and try again. |

## 11. Security Recommendations

- Keep your username and password private.
- Do not share your account with other users.
- Use only the functions permitted by your role.
- Upload files that are required for the system's intended use.
- Do not attempt to access assets that you are not authorised to view.
- Log out after using the system, especially on a shared device.
- Report unexpected access problems or suspicious activity to the administrator.

## 12. Conclusion

The DAM System provides a shared place to upload, organise, search and manage digital assets. Its role-based permissions control which actions each user can perform. Following this manual will help users navigate the application and use its features appropriately.

---

**Note:** The available pages and actions may depend on the user's role and the current system configuration.
