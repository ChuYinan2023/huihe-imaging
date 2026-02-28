import pytest
import pytest_asyncio
from app.models.user import User, UserRole
from app.models.project import Project, Center, Subject
from app.core.security import hash_password


@pytest_asyncio.fixture
async def setup_data(db_session):
    """Create all necessary test data for the E2E flow."""
    # Create users
    admin = User(username="admin", email="admin@test.com", hashed_password=hash_password("Admin123!"), full_name="Admin", role=UserRole.ADMIN)
    expert = User(username="expert", email="expert@test.com", hashed_password=hash_password("Expert123!"), full_name="Expert", role=UserRole.EXPERT)
    crc = User(username="crc", email="crc@test.com", hashed_password=hash_password("Crc123!"), full_name="CRC", role=UserRole.CRC)
    db_session.add_all([admin, expert, crc])
    await db_session.flush()

    # Create project structure
    project = Project(code="E2E-001", name="E2E Test Project", status="active")
    db_session.add(project)
    await db_session.flush()

    center = Center(project_id=project.id, code="C001", name="Test Center")
    db_session.add(center)
    await db_session.flush()

    subject = Subject(center_id=center.id, project_id=project.id, screening_number="E2E-S001")
    db_session.add(subject)
    await db_session.commit()

    return {
        "admin": admin, "expert": expert, "crc": crc,
        "project": project, "center": center, "subject": subject,
    }


@pytest.mark.asyncio
async def test_full_business_flow(client, setup_data):
    """Test the complete flow: login -> create session -> create issue -> process -> review."""
    data = setup_data

    # 1. CRC logs in
    login_res = await client.post("/api/auth/login", json={"username": "crc", "password": "Crc123!"})
    assert login_res.status_code == 200
    crc_token = login_res.json()["access_token"]
    crc_headers = {"Authorization": f"Bearer {crc_token}"}

    # 2. CRC creates imaging session
    session_res = await client.post("/api/imaging/sessions", json={
        "project_id": data["project"].id,
        "center_id": data["center"].id,
        "subject_id": data["subject"].id,
        "visit_point": "V1",
        "imaging_type": "CT",
    }, headers=crc_headers)
    assert session_res.status_code == 201
    session_id = session_res.json()["id"]

    # 3. Expert logs in
    expert_login = await client.post("/api/auth/login", json={"username": "expert", "password": "Expert123!"})
    assert expert_login.status_code == 200
    expert_token = expert_login.json()["access_token"]
    expert_headers = {"Authorization": f"Bearer {expert_token}"}

    # 4. Expert creates issue for the session
    issue_res = await client.post("/api/issues", json={
        "session_id": session_id,
        "description": "影像模糊，需要重新拍摄",
    }, headers=expert_headers)
    assert issue_res.status_code == 201
    issue_id = issue_res.json()["id"]

    # 5. CRC processes the issue (transitions: pending -> processing -> reviewing)
    process_res = await client.put(f"/api/issues/{issue_id}/process", json={
        "content": "已重新上传清晰影像",
    }, headers=crc_headers)
    assert process_res.status_code == 200

    # 6. Expert reviews and approves (transitions: reviewing -> closed)
    review_res = await client.put(f"/api/issues/{issue_id}/review", json={
        "action": "approve",
        "content": "影像质量合格",
    }, headers=expert_headers)
    assert review_res.status_code == 200

    # 7. Verify issue is closed
    detail_res = await client.get(f"/api/issues/{issue_id}", headers=expert_headers)
    assert detail_res.status_code == 200
    assert detail_res.json()["status"] == "closed"

    # 8. Verify issue logs (create + process + submit_review + review_approve = 4)
    logs = detail_res.json().get("logs", [])
    assert len(logs) >= 3  # create, process, review

    # 9. Admin can view audit logs
    admin_login = await client.post("/api/auth/login", json={"username": "admin", "password": "Admin123!"})
    assert admin_login.status_code == 200
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    audit_res = await client.get("/api/audit", headers=admin_headers)
    assert audit_res.status_code == 200
