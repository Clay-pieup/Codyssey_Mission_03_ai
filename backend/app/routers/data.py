"""
데이터 API 창구: 추가 / 목록 / 수정 / 삭제.

창구는 ① 입력을 받아(검증은 스키마가) ② 서비스 함수에 넘기고 ③ 서비스의 예외를 HTTP 상태 코드로 바꾼다.
"""
import datetime as dt

from fastapi import APIRouter, HTTPException, Query, Response

from app.schemas.data import DataIn, DataOut, GroupName
from app.schemas.summary import DataSummary
from app.services import data_service, summary_service
from app.services.data_service import DataNotFoundError, DuplicateDataError

router = APIRouter(prefix="/api/data", tags=["data"])


@router.post("", response_model=DataOut, status_code=201, summary="새 데이터 추가")
def create_data(item: DataIn):
    try:
        return data_service.create_data(item)
    except DuplicateDataError as error:
        raise HTTPException(status_code=409, detail=str(error))


@router.get("", response_model=list[DataOut], summary="데이터 목록 조회(최신 날짜순)")
def list_data(
    memo: GroupName | None = Query(None, description="그룹으로 거르기"),
    date_from: dt.date | None = Query(None, description="이 날짜 이후(포함)"),
    date_to: dt.date | None = Query(None, description="이 날짜 이전(포함)"),
    limit: int = Query(50, ge=1, le=500, description="최대 건수(1~500)"),
):
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=422, detail="date_from이 date_to보다 늦습니다.")
    return data_service.list_data(memo, date_from, date_to, limit)


@router.get("/summary", response_model=DataSummary, summary="데이터 요약(AI 프롬프트 주입용)")
def get_summary():
    """전체 + 6그룹의 기간·개수·합계·평균·최대·최소·추세. 서버가 최대 1시간 기억하고, 데이터가 바뀌면 다시 계산한다."""
    return summary_service.get_summary()


@router.put("/{data_id}", response_model=DataOut, summary="데이터 수정(통째로 교체)")
def update_data(data_id: str, item: DataIn):
    try:
        return data_service.update_data(data_id, item)
    except DataNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error))
    except DuplicateDataError as error:
        raise HTTPException(status_code=409, detail=str(error))


@router.delete("/{data_id}", status_code=204, summary="데이터 삭제")
def delete_data(data_id: str):
    try:
        data_service.delete_data(data_id)
    except DataNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error))
    return Response(status_code=204)   # 성공: 돌려줄 내용 없음
