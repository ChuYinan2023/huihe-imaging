"""Seed script for development data.

Usage: cd backend && source venv/bin/activate && python -m scripts.seed
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings
from app.core.database import Base
from app.core.security import hash_password
from app.models import User, UserRole, Project, Center, Subject, ProjectUser


async def seed():
    engine = create_async_engine(settings.DATABASE_URL)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Check if data already exists
        from sqlalchemy import select
        result = await session.execute(select(User).limit(1))
        if result.scalar_one_or_none():
            print("Data already exists, skipping seed.")
            return

        # Create users for each role
        users = [
            User(username="admin", email="admin@huihe.com", hashed_password=hash_password("Admin@2026"), full_name="系统管理员", role=UserRole.ADMIN, phone="13800000001"),
            User(username="pm1", email="pm1@huihe.com", hashed_password=hash_password("Pm@2026"), full_name="项目经理张三", role=UserRole.PM, phone="13800000002"),
            User(username="expert1", email="expert1@huihe.com", hashed_password=hash_password("Expert@2026"), full_name="影像专家李四", role=UserRole.EXPERT, phone="13800000003"),
            User(username="crc1", email="crc1@huihe.com", hashed_password=hash_password("Crc@2026"), full_name="CRC王五", role=UserRole.CRC, phone="13800000004"),
            User(username="cra1", email="cra1@huihe.com", hashed_password=hash_password("Cra@2026"), full_name="CRA赵六", role=UserRole.CRA, phone="13800000005"),
            User(username="dm1", email="dm1@huihe.com", hashed_password=hash_password("Dm@2026"), full_name="DM钱七", role=UserRole.DM, phone="13800000006"),
        ]
        session.add_all(users)
        await session.flush()

        # Create sample project
        project = Project(code="PRJ-2026-001", name="XX药物III期临床试验影像评估", description="多中心、随机、双盲、安慰剂对照的III期临床试验", status="active")
        session.add(project)
        await session.flush()

        # Assign users to project
        session.add_all([
            ProjectUser(user_id=users[1].id, project_id=project.id),  # PM
            ProjectUser(user_id=users[2].id, project_id=project.id),  # Expert
            ProjectUser(user_id=users[3].id, project_id=project.id),  # CRC
            ProjectUser(user_id=users[4].id, project_id=project.id),  # CRA
            ProjectUser(user_id=users[5].id, project_id=project.id),  # DM
        ])

        # Create centers
        centers = [
            Center(project_id=project.id, code="CTR-001", name="北京协和医院"),
            Center(project_id=project.id, code="CTR-002", name="上海瑞金医院"),
            Center(project_id=project.id, code="CTR-003", name="广州中山医院"),
        ]
        session.add_all(centers)
        await session.flush()

        # Create subjects
        subjects = []
        for i, center in enumerate(centers):
            for j in range(1, 4):  # 3 subjects per center
                subjects.append(Subject(
                    center_id=center.id,
                    project_id=project.id,
                    screening_number=f"S-{center.code[-3:]}-{j:03d}",
                ))
        session.add_all(subjects)

        await session.commit()

        print("Seed data created successfully!")
        print(f"  Users: {len(users)}")
        print(f"  Projects: 1")
        print(f"  Centers: {len(centers)}")
        print(f"  Subjects: {len(subjects)}")
        print()
        print("Login credentials:")
        print("  admin / Admin@2026")
        print("  pm1 / Pm@2026")
        print("  expert1 / Expert@2026")
        print("  crc1 / Crc@2026")
        print("  cra1 / Cra@2026")
        print("  dm1 / Dm@2026")


if __name__ == "__main__":
    asyncio.run(seed())
