# Security_CW2

Network Security Coursework 2

## Project Description
A secure document management system implementing
authentication, authorization, encryption,
logging, and other security controls.

# MASTER PROJECT BRIEF — SECURITY CW2 GROUP ASSIGNMENT

## 1. Assignment Information

We are a group of 5 Computer Science students working on:

- **Module:** 6000CMD / 6005CEM — Security
- **Assignment:** CW2 — Secure Application Development and Implementation
- **Official Deadline:** 14 November 2026, 11:59 PM (Malaysia Time)
- **Internal Target:** 2 November 2026
- **Development Duration:** 3 weeks
- **Report:** 4,000 words ±20% (3,200–4,800 words)
- **Assessment:** 60% Report + 40% Development and Viva
- **Target Grade:** 80%+ (Distinction-level target)

Our objective is to develop and demonstrate a fully functional, security-enhanced application that addresses real cybersecurity threats using secure software development practices.

This is NOT just a documentation assignment. We must implement, test, demonstrate, and justify our security solutions.

## 2. Selected Application

**Project:** File Digitalization System — Security Enhancement

**GitHub Repository:**
https://github.com/kusumstha2/File-Digitalization

We intend to use an existing Django-based document management application and enhance its security.

The repository describes functionality involving:

- User registration and authentication
- Role-based access control
- Document uploading and management
- Document approval workflows
- File sharing
- Document processing and OCR
- Analytics and reporting

The documented technology stack includes Django REST Framework, PostgreSQL, Djoser authentication, Firebase, Redis, and supporting document-processing tools.

**Important:** These are repository-described capabilities, not yet independently verified working features.

Before adopting the repository, we must confirm lecturer approval, check its license and reuse permissions, successfully run the original system, and audit its existing security.

Our assignment brief permits enhancement of previous work developed within our programme, but does not explicitly authorize reuse of unrelated GitHub code. We must not present third-party code as our original work.

## 3. Assignment Security Requirements

Our application must address six main security areas:

1. **Authentication and Authorization:** Secure login, multiple users, RBAC or Principle of Least Privilege.
2. **Input Validation and Error Handling:** Prevent SQL injection, XSS, unsafe input processing and sensitive error disclosures.
3. **Secure Communication:** HTTPS/TLS, certificate validation and secure communication configuration.
4. **Data Protection and User Education:** Protect sensitive user data and provide security and privacy guidance.
5. **Logging, Analytics and Advanced Security:** Record user/security activities and display role-restricted analytics.
6. **Security and Vulnerability Testing:** Conduct manual and automated security testing aligned with OWASP Top 10.

All implemented features must be technically justified and supported with evidence.

## 4. Work Distribution

### MEMBER 1 — Authentication, Session Security and Project Lead

**Estimated difficulty: 9.5/10**

Responsibilities:
- Audit existing Django/Djoser authentication.
- Verify registration and login.
- Strengthen password security.
- Implement login rate limiting.
- Secure authentication tokens or sessions.
- Implement secure logout and token revocation where appropriate.
- Configure authentication expiry.
- Prevent account enumeration.
- Test brute-force resistance, invalid credentials and expired tokens.
- Coordinate integration and shared architecture.
- Write authentication-related report sections.
- Prepare code, screenshots, test evidence and viva demonstration.

**Security threats:** Brute-force attacks, credential attacks, session hijacking and authentication weaknesses.

### MEMBER 2 — Authorization and Role-Based Access Control

**Estimated difficulty: 8/10**

Responsibilities:
- Audit existing Admin, Manager, User and Viewer roles.
- Create a permission matrix.
- Strengthen backend authorization.
- Implement document ownership checks.
- Secure document approval workflows.
- Secure document sharing permissions.
- Prevent unauthorized role changes.
- Enforce least-privilege access.
- Test IDOR and broken access control.
- Test horizontal and vertical privilege escalation.
- Document vulnerabilities and fixes.
- Write authorization-related report sections.
- Prepare individual viva demonstration.

**Security threats:** Broken access control, privilege escalation, IDOR and unauthorized document access.

