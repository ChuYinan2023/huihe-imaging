# 汇禾影像管理系统 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a complete medical imaging management system with DICOM anonymization, issue tracking, report signing, and multi-role RBAC.

**Architecture:** React + Ant Design frontend communicating via REST API with a Python FastAPI backend. SQLite for development, PostgreSQL for production. Celery + Redis for async tasks (DICOM anonymization, AI report analysis, SMS notifications). Local filesystem with StorageService abstraction for file storage.

**Tech Stack:** React 18, TypeScript, Vite, Ant Design 5, Zustand, React Router v6, Axios | Python 3.11+, FastAPI, SQLAlchemy 2.0, Alembic, Celery, Redis, pydicom, PyPDF2, ReportLab, pyjwt, httpx

**Reference design:** `docs/plans/2026-02-27-huihe-imaging-design.md`

---

## Phase 1: Backend Foundation (Tasks 1-6)

### Task 1: Backend Project Scaffolding

**Files:**
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/core/config.py`
- Create: `backend/app/core/database.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/tasks/__init__.py`
- Create: `backend/requirements.txt`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/.env.example`

**Step 1: Create requirements.txt**

```
# Web framework
fastapi==0.115.*
uvicorn[standard]==0.34.*
python-multipart==0.0.*

# Database
sqlalchemy==2.0.*
alembic==1.14.*
aiosqlite==0.20.*
asyncpg==0.30.*

# Auth
pyjwt==2.10.*
passlib[bcrypt]==1.7.*

# Config
pydantic-settings==2.7.*

# Async tasks
celery[redis]==5.4.*
redis==5.2.*

# Imaging
pydicom==3.0.*

# PDF
pypdf2==3.0.*
reportlab==4.2.*

# HTTP client
httpx==0.28.*

# Utils
python-dateutil==2.9.*

# Testing
pytest==8.3.*
pytest-asyncio==0.24.*
httpx  # also used as test client
```

**Step 2: Create config.py**

```python
# backend/app/core/config.py
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # App
    APP_NAME: str = "huihe-imaging"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./huihe.db"

    # JWT
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ISSUER: str = "huihe-imaging"
    JWT_LEEWAY_SECONDS: int = 30

    # Storage
    STORAGE_ROOT: Path = Path("storage")
    STORAGE_TMP_DIR: str = "tmp"
    STORAGE_ORIGINALS_DIR: str = "originals"
    STORAGE_ANONYMIZED_DIR: str = "anonymized"
    STORAGE_REPORTS_DIR: str = "reports"
    STORAGE_SIGNATURES_DIR: str = "signatures"

    # Upload
    MAX_FILE_SIZE_MB: int = 500
    ALLOWED_IMAGE_EXTENSIONS: set = {".dcm", ".jpg", ".jpeg", ".png"}

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # DICOM anonymization
    DICOM_UID_PREFIX: str = "2.25."
    DICOM_ANONYMIZATION_SALT: str = "change-me-in-production"

    # CSRF
    CSRF_SECRET_KEY: str = "change-me-csrf-secret"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
```

**Step 3: Create database.py**

```python
# backend/app/core/database.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session
```

**Step 4: Create main.py**

```python
# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

app = FastAPI(title=settings.APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME}
```

**Step 5: Create conftest.py for testing**

```python
# backend/tests/conftest.py
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.database import Base, get_db
from app.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSession = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def db_session():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with TestSession() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
```

**Step 6: Create __init__.py files and .env.example**

Create empty `__init__.py` in: `backend/app/`, `backend/app/core/`, `backend/app/api/`, `backend/app/models/`, `backend/app/services/`, `backend/app/tasks/`, `backend/tests/`

```
# backend/.env.example
DATABASE_URL=sqlite+aiosqlite:///./huihe.db
JWT_SECRET_KEY=change-me-in-production
CSRF_SECRET_KEY=change-me-csrf-secret
DICOM_ANONYMIZATION_SALT=change-me-salt
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

**Step 7: Set up Alembic**

Run: `cd backend && pip install -r requirements.txt && alembic init alembic`

Then edit `backend/alembic/env.py` to import `app.core.database.Base` and `app.models` for autogenerate.

**Step 8: Write and run health check test**

```python
# backend/tests/test_health.py
import pytest


@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "huihe-imaging"
```

Run: `cd backend && python -m pytest tests/test_health.py -v`
Expected: PASS

**Step 9: Commit**

```bash
git add backend/
git commit -m "feat: scaffold backend with FastAPI, SQLAlchemy, config, and test setup"
```

---

### Task 2: Database Models — User & Auth

**Files:**
- Create: `backend/app/models/user.py`
- Create: `backend/app/models/refresh_token.py`
- Create: `backend/tests/test_models_user.py`

**Step 1: Write the User model test**

```python
# backend/tests/test_models_user.py
import pytest
from app.models.user import User, UserRole
from sqlalchemy import select


@pytest.mark.asyncio
async def test_create_user(db_session):
    user = User(
        username="admin",
        email="admin@test.com",
        hashed_password="hashed",
        full_name="Admin User",
        role=UserRole.ADMIN,
        phone="13800001234",
    )
    db_session.add(user)
    await db_session.commit()

    result = await db_session.execute(select(User).where(User.username == "admin"))
    saved = result.scalar_one()
    assert saved.username == "admin"
    assert saved.role == UserRole.ADMIN
    assert saved.token_version == 1
    assert saved.is_active is True


@pytest.mark.asyncio
async def test_user_token_version_default(db_session):
    user = User(
        username="test",
        email="test@test.com",
        hashed_password="hashed",
        full_name="Test",
        role=UserRole.CRC,
    )
    db_session.add(user)
    await db_session.commit()
    assert user.token_version == 1
```

**Step 2: Run test — verify it fails**

Run: `cd backend && python -m pytest tests/test_models_user.py -v`
Expected: FAIL (models not defined)

**Step 3: Implement User model**

```python
# backend/app/models/user.py
import enum
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Boolean, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    CRC = "crc"
    CRA = "cra"
    DM = "dm"
    EXPERT = "expert"
    PM = "pm"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    token_version: Mapped[int] = mapped_column(Integer, default=1)
    signature_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
```

**Step 4: Implement RefreshToken model**

```python
# backend/app/models/refresh_token.py
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    jti: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    family_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
```

**Step 5: Update models/__init__.py to import all models**

```python
# backend/app/models/__init__.py
from app.models.user import User, UserRole
from app.models.refresh_token import RefreshToken
```

**Step 6: Run tests — verify they pass**

Run: `cd backend && python -m pytest tests/test_models_user.py -v`
Expected: PASS

**Step 7: Commit**

```bash
git add backend/app/models/ backend/tests/test_models_user.py
git commit -m "feat: add User and RefreshToken database models"
```

---

### Task 3: Database Models — Project, Center, Subject

**Files:**
- Create: `backend/app/models/project.py`
- Create: `backend/tests/test_models_project.py`

**Step 1: Write failing tests**

```python
# backend/tests/test_models_project.py
import pytest
from app.models.project import Project, Center, Subject, ProjectUser
from app.models.user import User, UserRole
from sqlalchemy import select


