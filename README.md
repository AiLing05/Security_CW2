# Security Enhancements for Digital Asset Management System

A full-stack Digital Asset Management (DAM) System developed using **Django REST Framework, Next.js and PostgreSQL**, enhanced with security controls to protect digital assets, user accounts and application infrastructure.

This project was developed for **6000CMD / 6005CEM – Security CW2: Secure Application Development and Implementation**.

## 1. Project Overview

The DAM System allows users to upload, manage, search, preview and download digital assets. It supports asset metadata, version control, administrative approval workflows and role-based access control (RBAC).

The security enhancement project addresses vulnerabilities identified in the original application through secure authentication, authorisation, input validation, encrypted communication, security monitoring and vulnerability testing.

## 2. Technology Stack

### Frontend
- Next.js (React)
- Chakra UI
- Redux Toolkit
- Axios

### Backend
- Python
- Django
- Django REST Framework
- SimpleJWT
- PostgreSQL
- Django Admin

### Security and Testing
- Argon2 password hashing
- JWT authentication and refresh-token rotation
- HTTPS/TLS 1.3 using Caddy
- PostgreSQL TLS
- Pytest
- OWASP ZAP
- Bandit
- pip-audit
- npm audit

## 3. User Roles and Permissions

The application supports three roles:

| Role | Permissions |
|---|---|
| **Admin** | Manage users and roles, manage assets, and approve or reject update requests |
| **Editor** | Upload assets, manage authorised assets and submit update requests |
| **Viewer** | View and download approved assets |

Permissions are enforced through backend role and asset-ownership checks. Frontend role information is used for interface presentation and does not replace server-side authorisation.

## 4. Core Application Features

- Secure user registration, login and logout
- Drag-and-drop asset uploads
- Asset metadata management, including titles, descriptions, categories and tags
- Asset search, filtering and pagination
- Asset preview and download
- Asset version history
- Editor update requests
- Administrator approval and rejection workflows
- User and role management
- Security audit logs and monitoring dashboard

## 5. Implemented Security Enhancements

### 5.1 Authentication and JWT Security

- Argon2 password hashing
- Django password-strength validation
- Login throttling limited to five attempts per minute
- Protection against spoofed `X-Forwarded-For` headers in the tested local configuration
- JWT access-token expiration after five minutes
- Refresh-token expiration after one day
- Refresh-token rotation and blacklisting
- Secure logout through refresh-token invalidation
- Backend administrator permission checks
- Authentication regression testing

**Note:** Logging out invalidates the submitted refresh token. Previously issued access tokens remain valid until their expiration.

### 5.2 Role-Based Access Control (RBAC)

- Server-side role and ownership validation
- Restricted asset modification and deletion
- Protection against unauthorised asset-version changes
- Administrator-only user and role management
- Approval workflow authorisation
- Prevention of tested privilege-escalation and unauthorised-access scenarios

### 5.3 Input Validation and File Protection

- Server-side file extension validation
- MIME type and file-signature verification
- Maximum upload size of 50 MB
- Category and tag input validation
- UUID-based stored filenames
- Protected file access and download endpoints
- Secure error handling
- Protection against tested unsafe uploads and unauthorised file access

File validation reduces upload risks but does not replace comprehensive malware scanning.

### 5.4 Infrastructure and Communication Security

- HTTPS with TLS 1.3 through Caddy
- Environment-based configuration for sensitive settings
- Secure, HttpOnly and SameSite cookie settings
- HTTP security headers
- CORS and CSRF protection
- PostgreSQL TLS with certificate verification
- Dependency vulnerability assessment and remediation
- Production-oriented Django security configuration

Infrastructure security controls were verified in the local testing environment. Production deployment requires separate validation.

### 5.5 Security Logging and Monitoring

- Security event logging for authentication and asset operations
- User activity and access-denial monitoring
- Append-only audit-log protection
- SHA-256 hash-chain integrity checks
- Sensitive-data redaction and log-injection protection
- Suspicious activity detection and alerts
- Administrator-restricted monitoring dashboard
- Audit-log retention configuration

Monitoring includes detection of suspicious login activity, access probing and potentially destructive operations.

## 6. Security Testing

The enhanced application was assessed using automated and manual security testing.

