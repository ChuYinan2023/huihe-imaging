import enum
from app.models.user import UserRole


class Permission(str, enum.Enum):
    MANAGE_USERS = "manage_users"
    MANAGE_PROJECTS = "manage_projects"
    UPLOAD_IMAGING = "upload_imaging"
    CREATE_ISSUE = "create_issue"
    PROCESS_ISSUE = "process_issue"
    REVIEW_ISSUE = "review_issue"
    UPLOAD_REPORT = "upload_report"
    DOWNLOAD_DATA = "download_data"
    VIEW_AUDIT_LOG = "view_audit_log"
    VIEW_REPORTS = "view_reports"
    VIEW_IMAGING = "view_imaging"
    VIEW_ISSUES = "view_issues"


ROLE_PERMISSIONS: dict[UserRole, set[Permission]] = {
    UserRole.ADMIN: set(Permission),  # Admin has all permissions
    UserRole.PM: {
        Permission.MANAGE_PROJECTS, Permission.DOWNLOAD_DATA,
        Permission.CREATE_ISSUE, Permission.REVIEW_ISSUE,
        Permission.UPLOAD_REPORT,
        Permission.VIEW_REPORTS, Permission.VIEW_IMAGING, Permission.VIEW_ISSUES,
    },
    UserRole.EXPERT: {
        Permission.CREATE_ISSUE, Permission.REVIEW_ISSUE,
        Permission.UPLOAD_REPORT, Permission.VIEW_REPORTS,
        Permission.VIEW_IMAGING, Permission.VIEW_ISSUES,
    },
    UserRole.CRC: {
        Permission.UPLOAD_IMAGING, Permission.CREATE_ISSUE, Permission.PROCESS_ISSUE,
        Permission.VIEW_REPORTS, Permission.VIEW_IMAGING, Permission.VIEW_ISSUES,
    },
    UserRole.CRA: {
        Permission.CREATE_ISSUE, Permission.UPLOAD_REPORT,
        Permission.VIEW_REPORTS, Permission.VIEW_IMAGING, Permission.VIEW_ISSUES,
    },
    UserRole.DM: {
        Permission.DOWNLOAD_DATA, Permission.VIEW_REPORTS,
        Permission.VIEW_IMAGING, Permission.VIEW_ISSUES,
    },
}


def check_permission(role: UserRole, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, set())