### MEMBER 3 — Input Validation, File Security and Data Protection

**Estimated difficulty: 8.5/10**

Responsibilities:
- Audit input handling and validation.
- Implement server-side validation.
- Prevent SQL injection using safe database operations.
- Prevent XSS using context-appropriate output encoding.
- Secure file upload functionality.
- Restrict file types and sizes.
- Prevent path traversal.
- Protect file storage and downloads.
- Secure document processing and OCR inputs.
- Prevent sensitive information leakage.
- Implement safe error handling.
- Document privacy and retention practices.
- Test malicious inputs, SQL injection, XSS and unsafe uploads.
- Write input validation and data protection report sections.
- Prepare individual viva demonstration.

**Security threats:** SQL injection, XSS, malicious uploads, path traversal and sensitive data exposure.

### MEMBER 4 — Secure Communication and Infrastructure

**Estimated difficulty: 7.5/10**

Responsibilities:
- Audit Django security configuration.
- Configure HTTPS/TLS.
- Validate certificates.
- Configure secure cookies where applicable.
- Implement security headers.
- Restrict CORS.
- Apply appropriate CSRF protection.
- Secure environment variables and credentials.
- Disable debug mode in the secure environment.
- Configure trusted hosts.
- Review PostgreSQL, Firebase and Redis security where applicable.
- Secure storage and backup configuration.
- Run dependency vulnerability checks.
- Create user security guidance.
- Test TLS, HTTP redirection and security headers.
- Write infrastructure-related report sections.
- Prepare individual viva demonstration.

**Security threats:** Man-in-the-middle attacks, insecure configuration, exposed credentials and vulnerable dependencies.

### MEMBER 5 — Security Logging, Analytics and Vulnerability Testing 

**Estimated difficulty: 9/10**

Responsibilities:
- Audit existing logging and analytics.
- Design security audit event records.
- Log successful and failed authentication.
- Log unauthorized access attempts.
- Log document upload, deletion, sharing and approval events.
- Log administrative and role changes.
- Implement a security monitoring dashboard.
- Display security-event trends.
- Detect suspicious activity patterns.
- Restrict log access according to roles.
- Prevent unauthorized audit-log modification.
- Avoid logging passwords, tokens or sensitive content.
- Configure log retention.
- Coordinate OWASP Top 10 testing.
- Configure automated vulnerability testing.
- Consolidate security findings and retesting results.
- Write logging, testing and evaluation report sections.
- Prepare individual viva demonstration.

**Security threats:** Insufficient logging, undetected attacks, unauthorized audit-log access and security monitoring failures.

## 5. Shared Responsibilities

Every member must:

- Contribute to architecture and threat analysis.
- Develop meaningful security improvements.
- Work in their own GitHub branch.
- Test their own security implementation.
- Document the vulnerabilities they address.
- Capture screenshots, relevant code and testing evidence.
- Write their assigned report sections.
- Participate in integration and regression testing.
- Understand and demonstrate their own code during the viva.

Member 5 coordinates testing, but is NOT responsible for testing everyone else's modules.

Member 1 coordinates integration, but is NOT responsible for fixing everyone else's code.

## 6. Development Workflow

We will work in parallel.

Suggested branches:

- `main`
- `feature/auth-security`
- `feature/rbac-security`
- `feature/input-security`
- `feature/infrastructure`
- `feature/audit-testing`

Before development, agree on database models, API contracts, roles, shared configurations and code ownership.

Each member should use pull requests for integration, with review and testing before merging.

The development process is:

**Audit Existing System → Identify Vulnerabilities → Design Improvements → Implement → Test → Retest → Document**

We must distinguish existing GitHub functionality from our own security enhancements.

## 7. Three-Week Timeline

### WEEK 1: 13–19 October — Setup, Audit and Core Development

- Obtain approval and verify license.
- Clone and run the original application.
- Test existing functionality.
- Record existing security controls and weaknesses.
- Finalize architecture and permission matrix.
- Assign module ownership.
- Begin parallel development.
- Integrate initial security improvements.

