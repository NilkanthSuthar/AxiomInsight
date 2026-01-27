# Information Security & Compliance Policy
## Axiom Company Inc. - Canada

**Document Classification:** Confidential  
**Version:** 2.0  
**Effective Date:** January 1, 2025  
**Review Date:** January 1, 2026  
**Owner:** Chief Information Security Officer (CISO)

---

## Executive Summary

This document outlines Axiom Company's information security and compliance framework. Our security program is designed to protect company assets, customer data, and intellectual property while ensuring compliance with Canadian and international regulations.

**Compliance Certifications:**
- SOC 2 Type II
- ISO 27001:2013
- PIPEDA Compliant
- GDPR Compliant
- PCI DSS Level 1 (for payment processing)

---

## 1. Information Security Governance

### 1.1 Security Organization

**Information Security Team Structure:**
- Chief Information Security Officer (CISO)
- Security Architecture Team (3 members)
- Security Operations Center (SOC) Team (5 members)
- Compliance & Risk Team (2 members)
- Security Awareness & Training (1 member)

**Security Committee:**
- Meets monthly
- Members: CISO, CTO, Legal Counsel, CFO, Privacy Officer
- Responsibilities: Risk assessment, policy review, incident response oversight

### 1.2 Roles & Responsibilities

**All Employees:**
- Complete annual security awareness training
- Report security incidents immediately
- Follow password and access control policies
- Protect confidential information

**Managers:**
- Ensure team compliance with security policies
- Review access permissions quarterly
- Conduct security discussions in team meetings

**IT & Engineering:**
- Implement security controls
- Conduct security assessments
- Maintain security infrastructure
- Respond to security incidents

---

## 2. Data Classification & Handling

### 2.1 Data Classification Levels

**Public**
- Marketing materials, job postings, press releases
- Handling: No special restrictions
- Examples: Website content, social media posts

**Internal**
- Business documents, internal communications
- Handling: Company employees only, not for external sharing
- Examples: Meeting notes, internal presentations

**Confidential**
- Proprietary information, customer data
- Handling: Access on need-to-know basis, encryption required
- Examples: Customer contracts, financial reports, source code

**Restricted**
- Highly sensitive information
- Handling: Executive approval required, strict access controls
- Examples: Executive compensation, M&A documents, security keys

### 2.2 Data Handling Requirements

**Confidential Data:**
- ✓ Encrypt at rest (AES-256)
- ✓ Encrypt in transit (TLS 1.3)
- ✓ Access logging enabled
- ✓ Annual access review
- ✓ Secure deletion when no longer needed

**Personal Information (PI):**
- ✓ Minimize collection
- ✓ Obtain consent
- ✓ Secure storage
- ✓ Retention limits
- ✓ Right to access/deletion

---

## 3. Access Control

### 3.1 Authentication Requirements

**Password Policy:**
- Minimum 12 characters
- Must include: uppercase, lowercase, numbers, special characters
- No common words or patterns
- Changed every 90 days
- Cannot reuse last 10 passwords
- Account lockout after 5 failed attempts

**Multi-Factor Authentication (MFA):**
- **Required for:**
  - All VPN access
  - Cloud service access (AWS, Azure, GCP)
  - Administrative accounts
  - Email and collaboration tools
  - Customer data access

- **MFA Methods:**
  - Authenticator apps (preferred): Google Authenticator, Microsoft Authenticator
  - Hardware tokens: YubiKey
  - SMS (only if no other option available)

### 3.2 Access Management

**Principle of Least Privilege:**
- Users granted minimum access necessary
- Role-based access control (RBAC)
- Quarterly access reviews

**Access Provisioning:**
- New hire: Provisioned within 1 business day
- Role change: Updated within 1 business day
- Termination: Revoked immediately

**Privileged Access:**
- Requires manager approval
- Logged and monitored
- Time-limited (reviewed every 90 days)
- Separate accounts for administrative tasks

---

## 4. Network & Infrastructure Security

### 4.1 Network Segmentation