| Testing Method | Purpose |
|---|---|
| Pytest | Authentication, authorisation, file validation and logging regression tests |
| OWASP ZAP | Dynamic vulnerability assessment |
| Bandit | Python static security analysis |
| pip-audit | Python dependency vulnerability assessment |
| npm audit | Frontend dependency vulnerability assessment |
| Manual API testing | Authentication, access control, input handling and security behaviour |
| Integration testing | Verify security controls after combining group members' changes |

The project report documents **20 security findings**, remediation activities and **18 successful live integration retests**.

Testing was performed in the local environment and does not guarantee that the application is free from vulnerabilities.

## 7. Local Development Setup

### Prerequisites

- Python
- Node.js and npm
- PostgreSQL
- Git

### 7.1 Clone the Repository

```bash
git clone <repository-url>
cd <repository-folder>
```

Replace the placeholders with the project's actual repository URL and directory.

### 7.2 Backend Setup

Navigate to the Django backend directory:

```powershell
cd backend
```

Create and activate a Python virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install backend dependencies:

```powershell
pip install -r requirements.txt
```

Configure PostgreSQL and the environment variables required by the backend.

Generate a secure Django secret key for the current PowerShell session:

```powershell
$env:DJANGO_SECRET_KEY = python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

For local development only:

```powershell
$env:DJANGO_DEBUG = "True"
$env:DJANGO_ALLOWED_HOSTS = "localhost,127.0.0.1"
```

Run database migrations:

```powershell
python manage.py migrate
```

Verify Django configuration:

```powershell
python manage.py check
```

Start the backend:

```powershell
python manage.py runserver
```

The `.env.example` file documents configuration variables but is not automatically loaded by Django. Set the required values according to the project's configuration.

### 7.3 Frontend Setup

Open another terminal and navigate to the frontend directory:

```powershell
cd frontend
```

Install dependencies:

```powershell
npm install
```

Start the development server:

```powershell
npm run dev
```

The frontend is normally accessible at:

```text
http://localhost:3000
```

Configure the frontend API address according to the backend and HTTPS setup used.

## 8. Running Security Tests

Activate the backend virtual environment and run the authentication security tests:

```powershell
python -m pytest assets/tests/test_authentication.py -v
```

Run the complete backend test suite:

```powershell
python -m pytest -v
```

Run Python security checks:

```powershell
bandit -r . 
pip-audit
```

Run frontend dependency auditing from the frontend directory:

```powershell
npm audit
```

OWASP ZAP testing requires a running application and an appropriately configured scan target. Active scanning should only be performed against an authorised test environment.

## 9. Security Configuration Notes

- Never commit actual passwords, secret keys, certificates, private keys or `.env` files.
- Use strong, randomly generated Django secret keys.
- Keep `DJANGO_DEBUG` disabled in production.
- Configure allowed hosts, CORS, CSRF and trusted proxy settings for the deployment environment.
- Protect PostgreSQL credentials and database access.
- Use trusted TLS certificates in production.
- Keep Python and npm dependencies updated.
- Restrict access to security logs and administrative endpoints.
- Do not assume that local security-test results guarantee production security.
- Treat previously committed secrets as potentially exposed and rotate them where necessary.

Changing the Django secret key can invalidate existing JWTs and other cryptographic signatures. Coordinate secret-key rotation across the development team.

## 10. Limitations and Future Improvements

Although the implemented controls improve application security, several limitations remain:

- JWT access tokens remain valid until expiration.
- File validation cannot detect every malicious file.
- Privileged database access may compromise locally stored audit evidence.
- Production infrastructure and proxy configurations require additional testing.

Recommended future improvements include stronger token revocation, malware scanning, external audit-log storage, production penetration testing and continuous dependency monitoring.

## 11. Project Contributors

Developed by students from **INTI International College Penang**, 3+0 Bachelor of Science (Hons) in Computer Science, in collaboration with Coventry University, UK.

| Contributor | Security Responsibility |
|---|---|
| Nurul Ashwin Farhah | Authentication and JWT Security |
| Preetikalaxmy Ruth | Role-Based Access Control and Asset Authorisation |
| Koay Ai Ling | Input Validation, File Security and Data Protection |
| Ong Jia E | Secure Communication and Infrastructure |
| Lim Yu Sheng | Security Logging, Monitoring and Vulnerability Testing |

## 12. Academic Project

**Module:** 6000CMD / 6005CEM – Security  
**Assignment:** CW2 – Secure Application Development and Implementation  
**Institution:** INTI International College Penang / Coventry University  
**Academic Session:** August 2026

This repository contains the security enhancements implemented for the DAM System as part of the group coursework assignment.
