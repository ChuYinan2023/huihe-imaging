import pytest
from app.services.dicom_service import generate_uid, PHI_TAGS, ANONYMIZATION_STRATEGY_VERSION


def test_generate_uid_format():
    uid = generate_uid("1.2.3.4.5", "test-salt")
    assert uid.startswith("2.25.")
    assert len(uid) <= 64
    assert all(c.isdigit() or c == "." for c in uid)


def test_generate_uid_deterministic():
    uid1 = generate_uid("1.2.3.4.5", "salt")
    uid2 = generate_uid("1.2.3.4.5", "salt")
    assert uid1 == uid2


def test_generate_uid_different_inputs():
    uid1 = generate_uid("1.2.3.4.5", "salt")
    uid2 = generate_uid("1.2.3.4.6", "salt")
    assert uid1 != uid2


def test_phi_tags_defined():
    assert (0x0010, 0x0010) in PHI_TAGS  # PatientName
    assert (0x0010, 0x0020) in PHI_TAGS  # PatientID
    assert (0x0010, 0x0030) in PHI_TAGS  # PatientBirthDate


def test_strategy_version():
    assert ANONYMIZATION_STRATEGY_VERSION == "1.0"