```
┌────────────────────────────────────────┐
│         Internet / Public              │
└────────────────────────────────────────┘
                  │
         ┌────────▼────────┐
         │   Firewall/WAF  │
         └────────┬────────┘
                  │
    ┌─────────────┴──────────────┐
    │                            │
    ▼                            ▼
┌────────┐                 ┌──────────┐
│  DMZ   │                 │ VPN/VDI  │
│ Zone   │                 │  Gateway │
└────┬───┘                 └────┬─────┘
     │                          │
     └────────┬─────────────────┘
              │
      ┌───────▼────────┐
      │ Internal Network│
      └───────┬────────┘
              │
     ┌────────┴────────┐
     │                 │
     ▼                 ▼
┌──────────┐     ┌──────────┐
│Production│     │ Dev/Test │
│  Zone    │     │   Zone   │
└──────────┘     └──────────┘
```

### 4.2 Firewall Rules

**Inbound Traffic:**
- Default deny all
- Whitelist specific ports and sources
- Web traffic: 443 (HTTPS) only
- SSH: Only from VPN, key-based auth

**Outbound Traffic:**
- Default allow with monitoring
- Block known malicious IPs
- DLP (Data Loss Prevention) scanning

### 4.3 Remote Access

**VPN Requirements:**
- GlobalProtect VPN (Palo Alto)
- MFA required
- Full tunnel mode
- Split tunneling prohibited
- Automatic disconnect after 12 hours
- Session logging

**Acceptable Remote Locations:**
- Home office
- Co-working spaces
- Hotels (with VPN)
- **Prohibited:** Public WiFi without VPN, internet cafes

---

## 5. Application Security

### 5.1 Secure Development Lifecycle

**Requirements Phase:**
- Security requirements defined
- Threat modeling conducted
- Privacy impact assessment

**Design Phase:**
- Security architecture review
- Data flow diagrams
- Attack surface analysis

**Development Phase:**
- Secure coding standards (OWASP Top 10)
- Code review (peer + automated)
- Static Application Security Testing (SAST)

**Testing Phase:**
- Dynamic Application Security Testing (DAST)
- Penetration testing
- Security regression testing

**Deployment Phase:**
- Security configuration review
- Infrastructure as Code scanning
- Container image scanning

**Maintenance Phase:**
- Dependency scanning
- Vulnerability management
- Security patches within SLA

### 5.2 Third-Party Code & Libraries

**Requirements:**
- Use reputable sources only
- Automated dependency scanning (Snyk, Dependabot)
- License compliance check
- Vulnerability assessment before use
- Regular updates (monthly)

**Prohibited:**
- Unlicensed software
- Outdated/unmaintained libraries
- Libraries with known critical vulnerabilities

---

## 6. Data Privacy & Protection

### 6.1 Privacy Principles

Axiom Company follows Privacy by Design principles:
1. **Proactive not reactive**
2. **Privacy as the default**
3. **Privacy embedded into design**
4. **Full functionality (positive-sum)**
5. **End-to-end security**
6. **Visibility and transparency**
7. **Respect for user privacy**

### 6.2 PIPEDA Compliance

**Collection:**
- Collect only what's necessary
- Obtain informed consent
- Explain purpose clearly

**Use:**
- Use only for stated purposes
- No secondary use without consent
- Retention limited to necessary period

**Disclosure:**
- Third-party processors vetted
- Data Processing Agreements (DPAs) in place
- No sale of personal information

**Individual Rights:**
- Right to access
- Right to correction
- Right to deletion
- Right to data portability
- Right to withdraw consent

### 6.3 Data Retention

| Data Type | Retention Period | Destruction Method |
|-----------|------------------|-------------------|
| Customer contracts | 7 years after termination | Secure deletion |
| Financial records | 7 years | Secure deletion |
| Employee records | 7 years after termination | Secure shredding |
| Application logs | 90 days | Automated deletion |
| Audit logs | 7 years | Encrypted archive |
| Backups | 30 days (daily), 12 months (monthly) | Secure deletion |