@pytest.mark.asyncio
async def test_create_project_with_center_and_subject(db_session):
    project = Project(code="PRJ001", name="Test Project", status="active")
    db_session.add(project)
    await db_session.flush()

    center = Center(project_id=project.id, code="CTR001", name="Test Center")
    db_session.add(center)
    await db_session.flush()

    subject = Subject(
        center_id=center.id,
        screening_number="S001",
        project_id=project.id,
    )
    db_session.add(subject)
    await db_session.commit()

    result = await db_session.execute(select(Subject).where(Subject.screening_number == "S001"))
    saved = result.scalar_one()
    assert saved.center_id == center.id
    assert saved.project_id == project.id


@pytest.mark.asyncio
async def test_project_user_association(db_session):
    user = User(
        username="pm1", email="pm@test.com", hashed_password="h",
        full_name="PM", role=UserRole.PM,
    )
    project = Project(code="PRJ002", name="Project 2", status="active")
    db_session.add_all([user, project])
    await db_session.flush()

    assoc = ProjectUser(user_id=user.id, project_id=project.id)
    db_session.add(assoc)
    await db_session.commit()

    result = await db_session.execute(
        select(ProjectUser).where(ProjectUser.user_id == user.id)
    )
    saved = result.scalar_one()
    assert saved.project_id == project.id
```

**Step 2: Run test — verify it fails**

Run: `cd backend && python -m pytest tests/test_models_project.py -v`
Expected: FAIL

**Step 3: Implement models**

```python
# backend/app/models/project.py
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active")
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class Center(Base):
    __tablename__ = "centers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (UniqueConstraint("project_id", "code", name="uq_center_project_code"),)


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    center_id: Mapped[int] = mapped_column(Integer, ForeignKey("centers.id"), nullable=False, index=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    screening_number: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (UniqueConstraint("project_id", "screening_number", name="uq_subject_project_screening"),)


class ProjectUser(Base):
    __tablename__ = "project_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), nullable=False, index=True)

    __table_args__ = (UniqueConstraint("user_id", "project_id", name="uq_project_user"),)
```

**Step 4: Update models/__init__.py**

```python
# backend/app/models/__init__.py
from app.models.user import User, UserRole
from app.models.refresh_token import RefreshToken
from app.models.project import Project, Center, Subject, ProjectUser
```

**Step 5: Run tests — verify pass**

Run: `cd backend && python -m pytest tests/test_models_project.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add backend/app/models/ backend/tests/test_models_project.py
git commit -m "feat: add Project, Center, Subject, ProjectUser models"
```

---

### Task 4: Database Models — ImagingSession, ImagingFile, AnonymizationLog

**Files:**
- Create: `backend/app/models/imaging.py`
- Create: `backend/tests/test_models_imaging.py`

**Step 1: Write failing tests**

```python
# backend/tests/test_models_imaging.py
import pytest
from app.models.imaging import ImagingSession, ImagingFile, ImagingStatus, AnonymizationLog
from app.models.project import Project, Center, Subject
from sqlalchemy import select


@pytest.mark.asyncio
async def test_create_imaging_session(db_session):
    project = Project(code="P1", name="P1", status="active")
    db_session.add(project)
    await db_session.flush()
    center = Center(project_id=project.id, code="C1", name="C1")
    db_session.add(center)
    await db_session.flush()
    subject = Subject(center_id=center.id, project_id=project.id, screening_number="S1")
    db_session.add(subject)
    await db_session.flush()

    session = ImagingSession(
        subject_id=subject.id,
        project_id=project.id,
        center_id=center.id,
        visit_point="V1",
        imaging_type="CT",
        status=ImagingStatus.UPLOADING,
        uploaded_by=1,
    )
    db_session.add(session)
    await db_session.commit()

    result = await db_session.execute(select(ImagingSession))
    saved = result.scalar_one()
    assert saved.visit_point == "V1"
    assert saved.status == ImagingStatus.UPLOADING


@pytest.mark.asyncio
async def test_imaging_status_values():
    assert ImagingStatus.UPLOADING.value == "uploading"
    assert ImagingStatus.ANONYMIZING.value == "anonymizing"
    assert ImagingStatus.COMPLETED.value == "completed"
    assert ImagingStatus.UPLOAD_FAILED.value == "upload_failed"
    assert ImagingStatus.ANONYMIZE_FAILED.value == "anonymize_failed"
    assert ImagingStatus.REJECTED.value == "rejected"
```

**Step 2: Run test — verify it fails**

Run: `cd backend && python -m pytest tests/test_models_imaging.py -v`

**Step 3: Implement models**

```python
# backend/app/models/imaging.py
import enum
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, ForeignKey, Enum, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ImagingStatus(str, enum.Enum):
    UPLOADING = "uploading"
    ANONYMIZING = "anonymizing"
    COMPLETED = "completed"
    UPLOAD_FAILED = "upload_failed"
    ANONYMIZE_FAILED = "anonymize_failed"
    REJECTED = "rejected"


class ImagingSession(Base):
    __tablename__ = "imaging_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subject_id: Mapped[int] = mapped_column(Integer, ForeignKey("subjects.id"), nullable=False, index=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    center_id: Mapped[int] = mapped_column(Integer, ForeignKey("centers.id"), nullable=False, index=True)
    visit_point: Mapped[str] = mapped_column(String(20), nullable=False)
    imaging_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[ImagingStatus] = mapped_column(Enum(ImagingStatus), default=ImagingStatus.UPLOADING)
    uploaded_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class ImagingFile(Base):
    __tablename__ = "imaging_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("imaging_sessions.id"), nullable=False, index=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    anonymized_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class AnonymizationLog(Base):
    __tablename__ = "anonymization_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("imaging_sessions.id"), nullable=False, index=True)
    file_id: Mapped[int] = mapped_column(Integer, ForeignKey("imaging_files.id"), nullable=False)
    original_tag_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    strategy_version: Mapped[str] = mapped_column(String(20), nullable=False)
    private_tags_removed: Mapped[int] = mapped_column(Integer, default=0)
    uid_mappings: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
```

**Step 4: Update models/__init__.py, run tests, commit**

Run: `cd backend && python -m pytest tests/test_models_imaging.py -v`
Expected: PASS

```bash
git add backend/app/models/ backend/tests/test_models_imaging.py
git commit -m "feat: add ImagingSession, ImagingFile, AnonymizationLog models"
```

---

### Task 5: Database Models — Issue, IssueLog, Report

**Files:**
- Create: `backend/app/models/issue.py`
- Create: `backend/app/models/report.py`
- Create: `backend/tests/test_models_issue.py`

**Step 1: Write failing tests**

```python
# backend/tests/test_models_issue.py
import pytest
from app.models.issue import Issue, IssueStatus, IssueLog


@pytest.mark.asyncio
async def test_issue_status_values():
    assert IssueStatus.PENDING.value == "pending"
    assert IssueStatus.PROCESSING.value == "processing"
    assert IssueStatus.REVIEWING.value == "reviewing"
    assert IssueStatus.CLOSED.value == "closed"
```

**Step 2: Implement Issue, IssueLog, Report models**

```python
# backend/app/models/issue.py
import enum
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class IssueStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    REVIEWING = "reviewing"
    CLOSED = "closed"


class Issue(Base):
    __tablename__ = "issues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("imaging_sessions.id"), nullable=False, index=True)
    subject_id: Mapped[int] = mapped_column(Integer, ForeignKey("subjects.id"), nullable=False, index=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    center_id: Mapped[int] = mapped_column(Integer, ForeignKey("centers.id"), nullable=False, index=True)
    visit_point: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[IssueStatus] = mapped_column(Enum(IssueStatus), default=IssueStatus.PENDING)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_to: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class IssueLog(Base):
    __tablename__ = "issue_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    issue_id: Mapped[int] = mapped_column(Integer, ForeignKey("issues.id"), nullable=False, index=True)
    operator_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    from_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    to_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
```

```python
# backend/app/models/report.py
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("imaging_sessions.id"), nullable=False, index=True)
    subject_id: Mapped[int] = mapped_column(Integer, ForeignKey("subjects.id"), nullable=False, index=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    issue_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("issues.id"), nullable=True)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    signed_file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
```

**Step 3: Update models/__init__.py, run tests, commit**

```python
# backend/app/models/__init__.py
from app.models.user import User, UserRole
from app.models.refresh_token import RefreshToken
from app.models.project import Project, Center, Subject, ProjectUser
from app.models.imaging import ImagingSession, ImagingFile, ImagingStatus, AnonymizationLog
from app.models.issue import Issue, IssueStatus, IssueLog
from app.models.report import Report
```

```bash
git add backend/app/models/ backend/tests/test_models_issue.py
git commit -m "feat: add Issue, IssueLog, Report models"
```

---

### Task 6: Database Models — AuditLog + Initial Alembic Migration

**Files:**
- Create: `backend/app/models/audit.py`
- Create: `backend/tests/test_models_audit.py`

**Step 1: Write failing test**

```python
# backend/tests/test_models_audit.py
import pytest
from app.models.audit import AuditLog
from sqlalchemy import select


@pytest.mark.asyncio
async def test_create_audit_log(db_session):
    log = AuditLog(
        operator_id=1,
        ip="192.168.1.1",
        user_agent="Mozilla/5.0",
        action="create_user",
        resource_type="user",
        resource_id="1",
        before_value=None,
        after_value='{"username":"admin"}',
    )
    db_session.add(log)
    await db_session.commit()

    result = await db_session.execute(select(AuditLog))
    saved = result.scalar_one()
    assert saved.action == "create_user"
    assert saved.ip == "192.168.1.1"
```

**Step 2: Implement AuditLog model**

```python
# backend/app/models/audit.py
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    operator_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    ip: Mapped[str] = mapped_column(String(45), nullable=False)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    resource_id: Mapped[str] = mapped_column(String(50), nullable=False)
    before_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    after_value: Mapped[str | None] = mapped_column(Text, nullable=True)
```

**Step 3: Update models/__init__.py**

```python
# add to models/__init__.py
from app.models.audit import AuditLog
```

**Step 4: Run all model tests**

Run: `cd backend && python -m pytest tests/ -v`
Expected: ALL PASS

**Step 5: Generate initial Alembic migration**

Run: `cd backend && alembic revision --autogenerate -m "initial models"`
Run: `cd backend && alembic upgrade head`

**Step 6: Commit**

```bash
git add backend/
git commit -m "feat: add AuditLog model and initial Alembic migration"
```

---

## Phase 2: Authentication & Security (Tasks 7-9)

### Task 7: Security Service — Password Hashing & JWT

**Files:**
- Create: `backend/app/core/security.py`
- Create: `backend/tests/test_security.py`

**Step 1: Write failing tests**

```python
# backend/tests/test_security.py
import pytest
from app.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    decode_token, hash_token,
)


