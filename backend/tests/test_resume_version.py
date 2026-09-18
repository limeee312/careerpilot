"""Resume Version assembly and truth-boundary tests without a database."""

from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.resume_version import ResumeVersionCreate
from app.services.resume_version import (
    ResumeVersionInvalidDraftError,
    ResumeVersionSourceNotFoundError,
    create_resume_version,
)
from tests.test_resume_tailor import source_records, tailor_result


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def version_payload() -> ResumeVersionCreate:
    return ResumeVersionCreate(
        match_result_id=source_records()[1].id,
        draft=tailor_result().output,
        prompt_version="resume_tailor_v1",
        model="tailor-model",
    )


def source_match_result():
    job, result = source_records()
    result.job_snapshot = {
        **result.job_snapshot,
        "id": str(job.id),
        "company_name": job.company_name,
        "title": job.title,
        "raw_jd": job.raw_jd,
    }
    return job, result


@pytest.mark.anyio
async def test_explicit_save_revalidates_and_assembles_immutable_fields() -> None:
    job, result = source_match_result()
    session = AsyncMock(spec=AsyncSession)
    session.scalar.return_value = result
    payload = version_payload()
    payload.match_result_id = result.id

    version = await create_resume_version(session, job.user_id, payload)

    session.add.assert_called_once_with(version)
    session.commit.assert_awaited_once()
    assert version.status.value == "SAVED"
    assert version.name == "目标公司 - 产品运营"
    assert version.source_resume_snapshot == result.resume_snapshot
    assert version.source_job_snapshot == result.job_snapshot
    assert version.content["summary"] == "具备数据分析与流程优化实践。"
    assert version.content["experiences"][0]["organization"] == "示例科技"
    assert version.content["experiences"][0]["position"] == "产品运营实习生"
    assert version.content["experiences"][0]["bullets"] == [
        "梳理近三年业务需求及全流程耗时数据，定位流程异常并推动优化。"
    ]
    assert version.content["projects"][0]["name"] == "运营数据周报"
    assert version.content["skills"][0]["skill_name"] == "Python"


@pytest.mark.anyio
async def test_save_rejects_an_unsupported_number_after_manual_edit() -> None:
    job, result = source_match_result()
    session = AsyncMock(spec=AsyncSession)
    session.scalar.return_value = result
    payload = version_payload()
    payload.match_result_id = result.id
    payload.draft.experiences[0].bullets[0].text += "，效率提升30%。"

    with pytest.raises(ResumeVersionInvalidDraftError):
        await create_resume_version(session, job.user_id, payload)

    session.add.assert_not_called()
    session.commit.assert_not_awaited()


@pytest.mark.anyio
async def test_save_hides_missing_or_other_user_match_results() -> None:
    session = AsyncMock(spec=AsyncSession)
    session.scalar.return_value = None

    with pytest.raises(ResumeVersionSourceNotFoundError):
        await create_resume_version(
            session, source_records()[0].user_id, version_payload()
        )

    session.add.assert_not_called()
