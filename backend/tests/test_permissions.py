import pytest
from app.core.permissions import check_permission, Permission
from app.models.user import UserRole


def test_admin_can_manage_users():
    assert check_permission(UserRole.ADMIN, Permission.MANAGE_USERS)

def test_crc_cannot_manage_users():
    assert not check_permission(UserRole.CRC, Permission.MANAGE_USERS)

def test_expert_can_create_issues():
    assert check_permission(UserRole.EXPERT, Permission.CREATE_ISSUE)

def test_crc_can_upload_imaging():
    assert check_permission(UserRole.CRC, Permission.UPLOAD_IMAGING)

def test_expert_cannot_upload_imaging():
    assert not check_permission(UserRole.EXPERT, Permission.UPLOAD_IMAGING)

def test_dm_can_download_data():
    assert check_permission(UserRole.DM, Permission.DOWNLOAD_DATA)

def test_crc_cannot_download_data():
    assert not check_permission(UserRole.CRC, Permission.DOWNLOAD_DATA)