---

## 7. Incident Response

### 7.1 Incident Classification

**P0 - Critical:**
- Active data breach
- Ransomware attack
- Complete service outage
- **Response Time:** 15 minutes
- **Notification:** CISO, CEO, affected customers

**P1 - High:**
- Suspected data breach
- Major security vulnerability
- Partial service outage
- **Response Time:** 1 hour
- **Notification:** CISO, CTO

**P2 - Medium:**
- Security policy violation
- Minor vulnerability
- **Response Time:** 4 hours
- **Notification:** Security team

**P3 - Low:**
- Security awareness issue
- Non-critical finding
- **Response Time:** Next business day
- **Notification:** Team lead

### 7.2 Incident Response Process

1. **Detection & Analysis**
   - Incident reported via security@axiom.ca or Slack #security
   - Severity classification
   - Initial containment

2. **Containment**
   - Isolate affected systems
   - Preserve evidence
   - Document all actions

3. **Eradication**
   - Remove threat
   - Patch vulnerabilities
   - System hardening

4. **Recovery**
   - Restore from clean backups
   - Verify system integrity
   - Resume normal operations

5. **Post-Incident**
   - Root cause analysis
   - Lessons learned
   - Policy/process updates
   - Customer notification (if required)

### 7.3 Breach Notification

**Privacy Breach:**
- Assess risk to individuals
- Notify affected individuals if real risk of significant harm
- Notify Privacy Commissioner of Canada
- Maintain breach register

**Timeline:**
- Internal notification: Immediately
- Regulatory notification: As soon as feasible
- Customer notification: Within 72 hours (if required)

---

## 8. Business Continuity & Disaster Recovery

### 8.1 Backup Strategy

**3-2-1 Rule:**
- 3 copies of data
- 2 different storage types
- 1 offsite/cloud copy

**Backup Schedule:**
- Database: Continuous replication + hourly snapshots
- Files: Daily incremental, weekly full
- Retention: Daily (30 days), Weekly (12 weeks), Monthly (12 months)

**Testing:**
- Monthly restore tests
- Quarterly DR drills
- Annual full failover test

### 8.2 Disaster Recovery Objectives

**Recovery Time Objective (RTO):**
- Critical systems: 4 hours
- Important systems: 24 hours
- Non-critical systems: 72 hours

**Recovery Point Objective (RPO):**
- Critical data: 15 minutes
- Important data: 1 hour
- Non-critical data: 24 hours

---

## 9. Vendor & Third-Party Risk Management

### 9.1 Vendor Security Assessment

**Pre-Engagement:**
- Security questionnaire (required)
- SOC 2 report review (for critical vendors)
- Data Processing Agreement (DPA)
- Insurance verification ($2M minimum)

**Risk Tiers:**
- **Tier 1 (Critical):** Access to customer data, core infrastructure
  - Annual reassessment
  - On-site audits
  - Continuous monitoring

- **Tier 2 (High):** Access to internal data
  - Biannual reassessment
  - Remote audits

- **Tier 3 (Medium):** Limited access
  - Annual reassessment

### 9.2 Vendor Obligations

All vendors must:
- Maintain security certifications
- Report security incidents within 24 hours
- Allow security audits
- Comply with data protection laws
- Provide right to audit

---

## 10. Physical Security

### 10.1 Office Security

**Access Control:**
- Badge-based entry systems
- Visitor sign-in required
- Visitor escorts mandatory
- After-hours access logged

**Surveillance:**
- Security cameras in common areas
- 90-day retention
- Monitored 24/7 (Toronto HQ)

**Device Security:**
- Clean desk policy
- Cable locks for laptops
- Secure disposal of documents (shred bins)
- Server rooms: biometric access

---

## 11. Compliance & Audit

### 11.1 Compliance Framework

**SOC 2 Type II:**
- Annual audit by Big 4 firm
- Trust Service Criteria: Security, Availability, Confidentiality
- Report available to customers under NDA

