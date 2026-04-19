import logging
from pathlib import Path
from typing import Optional

from rag_primitive.acquisition.api_client import NDLAPIClient
from rag_primitive.core.config import settings, setup_directories
from rag_primitive.schemas.speech import MeetingResponse

logger = logging.getLogger(__name__)


class NDLCrawler:
    """
    APIクライアントを用いてデータを取得し、ローカルのRaw Data Lakeに保存する。
    「Phase 1: Acquisition」の責任を負う。
    """

    def __init__(self):
        self.client = NDLAPIClient()
        setup_directories()

    async def save_meeting_to_jsonl(self, issue_id: str) -> Optional[Path]:
        """
        特定の会議IDを直接指定して取得し、保存する。
        """
        output_path = settings.RAW_DATA_DIR / f"{issue_id}.jsonl"

        if output_path.exists():
            logger.info(f"Data already exists: {output_path}. Skipping.")
            return output_path

        response = await self.client.fetch_meeting_by_id(issue_id)
        if not response:
            logger.error(f"Failed to fetch data for ID: {issue_id}")
            return None

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(response.model_dump_json(by_alias=True) + "\n")

        logger.info(f"Successfully saved: {output_path}")
        return output_path

    async def crawl_range(self, from_date: str, to_date: str):
        """
        特定の期間の会議データを全件取得し、1会議1ファイルで保存する。
        """
        logger.info(f"Starting crawl from {from_date} to {to_date}")
        
        count = 0
        async for record in self.client.stream_meetings(from_date, to_date):
            issue_id = record.issue_id
            output_path = settings.RAW_DATA_DIR / f"{issue_id}.jsonl"

            if output_path.exists():
                logger.info(f"Skipping existing record: {issue_id}")
                continue

            # 会議1件分のレスポンス形式をモックして保存
            mock_response = MeetingResponse(
                number_of_records=1,
                meeting_records=[record]
            )

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(mock_response.model_dump_json(by_alias=True) + "\n")
            
            count += 1
            logger.info(f"Saved meeting: {issue_id} (Total: {count})")

        logger.info(f"Crawl finished. Total new records saved: {count}")
