import httpx
import logging
from typing import Optional, AsyncGenerator
from tenacity import retry, stop_after_attempt, wait_exponential

from rag_primitive.core.config import settings
from rag_primitive.schemas.speech import MeetingResponse, MeetingRecord

logger = logging.getLogger(__name__)


class NDLAPIClient:
    """
    国会会議録検索システムAPIクライアント。
    「会議単位出力」に特化した実装。
    """

    def __init__(self):
        self.base_url = settings.NDL_API_BASE_URL

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def fetch_meeting_by_id(self, issue_id: str) -> Optional[MeetingResponse]:
        """
        特定の会議録ID (issueID) を指定して会議データを取得する。
        """
        params = {
            "issueID": issue_id,
            "recordPacking": "json",
        }

        async with httpx.AsyncClient() as client:
            logger.info(f"Fetching meeting data: {issue_id}")
            response = await client.get(self.base_url, params=params, timeout=30.0)
            
            if response.status_code == 404:
                logger.warning(f"Meeting not found: {issue_id}")
                return None
            
            response.raise_for_status()
            data = response.json()
            return MeetingResponse.model_validate(data)

    async def fetch_meetings_by_range(
        self, from_date: str, to_date: str, start_record: int, max_records: int
    ) -> Optional[MeetingResponse]:
        """
        期間を指定して会議データを取得する（1ページ分）。
        """
        params = {
            "from": from_date,
            "until": to_date,
            "startRecord": start_record,
            "maximumRecord": max_records,
            "recordPacking": "json",
        }

        async with httpx.AsyncClient() as client:
            logger.info(f"Fetching meetings from {from_date} to {to_date} (start: {start_record})")
            response = await client.get(self.base_url, params=params, timeout=30.0)
            
            if response.status_code == 404:
                return None
                
            response.raise_for_status()
            return MeetingResponse.model_validate(response.json())

    async def stream_meetings(
        self, from_date: str, to_date: str, max_records_per_request: int = 10
    ) -> AsyncGenerator[MeetingRecord, None]:
        """
        期間内の会議データを1件ずつ流す非同期ジェネレータ。
        ページネーション（次ページの取得）を自動で繰り返す。
        """
        start_record = 1
        
        while True:
            response = await self.fetch_meetings_by_range(
                from_date, to_date, start_record, max_records_per_request
            )
            
            if not response or not response.meeting_records:
                logger.info("No more records found.")
                break
            
            for record in response.meeting_records:
                yield record
            
            if response.next_record_position is None:
                logger.info("Reached the last page.")
                break
            
            start_record = response.next_record_position