**ISO 27001:**
- Triennial certification audit
- Annual surveillance audits
- 114 security controls implemented

**PIPEDA:**
- Annual privacy assessment
- Privacy Impact Assessments (PIAs) for new systems
- Privacy Commissioner audit readiness

### 11.2 Internal Audits

**Schedule:**
- Quarterly access reviews
- Annual security policy review
- Biannual penetration testing
- Monthly vulnerability scans

**Audit Trail:**
- All privileged actions logged
- Log retention: 7 years
- SIEM monitoring (Splunk)
- Alerts for suspicious activity

---

## 12. Security Awareness & Training

### 12.1 Training Requirements

**New Hire Training:**
- Security awareness (day 1)
- Phishing simulation (week 1)
- Role-specific training (week 2)

**Annual Training:**
- Security refresher (mandatory)
- Privacy training (mandatory)
- Phishing simulations (quarterly)
- Specialized training (role-dependent)

**Pass Rate:**
- Minimum 90% on assessments
- Retake if failed
- Manager notification for repeated failures

### 12.2 Security Awareness Program

**Monthly Activities:**
- Security newsletter
- Lunch & Learn sessions
- Simulated phishing campaigns
- Security tips on Slack

**Metrics:**
- Phishing click rate target: <5%
- Training completion: 100%
- Incident reporting time: <30 minutes

---

## 13. Acceptable Use Policy

### 13.1 Acceptable Use

Employees may use company resources for:
- Business purposes
- Reasonable personal use during breaks
- Professional development

### 13.2 Prohibited Activities

**Strictly Forbidden:**
- Accessing illegal content
- Downloading pirated software
- Cryptocurrency mining
- Sharing credentials
- Circumventing security controls
- Connecting unauthorized devices
- Using personal cloud storage for company data
- Installing unapproved software

**Consequences:**
- First violation: Written warning
- Second violation: Suspension
- Third violation: Termination
- Criminal activity: Law enforcement referral

---

## 14. Mobile Device Security

### 14.1 Company-Owned Devices

**Requirements:**
- MDM enrollment (Microsoft Intune)
- Encryption enabled
- Remote wipe capability
- Automatic OS updates
- Strong passcode (6+ digits)
- Timeout: 5 minutes

### 14.2 BYOD (Bring Your Own Device)

**Allowed for:**
- Email access
- Calendar and contacts
- Collaboration tools

**Requirements:**
- Containerized apps (work profile)
- No access to confidential data
- Must consent to remote work data wipe
- Personal data not accessible by company

---

## 15. Policy Violations & Enforcement

### 15.1 Violation Reporting

**How to Report:**
- Email: security@axiom.ca
- Phone: Security Hotline
- Anonymous: Ethics hotline

**Non-Retaliation:**
- Good faith reporters protected
- Anonymous reporting option available

### 15.2 Disciplinary Actions

**Minor Violations:**
- Verbal warning
- Mandatory retraining
- Manager notification

**Major Violations:**
- Written warning
- Suspension
- Termination
- Legal action (if warranted)

---

## 16. Policy Review & Updates

**Review Cycle:** Annual  
**Next Review Date:** January 1, 2026  
**Approval Required:** CISO, Legal, Executive Team  

**Change Management:**
- Material changes communicated to all employees
- Training updated accordingly
- Version control maintained

---

## Contact Information

**Security Team:**  
Email: security@axiom.ca  
Slack: #security  
Phone: +1 (416) 555-0199

**Privacy Officer:**  
Email: privacy@axiom.ca  
Phone: +1 (416) 555-0198

**Compliance Team:**  
Email: compliance@axiom.ca  
Phone: +1 (416) 555-0197

---

**Document Control:**  
Version: 2.0  
Approved by: CISO, Legal Counsel, CEO  
Effective Date: January 1, 2025  
Classification: Confidential (Compliance Team Access)

*This document outlines mandatory security requirements for all Axiom Company employees, contractors, and partners.*
