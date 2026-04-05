import json
import logging
from pathlib import Path
from typing import Optional

from rag_primitive.acquisition.api_client import NDLAPIClient
from rag_primitive.core.config import settings, setup_directories
from rag_primitive.schemas.speech import MeetingResponse

# rag_primitive.acquisition.crawler という階層名になる
logger = logging.getLogger(__name__)


class NDLCrawler:
    """
    APIクライアントを用いてデータを取得し、ローカルのRaw Data Lakeに保存する。
    「Phase 1: Acquisition」の責任を負う。
    """

    def __init__(self):
        self.client = NDLAPIClient()
        # 実行前にディレクトリがなければ作成する（シニアの気遣いよ！）
        setup_directories()

    async def save_meeting_to_jsonl(self, issue_id: str) -> Optional[Path]:
        """
        特定の会議IDを指定して取得し、data/raw/issue_id.jsonl に保存する。
        """
        # 保存先パスの決定
        output_path = settings.RAW_DATA_DIR / f"{issue_id}.jsonl"

        # すでに存在する場合はスキップ ( Idempotency / べき等性 )
        if output_path.exists():
            logger.info(f"Data already exists: [yellow]{output_path}[/yellow]. Skipping.")
            return output_path

        # データ取得
        # api_client.py 側の retry ロジックが効いているから、ここではシンプルに呼ぶだけ。
        response = await self.client.fetch_meeting_by_id(issue_id)
        if not response:
            logger.error(f"Failed to fetch data for ID: [bold red]{issue_id}[/bold red]")
            return None

        # JSONLとして書き込み
        # MeetingResponse を丸ごと1行のJSONにする。
        with open(output_path, "w", encoding="utf-8") as f:
            # model_dump_json() を使って Pydantic モデルを JSON 文字列に変換
            # by_alias=True を忘れちゃダメよ。APIのキー名（CamelCase）を尊重するの。
            f.write(response.model_dump_json(by_alias=True) + "\n")

        logger.info(f"Successfully saved data to: [bold green]{output_path}[/bold green]")
        return output_path

    async def crawl_range(self, from_date: str, to_date: str):
        """
        特定の期間の会議データを一括でクロールし、保存する。
        (1億件スケールのためのクロールロジックのプレースホルダー)
        """
        # TODO: 期間を指定してループを回し、全会議を JSONL 化する。
        pass
