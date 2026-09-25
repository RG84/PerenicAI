# Example internal engineering policy: healthcare

An example of the kind of internal policy PAT Compliance can check against.
Replace it with your organisation's real policies.

## LOG-1 No patient data in logs

Application logs, print statements and error messages must not contain PHI
such as names, dates of birth, SSNs, MRNs or diagnoses. Log an internal,
pseudonymous patient ID instead.

## LOG-2 Audit trail for patient records

Every read, create, update or delete of a patient record must write an audit
event recording who did it, what they did and when.

## DEV-1 Synthetic test data only

Tests, fixtures and example code must use synthetic data. Real or
realistic-looking SSNs and MRNs must never be committed to source control.

## SEC-1 Secrets management

Passwords, API keys and tokens must be loaded from the secrets manager or
environment variables, never written in source code.
