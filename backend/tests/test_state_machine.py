import pytest
from app.services.state_machine import ImagingFSM, IssueFSM, InvalidTransitionError
from app.models.imaging import ImagingStatus
from app.models.issue import IssueStatus


def test_imaging_valid_transitions():
    assert ImagingFSM.can_transition(ImagingStatus.UPLOADING, ImagingStatus.ANONYMIZING)
    assert ImagingFSM.can_transition(ImagingStatus.ANONYMIZING, ImagingStatus.COMPLETED)
    assert ImagingFSM.can_transition(ImagingStatus.UPLOADING, ImagingStatus.UPLOAD_FAILED)
    assert ImagingFSM.can_transition(ImagingStatus.COMPLETED, ImagingStatus.REJECTED)
    assert ImagingFSM.can_transition(ImagingStatus.REJECTED, ImagingStatus.COMPLETED)


def test_imaging_invalid_transitions():
    assert not ImagingFSM.can_transition(ImagingStatus.UPLOADING, ImagingStatus.COMPLETED)
    assert not ImagingFSM.can_transition(ImagingStatus.COMPLETED, ImagingStatus.UPLOADING)


def test_imaging_transition_raises_on_invalid():
    with pytest.raises(InvalidTransitionError):
        ImagingFSM.transition(ImagingStatus.UPLOADING, ImagingStatus.COMPLETED)


def test_imaging_transition_returns_new_status():
    result = ImagingFSM.transition(ImagingStatus.UPLOADING, ImagingStatus.ANONYMIZING)
    assert result == ImagingStatus.ANONYMIZING


def test_issue_valid_transitions():
    assert IssueFSM.can_transition(IssueStatus.PENDING, IssueStatus.PROCESSING)
    assert IssueFSM.can_transition(IssueStatus.PROCESSING, IssueStatus.REVIEWING)
    assert IssueFSM.can_transition(IssueStatus.REVIEWING, IssueStatus.CLOSED)
    assert IssueFSM.can_transition(IssueStatus.REVIEWING, IssueStatus.PENDING)


def test_issue_invalid_transitions():
    assert not IssueFSM.can_transition(IssueStatus.PENDING, IssueStatus.CLOSED)
    assert not IssueFSM.can_transition(IssueStatus.CLOSED, IssueStatus.PENDING)
