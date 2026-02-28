import hashlib
from pathlib import Path
from app.core.config import settings

ANONYMIZATION_STRATEGY_VERSION = "1.0"

PHI_TAGS = {
    (0x0010, 0x0010),  # PatientName
    (0x0010, 0x0020),  # PatientID
    (0x0010, 0x0030),  # PatientBirthDate
    (0x0010, 0x0040),  # PatientSex
    (0x0010, 0x1000),  # OtherPatientIDs
    (0x0010, 0x1001),  # OtherPatientNames
    (0x0010, 0x1010),  # PatientAge
    (0x0010, 0x1020),  # PatientSize
    (0x0010, 0x1030),  # PatientWeight
    (0x0010, 0x2160),  # EthnicGroup
    (0x0008, 0x0080),  # InstitutionName
    (0x0008, 0x0081),  # InstitutionAddress
    (0x0008, 0x0090),  # ReferringPhysicianName
    (0x0008, 0x1048),  # PhysiciansOfRecord
    (0x0008, 0x1050),  # PerformingPhysicianName
    (0x0008, 0x1070),  # OperatorsName
    (0x0020, 0x4000),  # ImageComments
    (0x0032, 0x1032),  # RequestingPhysician
    (0x0040, 0x0006),  # ScheduledPerformingPhysicianName
}

UID_TAGS = {
    (0x0020, 0x000D),  # StudyInstanceUID
    (0x0020, 0x000E),  # SeriesInstanceUID
    (0x0008, 0x0018),  # SOPInstanceUID
}


def generate_uid(original_uid: str, salt: str) -> str:
    hash_bytes = hashlib.sha256(f"{original_uid}{salt}".encode()).digest()
    hash_int = int.from_bytes(hash_bytes[:16], byteorder="big")
    decimal_str = str(hash_int)
    prefix = "2.25."
    max_decimal_len = 64 - len(prefix)
    return prefix + decimal_str[:max_decimal_len]


class DicomAnonymizer:
    def __init__(self, salt: str | None = None):
        self.salt = salt or settings.DICOM_ANONYMIZATION_SALT

    def anonymize(self, input_path: Path, output_path: Path) -> dict:
        import pydicom

        ds = pydicom.dcmread(str(input_path))

        tag_snapshot = str(sorted(
            (str(tag), str(ds.get(tag, "")))
            for tag in PHI_TAGS if tag in ds
        ))
        original_tag_hash = hashlib.sha256(tag_snapshot.encode()).hexdigest()

        for tag in PHI_TAGS:
            if tag in ds:
                del ds[tag]

        private_count = 0
        private_tags = [elem.tag for elem in ds if elem.tag.is_private]
        for tag in private_tags:
            del ds[tag]
            private_count += 1

        uid_mappings = {}
        for tag in UID_TAGS:
            if tag in ds:
                original = str(ds[tag].value)
                new_uid = generate_uid(original, self.salt)
                uid_mappings[original] = new_uid
                ds[tag].value = new_uid

        output_path.parent.mkdir(parents=True, exist_ok=True)
        ds.save_as(str(output_path))

        return {
            "original_tag_hash": original_tag_hash,
            "strategy_version": ANONYMIZATION_STRATEGY_VERSION,
            "private_tags_removed": private_count,
            "uid_mappings": uid_mappings,
        }
