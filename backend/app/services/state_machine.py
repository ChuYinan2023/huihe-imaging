from app.models.imaging import ImagingStatus
from app.models.issue import IssueStatus


class InvalidTransitionError(Exception):
    def __init__(self, from_status, to_status):
        super().__init__(f"Invalid transition: {from_status} → {to_status}")
        self.from_status = from_status
        self.to_status = to_status


class FSM:
    transitions: dict

    @classmethod
    def can_transition(cls, from_status, to_status) -> bool:
        return to_status in cls.transitions.get(from_status, set())

    @classmethod
    def transition(cls, from_status, to_status):
        if not cls.can_transition(from_status, to_status):
            raise InvalidTransitionError(from_status, to_status)
        return to_status


class ImagingFSM(FSM):
    transitions = {
        ImagingStatus.UPLOADING: {ImagingStatus.ANONYMIZING, ImagingStatus.UPLOAD_FAILED},
        ImagingStatus.ANONYMIZING: {ImagingStatus.COMPLETED, ImagingStatus.ANONYMIZE_FAILED},
        ImagingStatus.COMPLETED: {ImagingStatus.REJECTED},
        ImagingStatus.REJECTED: {ImagingStatus.COMPLETED},
        ImagingStatus.UPLOAD_FAILED: set(),
        ImagingStatus.ANONYMIZE_FAILED: set(),
    }


class IssueFSM(FSM):
    transitions = {
        IssueStatus.PENDING: {IssueStatus.PROCESSING},
        IssueStatus.PROCESSING: {IssueStatus.REVIEWING},
        IssueStatus.REVIEWING: {IssueStatus.CLOSED, IssueStatus.PENDING},
        IssueStatus.CLOSED: set(),
    }
