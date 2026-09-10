"""Resume API lifecycle and ownership tests against CI PostgreSQL."""

import os
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from app.database import AsyncSessionFactory
from app.main import app
from app.models.user import User

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.skipif(
        os.getenv("RUN_DB_TESTS") != "1",
        reason="requires an isolated migrated PostgreSQL database",
    ),
]

PASSWORD = "correct horse battery staple"


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


async def register_and_login(client: AsyncClient, email: str) -> None:
    register_response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD},
    )
    assert register_response.status_code == 201
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert login_response.status_code == 200


def initial_resume() -> dict:
    return {
        "basic_info": {
            "name": "张三",
            "phone": "13800000000",
            "email": "resume-contact@example.com",
            "city": "杭州",
            "job_status": "求职中",
            "summary": "产品运营方向",
        },
        "education": [
            {
                "school": "XX大学",
                "degree": "硕士",
                "major": "应用语言学",
                "start_date": "2024-09",
                "end_date": "2027-06",
            }
        ],
        "experiences": [
            {
                "experience_type": "INTERNSHIP",
                "organization": "示例公司",
                "position": "产品运营实习生",
                "start_date": "2026-01",
                "is_current": True,
                "description": "分析用户反馈并推动流程优化。",
            }
        ],
        "projects": [
            {
                "name": "数据周报",
                "role": "产品负责人",
                "start_date": "2026-03",
                "end_date": "2026-05",
                "description": "设计数据周报 PRD 并推进研发评审。",
            }
        ],
        "skills": [
            {"skill_name": "Python", "skill_category": "数据分析"},
            {"skill_name": "Excel", "skill_category": "数据分析"},
        ],
    }


async def test_resume_upsert_preserves_ids_and_blocks_cross_user_sections() -> None:
    first_email = f"resume-api-a-{uuid4().hex}@example.com"
    second_email = f"resume-api-b-{uuid4().hex}@example.com"

    try:
        async with (
            AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as first_client,
            AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as second_client,
        ):
            await register_and_login(first_client, first_email)
            await register_and_login(second_client, second_email)

            empty_response = await first_client.get("/api/v1/resume/master")
            assert empty_response.status_code == 200
            assert empty_response.json() == {"data": None}

            create_response = await first_client.put(
                "/api/v1/resume/master",
                json=initial_resume(),
            )
            assert create_response.status_code == 200
            created = create_response.json()["data"]
            assert created["basic_info"]["email"] == "resume-contact@example.com"
            assert created["education"][0]["start_date"] == "2024-09"
            assert created["experiences"][0]["end_date"] is None
            education_id = created["education"][0]["id"]
            experience_id = created["experiences"][0]["id"]
            python_id = created["skills"][0]["id"]

            update_payload = initial_resume()
            update_payload["basic_info"]["summary"] = "产品与用户运营方向"
            update_payload["education"][0]["id"] = education_id
            update_payload["education"][0]["description"] = "研究语用与韵律。"
            update_payload["experiences"][0]["id"] = experience_id
            update_payload["projects"] = []
            update_payload["skills"] = [
                {"skill_name": "SQL"},
                {"id": python_id, "skill_name": "Python"},
            ]
            update_response = await first_client.put(
                "/api/v1/resume/master",
                json=update_payload,
            )
            assert update_response.status_code == 200
            updated = update_response.json()["data"]
            assert updated["education"][0]["id"] == education_id
            assert updated["experiences"][0]["id"] == experience_id
            assert updated["projects"] == []
            assert [item["skill_name"] for item in updated["skills"]] == [
                "SQL",
                "Python",
            ]
            assert updated["skills"][1]["id"] == python_id

            second_resume = initial_resume()
            second_resume["education"][0]["school"] = "另一所大学"
            second_create = await second_client.put(
                "/api/v1/resume/master",
                json=second_resume,
            )
            assert second_create.status_code == 200
            foreign_education_id = second_create.json()["data"]["education"][0]["id"]

            invalid_update = update_payload
            invalid_update["basic_info"]["summary"] = "不应被保存"
            invalid_update["education"][0]["id"] = foreign_education_id
            forbidden_response = await first_client.put(
                "/api/v1/resume/master",
                json=invalid_update,
            )
            assert forbidden_response.status_code == 404
            assert (
                forbidden_response.json()["error"]["code"] == "RESUME_SECTION_NOT_FOUND"
            )

            first_after_failure = await first_client.get("/api/v1/resume/master")
            assert first_after_failure.status_code == 200
            assert (
                first_after_failure.json()["data"]["basic_info"]["summary"]
                == "产品与用户运营方向"
            )
            second_after_attempt = await second_client.get("/api/v1/resume/master")
            assert second_after_attempt.status_code == 200
            assert (
                second_after_attempt.json()["data"]["education"][0]["school"]
                == "另一所大学"
            )
    finally:
        async with AsyncSessionFactory() as session:
            await session.execute(
                delete(User).where(User.email.in_([first_email, second_email]))
            )
            await session.commit()