def test_password_hash_and_verify():
    password = "SecurePass123!"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("wrong", hashed)


def test_create_access_token():
    token = create_access_token(user_id=1, role="admin", token_version=1)
    payload = decode_token(token, audience="access")
    assert payload["sub"] == "1"
    assert payload["role"] == "admin"
    assert payload["tv"] == 1
    assert payload["iss"] == "huihe-imaging"
    assert payload["aud"] == "access"


def test_create_refresh_token():
    token, jti, family_id = create_refresh_token(user_id=1, token_version=1)
    payload = decode_token(token, audience="refresh")
    assert payload["sub"] == "1"
    assert payload["aud"] == "refresh"
    assert payload["jti"] == jti
    assert payload["fid"] == family_id


def test_refresh_token_rotation():
    token, jti, family_id = create_refresh_token(user_id=1, token_version=1)
    new_token, new_jti, same_family = create_refresh_token(
        user_id=1, token_version=1, family_id=family_id
    )
    assert same_family == family_id
    assert new_jti != jti


def test_decode_token_wrong_audience():
    token = create_access_token(user_id=1, role="admin", token_version=1)
    with pytest.raises(Exception):
        decode_token(token, audience="refresh")


def test_hash_token():
    token = "some-token-string"
    hashed = hash_token(token)
    assert len(hashed) == 64  # SHA256 hex digest
    assert hash_token(token) == hashed  # deterministic
