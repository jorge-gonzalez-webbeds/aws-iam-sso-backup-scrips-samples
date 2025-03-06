# SSO Migration Plan
# Steps
## 1. Pre-migration:
- Backup IdC by creating a relationship between entities (groups, permission sets and apps) and user emails.
- Test you can restore this in the test-IdC
## 2. Migration:
- Change IdP in IdC to the new Entra ID tenant
- Test Authentication
- Activate SCIM – Note SCIM uses email to sync, so it’ll continue overwriting existing users
- Test sync is working.
## 3. Disaster Plans:
- If Entra ID cannot authenticate:
    - Change identity provider to internal directory in IdC
    - Create break glass users for critical members or set up password for their current users
    - Fix the issue in Entra ID
    - When fixed, configure Entra ID as IdP and SCIM and test
- If configuration is lost in IdC
    - Use backups to fully or partially restore
    - Configure Entra ID as IdP and SCIM and test
# Documentation
- https://docs.aws.amazon.com/singlesignon/latest/userguide/manage-your-identity-source-change.html
- https://docs.aws.amazon.com/singlesignon/latest/userguide/manage-your-identity-source-considerations.html#changing-from-one-idp-to-another-idp
- https://docs.aws.amazon.com/singlesignon/latest/userguide/provision-automatically.html
- https://docs.aws.amazon.com/singlesignon/latest/userguide/idp-microsoft-entra.html
- https://learn.microsoft.com/en-us/entra/identity/saas-apps/amazon-web-service-tutorial#aws-single-account-access-architecture