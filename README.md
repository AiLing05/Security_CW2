# SoftwareEngineeringGroupProject

Digital Asset Management System (Django + Next.js + PostgreSQL)

A full-stack digital asset management platform built using Django REST Framework, Next.js (React) and PostgreSQL, 
designed to support secure asset uploads, metadata handling, version control, admin approval workflows and role-based access control.

Overview

This system allows organizations to store, manage and retrieve digital assets efficiently. It includes JWT authentication, user roles, 
asset versioning, drag-and-drop uploads and a full admin panel for managing users and approval requests.

Frontend
- Next.js (React)
- Chakra UI

Backend
- Python Django
- Django REST Framework
- SimpleJWT Authentication
- Redux ToolKit
- PostgreSQL
- Django Admin

The system supports 3 main roles:

Role	Permissions
Admin: Full control: user management, approve updates, edit/delete all assets
Editor: Upload assets, edit their own assets, request updates
Viewer: View and download approved assets

Main Features

✔️ 1. User Authentication & Role Access
Login using SimpleJWT
Tokens contain user role → used for frontend access control
Middleware protects API routes
Admin-only functions in backend

✔️ 2. Asset Upload & Download
Drag-and-drop upload (Next.js)
Django handles file validation + saving
Secure download endpoint
Files stored with metadata + version history

✔️ 3. Metadata Management
Custom fields: tags, description, category
Tag creation (admin) + smart tagging system
Metadata stored in PostgreSQL and returned through serialized API responses

✔️ 4. Advanced Search & Pagination
Search by:
Title
Tags
Category
Uploaded date
Pagination ensures high performance for large datasets.

✔️ 5. Asset Preview & Version History
Image, video, PDF preview support
Track updates using AssetVersion model
Editors submit updates → Admin approves or rejects

✔️ 6. User Management
Admin can create, update, deactivate users
Change roles directly in the admin panel or custom admin page

✔️ 7. Update Request (Admin Side)
Editors request asset changes
Admin receives request list (API)
Admin approves/rejects via dedicated endpoints

1️⃣ Backend Setup:
cd backend
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver

2️⃣ Frontend Setup:
cd frontend
npm install
npm run dev

Author:
Nurul Ashwin Farhah,
INTI International College Penang,
3+0 Bachelor of Science (Hons) in Computer Science, in collaboration with Coventry
University, UK

