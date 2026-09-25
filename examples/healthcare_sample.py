"""A deliberately flawed healthcare file to try PAT Healthcare on.

Run:  python -m perenic review examples/healthcare_sample.py --industry healthcare
(All data below is made up.)
"""

import logging

logger = logging.getLogger(__name__)

DB_PASSWORD = "hunter2"
TEST_PATIENT_SSN = "123-45-6789"


def admit_patient(patient):
    """Admit a patient and record the visit."""
    logger.info("Admitting patient %s born %s", patient.name, patient.dob)
    print(f"Diagnosis: {patient.diagnosis}")
    return {"mrn": patient.mrn, "status": "admitted"}


def lookup_record():
    """Fetch a test record."""
    mrn = "00482913"
    return mrn