```

**Step 2: Run tests — verify fail**

**Step 3: Implement security.py**

```python
# backend/app/core/security.py
import hashlib
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_access_token(user_id: int, role: str, token_version: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "tv": token_version,
        "iss": settings.JWT_ISSUER,
        "aud": "access",
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(
    user_id: int,
    token_version: int,
    family_id: str | None = None,
) -> tuple[str, str, str]:
    now = datetime.now(timezone.utc)
    jti = str(uuid.uuid4())
    fid = family_id or str(uuid.uuid4())
    payload = {
        "sub": str(user_id),
        "tv": token_version,
        "iss": settings.JWT_ISSUER,
        "aud": "refresh",
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        "jti": jti,
        "fid": fid,
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, jti, fid


def decode_token(token: str, audience: str) -> dict:
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
        issuer=settings.JWT_ISSUER,
        audience=audience,
        leeway=timedelta(seconds=settings.JWT_LEEWAY_SECONDS),
        options={"require": ["exp", "nbf", "iat", "iss", "aud"]},
    )
```

**Step 4: Run tests — verify pass, commit**

```bash
git add backend/app/core/security.py backend/tests/test_security.py
git commit -m "feat: add password hashing and JWT token utilities"
```

---

### Task 8: Auth API — Login, Refresh, Logout

**Files:**
- Create: `backend/app/api/auth.py`
- Create: `backend/app/api/deps.py`
- Create: `backend/tests/test_api_auth.py`
- Modify: `backend/app/main.py` (register router)

**Step 1: Write failing tests**

```python
# backend/tests/test_api_auth.py
import pytest
from app.models.user import User, UserRole
from app.core.security import hash_password


@pytest.fixture
async def test_user(db_session):
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=hash_password("TestPass123!"),
        full_name="Test User",
        role=UserRole.CRC,
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest.mark.asyncio
async def test_login_success(client, test_user):
    response = await client.post("/api/auth/login", json={
        "username": "testuser",
        "password": "TestPass123!",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "csrf_token" in data
    # Check refresh token is set as HttpOnly cookie
    assert "refresh_token" in response.cookies


@pytest.mark.asyncio
async def test_login_wrong_password(client, test_user):
    response = await client.post("/api/auth/login", json={
        "username": "testuser",
        "password": "wrong",
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client):
    response = await client.post("/api/auth/login", json={
        "username": "nobody",
        "password": "pass",
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user(client, test_user):
    login = await client.post("/api/auth/login", json={
        "username": "testuser",
        "password": "TestPass123!",
    })
    token = login.json()["access_token"]
    response = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert data["role"] == "crc"
```

**Step 2: Implement deps.py (dependency injection for auth)**

```python
# backend/app/api/deps.py
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User

bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = decode_token(credentials.credentials, audience="access")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user_id = int(payload["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    if user.token_version != payload.get("tv"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked")

    return user


def require_roles(*roles):
    def checker(user: User = Depends(get_current_user)):
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user
    return checker
```

**Step 3: Implement auth.py API router**

```python
# backend/app/api/auth.py
import secrets
from fastapi import APIRouter, Depends, HTTPException, Response, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import (
    verify_password, create_access_token, create_refresh_token,
    decode_token, hash_token,
)
from app.models.user import User
from app.models.refresh_token import RefreshToken
from app.api.deps import get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    csrf_token: str
    user: dict


@router.post("/login")
async def login(
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account disabled")

    access_token = create_access_token(user.id, user.role.value, user.token_version)
    refresh_token_str, jti, family_id = create_refresh_token(user.id, user.token_version)
    csrf_token = secrets.token_urlsafe(32)

    # Store refresh token hash
    rt = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(refresh_token_str),
        jti=jti,
        family_id=family_id,
        expires_at=user.created_at,  # will be set properly via JWT exp
    )
    db.add(rt)
    await db.commit()

    response.set_cookie(
        key="refresh_token",
        value=refresh_token_str,
        httponly=True,
        secure=False,  # True in production
        samesite="strict",
        max_age=7 * 24 * 3600,
        path="/api/auth",
    )

    return {
        "access_token": access_token,
        "csrf_token": csrf_token,
        "user": {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role.value,
            "email": user.email,
        },
    }


@router.post("/refresh")
async def refresh_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token")

    try:
        payload = decode_token(token, audience="refresh")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    jti = payload["jti"]
    family_id = payload["fid"]
    user_id = int(payload["sub"])

    # Find the token record
    result = await db.execute(select(RefreshToken).where(RefreshToken.jti == jti))
    rt = result.scalar_one_or_none()

    if not rt:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token not found")

    # Detect reuse: if token already used, invalidate entire family
    if rt.used:
        await db.execute(
            RefreshToken.__table__.update()
            .where(RefreshToken.family_id == family_id)
            .values(used=True)
        )
        await db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token reuse detected")

    # Mark current token as used
    rt.used = True

    # Get user and check token_version
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user or not user.is_active or user.token_version != payload.get("tv"):
        await db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked")

    # Issue new tokens
    new_access = create_access_token(user.id, user.role.value, user.token_version)
    new_refresh, new_jti, same_family = create_refresh_token(
        user.id, user.token_version, family_id=family_id
    )

    new_rt = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(new_refresh),
        jti=new_jti,
        family_id=same_family,
        expires_at=rt.expires_at,
    )
    db.add(new_rt)
    await db.commit()

    response.set_cookie(
        key="refresh_token",
        value=new_refresh,
        httponly=True,
        secure=False,
        samesite="strict",
        max_age=7 * 24 * 3600,
        path="/api/auth",
    )

    return {"access_token": new_access}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("refresh_token", path="/api/auth")
    return {"message": "Logged out"}


@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role.value,
        "email": user.email,
        "phone": user.phone,
    }
```

**Step 4: Register router in main.py**

Add to `backend/app/main.py`:
```python
from app.api.auth import router as auth_router
app.include_router(auth_router)
```

**Step 5: Run tests — verify pass, commit**

Run: `cd backend && python -m pytest tests/test_api_auth.py -v`

```bash
git add backend/
git commit -m "feat: add auth API with login, refresh token rotation, and logout"
```

---

### Task 9: RBAC Permissions Middleware

**Files:**
- Create: `backend/app/core/permissions.py`
- Create: `backend/tests/test_permissions.py`

**Step 1: Write failing tests**

```python
# backend/tests/test_permissions.py
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
```

**Step 2: Implement permissions.py**

```python
# backend/app/core/permissions.py
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
    UserRole.ADMIN: {
        Permission.MANAGE_USERS,
        Permission.MANAGE_PROJECTS,
        Permission.DOWNLOAD_DATA,
        Permission.VIEW_AUDIT_LOG,
        Permission.VIEW_REPORTS,
        Permission.VIEW_IMAGING,
        Permission.VIEW_ISSUES,
    },
    UserRole.PM: {
        Permission.MANAGE_PROJECTS,
        Permission.DOWNLOAD_DATA,
        Permission.VIEW_REPORTS,
        Permission.VIEW_IMAGING,
        Permission.VIEW_ISSUES,
    },
    UserRole.EXPERT: {
        Permission.CREATE_ISSUE,
        Permission.REVIEW_ISSUE,
        Permission.UPLOAD_REPORT,
        Permission.VIEW_REPORTS,
        Permission.VIEW_IMAGING,
        Permission.VIEW_ISSUES,
    },
    UserRole.CRC: {
        Permission.UPLOAD_IMAGING,
        Permission.PROCESS_ISSUE,
        Permission.VIEW_REPORTS,
        Permission.VIEW_IMAGING,
        Permission.VIEW_ISSUES,
    },
    UserRole.CRA: {
        Permission.VIEW_REPORTS,
        Permission.VIEW_IMAGING,
        Permission.VIEW_ISSUES,
    },
    UserRole.DM: {
        Permission.DOWNLOAD_DATA,
        Permission.VIEW_REPORTS,
        Permission.VIEW_IMAGING,
        Permission.VIEW_ISSUES,
    },
}


def check_permission(role: UserRole, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, set())
```

**Step 3: Run tests — verify pass, commit**

```bash
git add backend/app/core/permissions.py backend/tests/test_permissions.py
git commit -m "feat: add RBAC permission matrix and check_permission utility"
```

---

## Phase 3: Core Services (Tasks 10-13)

### Task 10: StorageService Abstraction

**Files:**
- Create: `backend/app/services/storage_service.py`
- Create: `backend/tests/test_storage_service.py`

**Step 1: Write failing tests**

```python
# backend/tests/test_storage_service.py
import os
import pytest
from pathlib import Path
from app.services.storage_service import LocalStorage


@pytest.fixture
def storage(tmp_path):
    return LocalStorage(root_dir=tmp_path)


def test_save_and_get(storage, tmp_path):
    data = b"hello world"
    path = storage.save("test/file.txt", data)
    assert os.path.exists(tmp_path / path)
    retrieved = storage.get(path)
    assert retrieved == data


def test_delete(storage):
    storage.save("test/file.txt", b"data")
    assert storage.delete("test/file.txt")
    assert not storage.delete("nonexistent.txt")


def test_save_creates_subdirectories(storage, tmp_path):
    storage.save("deep/nested/dir/file.bin", b"data")
    assert os.path.exists(tmp_path / "deep/nested/dir/file.bin")


def test_atomic_move(storage, tmp_path):
    tmp_file = tmp_path / "tmp" / "upload.bin"
    tmp_file.parent.mkdir(parents=True, exist_ok=True)
    tmp_file.write_bytes(b"data")
    storage.atomic_move("tmp/upload.bin", "final/upload.bin")
    assert not tmp_file.exists()
    assert (tmp_path / "final/upload.bin").exists()
```

**Step 2: Implement storage_service.py**

```python
# backend/app/services/storage_service.py
import os
from abc import ABC, abstractmethod
from pathlib import Path


class StorageService(ABC):
    @abstractmethod
    def save(self, path: str, data: bytes) -> str: ...

    @abstractmethod
    def get(self, path: str) -> bytes: ...

    @abstractmethod
    def delete(self, path: str) -> bool: ...

    @abstractmethod
    def get_url(self, path: str) -> str: ...

    @abstractmethod
    def atomic_move(self, src: str, dst: str) -> None: ...

    @abstractmethod
    def exists(self, path: str) -> bool: ...


class LocalStorage(StorageService):
    def __init__(self, root_dir: Path):
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def _full_path(self, path: str) -> Path:
        # Prevent directory traversal
        resolved = (self.root_dir / path).resolve()
        if not str(resolved).startswith(str(self.root_dir.resolve())):
            raise ValueError("Path traversal detected")
        return resolved

    def save(self, path: str, data: bytes) -> str:
        full = self._full_path(path)
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_bytes(data)
        return path

    def get(self, path: str) -> bytes:
        return self._full_path(path).read_bytes()

    def delete(self, path: str) -> bool:
        full = self._full_path(path)
        if full.exists():
            full.unlink()
            return True
        return False

    def get_url(self, path: str) -> str:
        return f"/storage/{path}"

    def atomic_move(self, src: str, dst: str) -> None:
        src_path = self._full_path(src)
        dst_path = self._full_path(dst)
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        os.replace(str(src_path), str(dst_path))

    def exists(self, path: str) -> bool:
        return self._full_path(path).exists()
```

**Step 3: Run tests — verify pass, commit**

```bash
git add backend/app/services/storage_service.py backend/tests/test_storage_service.py
git commit -m "feat: add StorageService abstraction with LocalStorage implementation"
```

---

### Task 11: FSM State Machine

**Files:**
- Create: `backend/app/services/state_machine.py`
- Create: `backend/tests/test_state_machine.py`

**Step 1: Write failing tests**

```python
# backend/tests/test_state_machine.py
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
```

**Step 2: Implement state_machine.py**

```python
# backend/app/services/state_machine.py
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
```

**Step 3: Run tests — verify pass, commit**

```bash
git add backend/app/services/state_machine.py backend/tests/test_state_machine.py
git commit -m "feat: add FSM state machines for imaging and issue status transitions"
```

---

### Task 12: Audit Log Service

**Files:**
- Create: `backend/app/services/audit_service.py`
- Create: `backend/tests/test_audit_service.py`

**Step 1: Write failing tests**

```python
# backend/tests/test_audit_service.py
import pytest
from app.services.audit_service import AuditService, sanitize_value
from app.models.audit import AuditLog
from sqlalchemy import select


def test_sanitize_phone():
    assert sanitize_value("phone", "13812345678") == "138****5678"


def test_sanitize_id_card():
    assert sanitize_value("id_card", "110101199001011234") == "110***********1234"


def test_sanitize_normal_field():
    assert sanitize_value("username", "admin") == "admin"


@pytest.mark.asyncio
async def test_log_action(db_session):
    service = AuditService(db_session)
    await service.log(
        operator_id=1,
        ip="127.0.0.1",
        user_agent="test",
        action="create",
        resource_type="user",
        resource_id="1",
        before_value=None,
        after_value={"username": "admin", "phone": "13812345678"},
    )
    result = await db_session.execute(select(AuditLog))
    log = result.scalar_one()
    assert log.action == "create"
    assert "138****5678" in log.after_value
```

**Step 2: Implement audit_service.py**

```python
# backend/app/services/audit_service.py
import json
import re
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog

SENSITIVE_FIELDS = {"phone", "mobile", "id_card", "id_number", "identity"}


def sanitize_value(field_name: str, value: str) -> str:
    if field_name in SENSITIVE_FIELDS:
        if re.match(r"^\d{11}$", value):  # phone
            return f"{value[:3]}****{value[-4:]}"
        if re.match(r"^\d{17}[\dXx]$", value):  # id card
            return f"{value[:3]}{'*' * 11}{value[-4:]}"
    return value


def sanitize_dict(data: dict | None) -> str | None:
    if data is None:
        return None
    sanitized = {}
    for k, v in data.items():
        if isinstance(v, str):
            sanitized[k] = sanitize_value(k, v)
        else:
            sanitized[k] = v
    return json.dumps(sanitized, ensure_ascii=False)


class AuditService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def log(
        self,
        operator_id: int,
        ip: str,
        user_agent: str | None,
        action: str,
        resource_type: str,
        resource_id: str,
        before_value: dict | None = None,
        after_value: dict | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            operator_id=operator_id,
            ip=ip,
            user_agent=user_agent,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            before_value=sanitize_dict(before_value),
            after_value=sanitize_dict(after_value),
        )
        self.db.add(entry)
        await self.db.flush()
        return entry
```

**Step 3: Run tests — verify pass, commit**

```bash
git add backend/app/services/audit_service.py backend/tests/test_audit_service.py
git commit -m "feat: add AuditService with field-level sanitization"
```

---

### Task 13: DICOM Anonymization Service

**Files:**
- Create: `backend/app/services/dicom_service.py`
- Create: `backend/tests/test_dicom_service.py`
- Create: `backend/tests/fixtures/` (test DICOM files)

**Step 1: Write failing tests**

```python
# backend/tests/test_dicom_service.py
import pytest
from app.services.dicom_service import (
    DicomAnonymizer, generate_uid, PHI_TAGS, ANONYMIZATION_STRATEGY_VERSION,
)


def test_generate_uid_format():
    uid = generate_uid("1.2.3.4.5", "test-salt")
    assert uid.startswith("2.25.")
    assert len(uid) <= 64
    # Only digits and dots
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
    # Key PHI tags must be in the blacklist
    assert (0x0010, 0x0010) in PHI_TAGS  # PatientName
    assert (0x0010, 0x0020) in PHI_TAGS  # PatientID
    assert (0x0010, 0x0030) in PHI_TAGS  # PatientBirthDate


def test_strategy_version():
    assert ANONYMIZATION_STRATEGY_VERSION == "1.0"
```

**Step 2: Implement dicom_service.py**

```python
# backend/app/services/dicom_service.py
import hashlib
from pathlib import Path

from app.core.config import settings

ANONYMIZATION_STRATEGY_VERSION = "1.0"

# PHI tag blacklist (DICOM tag group, element)
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

# UID tags to rewrite
UID_TAGS = {
    (0x0020, 0x000D),  # StudyInstanceUID
    (0x0020, 0x000E),  # SeriesInstanceUID
    (0x0008, 0x0018),  # SOPInstanceUID
}


def generate_uid(original_uid: str, salt: str) -> str:
    """Generate a compliant DICOM UID: 2.25.{hash_decimal}, max 64 chars."""
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
        """Anonymize a DICOM file. Returns anonymization metadata."""
        import pydicom

        ds = pydicom.dcmread(str(input_path))

        # Compute original tag hash for traceability
        tag_snapshot = str(sorted(
            (str(tag), str(ds.get(tag, "")))
            for tag in PHI_TAGS if tag in ds
        ))
        original_tag_hash = hashlib.sha256(tag_snapshot.encode()).hexdigest()

        # Remove PHI tags
        for tag in PHI_TAGS:
            if tag in ds:
                del ds[tag]

        # Remove private tags
        private_count = 0
        private_tags = [elem.tag for elem in ds if elem.tag.is_private]
        for tag in private_tags:
            del ds[tag]
            private_count += 1

        # Rewrite UIDs
        uid_mappings = {}
        for tag in UID_TAGS:
            if tag in ds:
                original = str(ds[tag].value)
                new_uid = generate_uid(original, self.salt)
                uid_mappings[original] = new_uid
                ds[tag].value = new_uid

        # Save anonymized file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        ds.save_as(str(output_path))

        return {
            "original_tag_hash": original_tag_hash,
            "strategy_version": ANONYMIZATION_STRATEGY_VERSION,
            "private_tags_removed": private_count,
            "uid_mappings": uid_mappings,
        }
```

**Step 3: Run tests — verify pass, commit**

```bash
git add backend/app/services/dicom_service.py backend/tests/test_dicom_service.py
git commit -m "feat: add DICOM anonymization service with PHI removal and UID rewriting"
```

---

## Phase 4: API Endpoints (Tasks 14-20)

### Task 14: User Management API

**Files:**
- Create: `backend/app/api/users.py`
- Create: `backend/tests/test_api_users.py`
- Modify: `backend/app/main.py` (register router)

**Step 1: Write failing tests**

```python
# backend/tests/test_api_users.py
import pytest
from app.models.user import User, UserRole
from app.core.security import hash_password, create_access_token


@pytest.fixture
async def admin_token(db_session):
    admin = User(
        username="admin", email="admin@test.com",
        hashed_password=hash_password("Admin123!"),
        full_name="Admin", role=UserRole.ADMIN,
    )
    db_session.add(admin)
    await db_session.commit()
    return create_access_token(admin.id, admin.role.value, admin.token_version)


@pytest.mark.asyncio
async def test_create_user(client, admin_token):
    response = await client.post(
        "/api/users",
        json={
            "username": "newuser",
            "email": "new@test.com",
            "password": "Pass123!",
            "full_name": "New User",
            "role": "crc",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    assert response.json()["username"] == "newuser"


@pytest.mark.asyncio
async def test_list_users(client, admin_token):
    response = await client.get(
        "/api/users",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert isinstance(response.json()["items"], list)


@pytest.mark.asyncio
async def test_non_admin_cannot_create_user(client, db_session):
    crc = User(
        username="crc1", email="crc@test.com",
        hashed_password=hash_password("Pass123!"),
        full_name="CRC", role=UserRole.CRC,
    )
    db_session.add(crc)
    await db_session.commit()
    token = create_access_token(crc.id, crc.role.value, crc.token_version)
    response = await client.post(
        "/api/users",
        json={
            "username": "another", "email": "a@t.com",
            "password": "Pass123!", "full_name": "A", "role": "crc",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
```

**Step 2: Implement users.py**

```python
# backend/app/api/users.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import hash_password
from app.core.permissions import Permission, check_permission
from app.api.deps import get_current_user
from app.models.user import User, UserRole

router = APIRouter(prefix="/api/users", tags=["users"])


class CreateUserRequest(BaseModel):
    username: str
    email: str
    password: str
    full_name: str
    role: str
    phone: str | None = None


class UpdateUserRequest(BaseModel):
    email: str | None = None
    full_name: str | None = None
    role: str | None = None
    phone: str | None = None
    is_active: bool | None = None


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


@router.post("", status_code=201)
async def create_user(
    body: CreateUserRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not check_permission(current_user.role, Permission.MANAGE_USERS):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    existing = await db.execute(select(User).where(User.username == body.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already exists")

    user = User(
        username=body.username,
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        role=UserRole(body.role),
        phone=body.phone,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return {
        "id": user.id, "username": user.username,
        "email": user.email, "full_name": user.full_name,
        "role": user.role.value, "is_active": user.is_active,
    }


@router.get("")
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not check_permission(current_user.role, Permission.MANAGE_USERS):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    total_result = await db.execute(select(func.count(User.id)))
    total = total_result.scalar()

    result = await db.execute(
        select(User).offset((page - 1) * page_size).limit(page_size)
    )
    users = result.scalars().all()

    return {
        "items": [
            {
                "id": u.id, "username": u.username, "email": u.email,
                "full_name": u.full_name, "role": u.role.value,
                "is_active": u.is_active, "phone": u.phone,
            }
            for u in users
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.put("/{user_id}")
async def update_user(
    user_id: int,
    body: UpdateUserRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not check_permission(current_user.role, Permission.MANAGE_USERS):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if body.email is not None:
        user.email = body.email
    if body.full_name is not None:
        user.full_name = body.full_name
    if body.role is not None:
        user.role = UserRole(body.role)
    if body.phone is not None:
        user.phone = body.phone
    if body.is_active is not None:
        user.is_active = body.is_active

    await db.commit()
    return {"message": "Updated"}


@router.put("/{user_id}/reset-password")
async def reset_password(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not check_permission(current_user.role, Permission.MANAGE_USERS):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    new_password = "Huihe@2026"  # default reset password
    user.hashed_password = hash_password(new_password)
    user.token_version += 1  # force re-login
    await db.commit()
    return {"message": "Password reset", "temp_password": new_password}
```

**Step 3: Register router in main.py, run tests, commit**

```bash
git add backend/app/api/users.py backend/tests/test_api_users.py backend/app/main.py
git commit -m "feat: add user management API with CRUD and role-based access"
```

---

### Task 15: Project Management API

**Files:**
- Create: `backend/app/api/projects.py`
- Create: `backend/tests/test_api_projects.py`

Implementation follows the same pattern as Task 14: CRUD for projects, centers, and project-user associations. PM and Admin roles only. Includes listing, creating, editing projects and configuring centers under projects.

**Commit:** `git commit -m "feat: add project and center management API"`

---

### Task 16: Imaging Upload API (with chunked upload)

**Files:**
- Create: `backend/app/api/imaging.py`
- Create: `backend/app/services/upload_service.py`
- Create: `backend/tests/test_api_imaging.py`

Key implementation:
- `POST /api/imaging/sessions` — create upload session with metadata
- `POST /api/imaging/sessions/{id}/chunks` — upload file chunks with streaming SHA256
- `POST /api/imaging/sessions/{id}/complete` — finalize upload, verify hash, atomic move
- `GET /api/imaging` — list with multi-dimensional filtering (project, center, subject, status)
- `GET /api/imaging/by-subject` — subject-grouped view

The upload service handles:
- Streaming SHA256 computation per chunk
- Temporary file storage in `storage/tmp/`
- Hash verification on completion
- `os.replace()` atomic move to final path
- MIME + extension dual validation

**Commit:** `git commit -m "feat: add imaging upload API with chunked upload and hash verification"`

---

### Task 17: DICOM Anonymization Celery Task

**Files:**
- Create: `backend/app/tasks/celery_app.py`
- Create: `backend/app/tasks/imaging_tasks.py`
- Create: `backend/tests/test_imaging_tasks.py`

Key implementation:
- Celery app configuration with 3 queues (imaging, ai, notification)
- `anonymize_imaging_session` task with idempotency via Redis key (`session_id:file_hash`)
- Calls `DicomAnonymizer.anonymize()` for DICOM files
- Saves `AnonymizationLog` records
- Updates session status via FSM transitions

**Commit:** `git commit -m "feat: add Celery task for DICOM anonymization with idempotency"`

---

### Task 18: Issue Tracking API

**Files:**
- Create: `backend/app/api/issues.py`
- Create: `backend/tests/test_api_issues.py`

Key implementation:
- `POST /api/issues` — Expert creates issue (Permission.CREATE_ISSUE)
- `GET /api/issues` — list with multi-dimensional filtering
- `GET /api/issues/{id}` — detail with issue logs
- `PUT /api/issues/{id}/process` — CRC submits feedback (FSM: pending → processing → reviewing)
- `PUT /api/issues/{id}/review` — Expert reviews (FSM: reviewing → closed or → pending)
- All transitions create `IssueLog` entries
- Status changes trigger notification tasks

**Commit:** `git commit -m "feat: add issue tracking API with FSM transitions and audit trail"`

---

### Task 19: Report Management API

**Files:**
- Create: `backend/app/api/reports.py`
- Create: `backend/app/services/signature_service.py`
- Create: `backend/app/tasks/ai_tasks.py`
- Create: `backend/tests/test_api_reports.py`

Key implementation:
- `POST /api/reports` — Expert uploads PDF report
- `GET /api/reports` — list with filtering
- `POST /api/reports/{id}/sign` — compose signature onto PDF (PyPDF2 + ReportLab)
- `GET /api/reports/{id}/download` — download report file
- AI task triggered on upload: extract PDF content and save summary

**Commit:** `git commit -m "feat: add report management API with PDF signing and AI summary"`

---

### Task 20: Audit Log API + Notification Task

**Files:**
- Create: `backend/app/api/audit.py`
- Create: `backend/app/tasks/notification_tasks.py`
- Create: `backend/tests/test_api_audit.py`

Key implementation:
- `GET /api/audit` — Admin-only, paginated log list with filters
- `send_sms_notification` Celery task with idempotency
- SMS service interface (stub for external SMS provider)

**Commit:** `git commit -m "feat: add audit log API and SMS notification task"`

---

## Phase 5: Frontend Foundation (Tasks 21-24)

### Task 21: Frontend Project Scaffolding

**Files:**
- Create: `frontend/` (via Vite)
- Create: `frontend/src/services/api.ts`
- Create: `frontend/src/stores/auth.ts`
- Create: `frontend/src/router/index.tsx`
- Create: `frontend/src/layouts/MainLayout.tsx`

**Step 1: Scaffold React project**

Run:
```bash
cd /home/chu2026/Documents/github/huihe-imaging
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install antd @ant-design/icons react-router-dom zustand axios dayjs
```

**Step 2: Create API service with Axios interceptors**

```typescript
// frontend/src/services/api.ts
import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  withCredentials: true,
});

let accessToken: string | null = null;
let csrfToken: string | null = null;

export function setTokens(access: string, csrf: string) {
  accessToken = access;
  csrfToken = csrf;
}

export function clearTokens() {
  accessToken = null;
  csrfToken = null;
}

api.interceptors.request.use((config) => {
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  if (csrfToken) {
    config.headers['X-CSRF-Token'] = csrfToken;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      try {
        const res = await axios.post('/api/auth/refresh', {}, { withCredentials: true });
        accessToken = res.data.access_token;
        error.config.headers.Authorization = `Bearer ${accessToken}`;
        return axios(error.config);
      } catch {
        clearTokens();
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export default api;
```

**Step 3: Create auth store**

```typescript
// frontend/src/stores/auth.ts
import { create } from 'zustand';
import api, { setTokens, clearTokens } from '../services/api';

interface User {
  id: number;
  username: string;
  full_name: string;
  role: string;
  email: string;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  fetchMe: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,

  login: async (username, password) => {
    const res = await api.post('/auth/login', { username, password });
    setTokens(res.data.access_token, res.data.csrf_token);
    set({ user: res.data.user, isAuthenticated: true });
  },

  logout: async () => {
    await api.post('/auth/logout');
    clearTokens();
    set({ user: null, isAuthenticated: false });
  },

  fetchMe: async () => {
    const res = await api.get('/auth/me');
    set({ user: res.data, isAuthenticated: true });
  },
}));
```

**Step 4: Create router and MainLayout**

Set up React Router with protected routes and sidebar layout using Ant Design `Layout`, `Menu`, `Sider`.

**Step 5: Verify dev server starts**

Run: `cd frontend && npm run dev`
Expected: Vite dev server starts on http://localhost:5173

**Step 6: Commit**

```bash
git add frontend/
git commit -m "feat: scaffold React frontend with Vite, Ant Design, auth store, and router"
```

---

### Task 22: Login Page

**Files:**
- Create: `frontend/src/pages/login/LoginPage.tsx`

Ant Design `Form` with username/password fields, calls `useAuthStore.login()`, redirects to `/dashboard` on success.

**Commit:** `git commit -m "feat: add login page with auth integration"`

---

### Task 23: Dashboard (Workbench) Page

**Files:**
- Create: `frontend/src/pages/dashboard/DashboardPage.tsx`

Ant Design `Card` + `Statistic` components showing subject/imaging/issue counts. `Table` for recent operation records. `Alert` for CRC event reminders.

**Commit:** `git commit -m "feat: add dashboard page with statistics and event reminders"`

---

### Task 24: Shared Layout & Navigation

**Files:**
- Modify: `frontend/src/layouts/MainLayout.tsx`
- Create: `frontend/src/components/ProtectedRoute.tsx`

Ant Design `Layout` with `Sider` navigation menu (role-based menu items), `Header` with user info + logout, `Content` area. `ProtectedRoute` component checks auth and permissions.

**Commit:** `git commit -m "feat: add shared layout with role-based navigation"`

---

## Phase 6: Frontend Feature Pages (Tasks 25-31)

### Task 25: User Management Page

**Files:**
- Create: `frontend/src/pages/users/UserListPage.tsx`
- Create: `frontend/src/pages/users/UserFormModal.tsx`
- Create: `frontend/src/services/userService.ts`

Ant Design `Table` with user list, `Modal` with `Form` for create/edit, role selection, password reset button. Admin-only access.

**Commit:** `git commit -m "feat: add user management page with CRUD modals"`

---

### Task 26: Project Management Page

**Files:**
- Create: `frontend/src/pages/projects/ProjectListPage.tsx`
- Create: `frontend/src/pages/projects/CenterConfigModal.tsx`
- Create: `frontend/src/services/projectService.ts`

Project list with create/edit. Expandable rows showing centers. Modal for center configuration.

**Commit:** `git commit -m "feat: add project management page with center configuration"`

---

### Task 27: Imaging Upload Page

**Files:**
- Create: `frontend/src/pages/imaging/ImagingUploadPage.tsx`
- Create: `frontend/src/services/imagingService.ts`
- Create: `frontend/src/utils/fileUpload.ts`

Multi-step form: select project/center/subject/visit/type → file selection with MIME+extension validation → chunked upload with progress bar → SHA256 computation in browser (Web Crypto API). Resumable upload support.

**Commit:** `git commit -m "feat: add imaging upload page with chunked upload and progress"`

---

### Task 28: Imaging List & Center Page

**Files:**
- Create: `frontend/src/pages/imaging/ImagingListPage.tsx`

Ant Design `Table` with multi-dimensional filtering (project, center, subject, status). Toggle between imaging list and subject-grouped view. Export and download buttons (permission-gated).

**Commit:** `git commit -m "feat: add imaging list page with filtering and subject view"`

---

### Task 29: Issue Tracking Pages

**Files:**
- Create: `frontend/src/pages/issues/IssueListPage.tsx`
- Create: `frontend/src/pages/issues/IssueDetailPage.tsx`
- Create: `frontend/src/pages/issues/CreateIssueModal.tsx`
- Create: `frontend/src/services/issueService.ts`

Issue list with status badges and filters. Detail page with timeline of issue logs. CRC feedback form. Expert review buttons (approve/reject). Create issue modal for experts.

**Commit:** `git commit -m "feat: add issue tracking pages with create, feedback, and review"`

---

### Task 30: Report Management Page

**Files:**
- Create: `frontend/src/pages/reports/ReportListPage.tsx`
- Create: `frontend/src/services/reportService.ts`

Report list with filters. AI summary display in expandable rows. Upload report button (expert). Sign report button. Download buttons (permission-gated).

**Commit:** `git commit -m "feat: add report management page with signing and AI summary"`

---

### Task 31: Audit Log & Settings Pages

**Files:**
- Create: `frontend/src/pages/audit/AuditLogPage.tsx`
- Create: `frontend/src/pages/settings/SettingsPage.tsx`
- Create: `frontend/src/services/auditService.ts`

Audit log: Admin-only table with all operation logs. Settings: password change form + signature image upload.

**Commit:** `git commit -m "feat: add audit log page and user settings with signature upload"`

---

## Phase 7: Integration & Polish (Tasks 32-34)

### Task 32: Backend-Frontend Integration & Proxy

**Files:**
- Modify: `frontend/vite.config.ts` (add proxy)
- Create: `docker-compose.yml` (optional: Redis for Celery)

Add Vite proxy to forward `/api` requests to FastAPI. Verify all API endpoints work end-to-end.

**Commit:** `git commit -m "feat: add dev proxy and verify frontend-backend integration"`

---

### Task 33: Seed Data & Dev Utilities

**Files:**
- Create: `backend/scripts/seed.py`

Create seed script that populates: admin user, sample project with centers, test users for each role. Makes local development easy.

**Commit:** `git commit -m "feat: add seed script for development data"`

---

### Task 34: End-to-End Smoke Test

**Files:**
- Create: `backend/tests/test_e2e_flow.py`

Test the complete flow: login → create project → create center → upload imaging → trigger anonymization → create issue → CRC feedback → expert review → upload report → sign report.

**Commit:** `git commit -m "test: add end-to-end smoke test for core business flow"`

---

## Summary

| Phase | Tasks | Description |
|-------|-------|-------------|
| 1 | 1-6 | Backend scaffolding + all database models |
| 2 | 7-9 | Authentication, JWT, RBAC |
| 3 | 10-13 | Core services (storage, FSM, audit, DICOM) |
| 4 | 14-20 | All backend API endpoints |
| 5 | 21-24 | Frontend scaffolding + auth + layout |
| 6 | 25-31 | All frontend feature pages |
| 7 | 32-34 | Integration, seed data, E2E tests |

Total: **34 tasks** across 7 phases.