**Milestone:** Working baseline application and initial security enhancements from all five members.

### WEEK 2: 20–26 October — Security Implementation and Integration

- Complete major authentication improvements.
- Complete RBAC and document-level authorization.
- Complete input validation and secure file handling.
- Configure HTTPS and infrastructure security.
- Complete security logging and dashboard.
- Integrate all modules.
- Perform initial manual and automated security tests.
- Fix critical integration and security problems.

**Milestone:** Functional, integrated application covering all six security requirements.

### WEEK 3: 27 October – 2 November — Testing, Report and Viva

- Conduct security regression testing.
- Run OWASP ZAP and relevant manual tests in the authorized environment.
- Document vulnerabilities, severity, fixes and retesting.
- Capture screenshots and code evidence.
- Finalize approximately 4,000-word report.
- Check citations, references and academic integrity requirements.
- Prepare individual viva demonstrations.
- Conduct full group rehearsal.
- Export final PDF and prepare submission package.

**Milestone:** Distinction-ready application, report, security evidence and viva preparation.

The remaining time before 14 November is reserved for contingency and final submission.

## 8. Report Structure

Suggested report sections:

1. Introduction and System Overview
2. Security Analysis and Threat Modelling
3. Security Architecture and Design
4. Authentication and Session Security
5. Authorization and RBAC
6. Input Validation and Data Protection
7. Secure Communication and Infrastructure
8. Security Logging and Analytics
9. Vulnerability Testing and Results
10. Discussion, Limitations and Improvements
11. Conclusion
12. References and supporting evidence

For every implemented security feature, explain:

- What vulnerability or security risk existed?
- Why is it a concern?
- What control did we select?
- How did we implement it?
- How did we test it?
- What evidence demonstrates its effectiveness?
- What limitations or residual risks remain?

Use credible sources such as OWASP, NIST, Django security documentation and relevant academic literature.

## 9. Assessment and Distinction Expectations

**Report: 60 marks**
- Introduction and System Overview — 5
- Security Analysis and Design — 10
- Security Implementation — 25
- Discussion and Improvement — 10
- Background Research and Report Quality — 10

**Development and Viva: 40 marks**
- Overall System Functionality — 5
- Individual Security Issues Addressed — 15
- Individual Security Solutions Implemented — 20

We are aiming for the highest rubric descriptors through technically correct security controls, strong implementation evidence, thorough testing, clear justifications and professional documentation.

Our 80%+ target is an internal goal, not a guaranteed grade.

## 10. Important Group Rules

1. Everyone must contribute actual security code or configuration.
2. Everyone must test their own module.
3. Everyone must write and understand their report contribution.
4. Do not wait until Week 3 to begin documentation.
5. Do not claim that a vulnerability exists without evidence.
6. Do not claim that a security control works without testing.
7. Do not present original GitHub functionality as our group's new implementation.
8. Do not commit passwords, tokens, API keys or other secrets.
9. Communicate integration problems early.
10. Prioritize a stable, secure application over unnecessary extra features.

## 11. Instructions for ChatGPT

I am one of the five group members working on this project.

Please use this project brief as context when helping me.

When I ask for development help:

- Focus primarily on my assigned security module.
- Consider compatibility with the existing Django application.
- Do not assume repository features are working without inspecting the code.
- Explain the security threat before recommending an implementation.
- Provide technically correct, maintainable and secure solutions.
- Include relevant testing procedures.
- Help me collect evidence suitable for the assignment report.
- Help me understand the implementation for my individual viva.
- Keep the three-week deadline and distinction-level rubric in mind.
- Do not unnecessarily rebuild functionality already present in the original system.

**My assigned role is: MEMBER [1 - ASHWIN].**
**My assigned role is: MEMBER [2 - RUTH].**
**My assigned role is: MEMBER [3 - AI LING].**
**My assigned role is: MEMBER [4 - JIAE].**
**My assigned role is: MEMBER [5 - YU SHENG].**

Help me plan, implement, test and document my responsibilities while ensuring my work integrates with the rest of the group.