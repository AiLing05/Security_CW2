# 📁 File Digitalization System

A document digitalization and workflow management system built with Django REST Framework. It enables secure scanning, uploading, reviewing, and sharing of digital documents with real-time notifications using Firebase, authentication via Djoser tokens, and robust role-based access control.

## 🚀 Features

- 📄 **Document Scanning & Uploading** with OCR
- ✅ **File Approval Workflow** with escalation
- 🔍 **Smart Search & Retrieval** with filters and relevance ranking
- 🔐 **Access Control & Document Sharing**
- 💾 **Encrypted Backup & Recovery**
- 📊 **Analytics Reporting** with scheduled reports
- 🔔 **Real-time Notifications** using Firebase Cloud Messaging (FCM)
- 🔑 **Authentication** via Djoser Token Auth
- 👥 **Role-Based Permissions** (Admin, Manager, User, Viewer)

---

## 🧭 Workflows

### 📤 Document Scanning and Upload
- **Initiator**: Standard User
- **Actions**:
  - Scan and upload documents.
  - Tag with metadata (file name, category).
  - Save to folder.
- **Automations**:
  - OCR text extraction.
  - Firebase notification to users with access.

---

### ✔️ File Approval
- **Initiator**: Standard User
- **Actions**:
  - Submit file for approval.
  - Approver reviews and acts (approve/request changes/reject).
- **Automations**:
  - Escalation to higher authority after timeout.
  - Firebase alert to approvers.

---

### 🔎 Search and Retrieval
- **Initiator**: Any user with access.
- **Actions**:
  - Filter by metadata, date, keywords.
  - View sorted and ranked results.
- **Automations**:
  - Show related files based on usage patterns.

---

### 🔐 Access Control and Sharing
- **Initiator**: Any user.
- **Actions**:
  - Request or share access to files.
  - Admin approves or denies.
- **Automations**:
  - Notify stakeholders of permission changes.

---

### 🛡️ Backup and Recovery
- **Initiator**: System
- **Actions**:
  - Auto backup at scheduled intervals.
  - Encrypted storage.
  - Restore upon user request.
- **Automations**:
  - Notify users on completion/recovery.

---

### 📈 Analytics Reporting
- **Initiator**: Admin
- **Actions**:
  - Choose report type (usage, access, etc.).
  - Generate visuals and stats.
- **Automations**:
  - Schedule recurring reports.

---

## 👥 Roles and Permissions

### 🛠️ Admin
- Full system access
- Manage users, roles, workflows, and reports
- Handle escalations

### 📂 Manager
- Team-specific access
- Approve/reject files
- View reports for their domain

### 👨‍💼 Standard User
- Upload, tag, and request file access
- Start approval workflows
- Retrieve permitted documents

### 👀 Viewer
- View-only role
- Can comment (if allowed)
- No workflow privileges

---

## 🛠️ Tech Stack

- **Backend**: Django, Django REST Framework
- **Authentication**: Djoser Token Authentication
- **Notifications**: Firebase Cloud Messaging (FCM)
- **OCR**: Tesseract / OpenCV
- **Database**: PostgreSQL
- **Storage**: Encrypted local/remote file system

---

## 📦 Dependencies Installation

### 📄 OCR Setup (Tesseract + Poppler)
- Download Tesseract
- Download Poppler

### ⚡ Redis Cache Setup
- Install Redis
- Open cmd 
- Open redis directy as cd
- Open redis-server

---

## 🔐 Authentication

Uses **Djoser** for token-based authentication:

```http
POST /auth/token/login/
{
  "username": "user",
  "password": "pass"
}

