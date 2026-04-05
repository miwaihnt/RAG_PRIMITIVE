import asyncio
import logging
from rag_primitive.core.config import settings
from rag_primitive.core.logging import setup_logging
from rag_primitive.acquisition.crawler import NDLCrawler

# ロガーの取得
logger = logging.getLogger("rag_primitive.main")


async def main():
    # 1. 共通セットアップ (ロギングの初期化)
    setup_logging()
    logger.info("[bold blue]--- RAG Primitive Pipeline: Phase 1 (Acquisition) ---[/bold blue]")

    # 2. クローラーの初期化
    crawler = NDLCrawler()

    # 3. ターゲット会議IDの取得実行
    # 設定ファイルから会議IDを取得 (122104339X00320260312)
    target_id = settings.TARGET_ISSUE_ID
    
    logger.info(f"Targeting Meeting ID: [cyan]{target_id}[/cyan]")
    
    # 非同期で実行！
    path = await crawler.save_meeting_to_jsonl(target_id)
    
    if path:
        logger.info(f"[bold green]Acquisition Phase Complete![/bold green] Data saved to {path}")
    else:
        logger.error("[bold red]Acquisition Phase Failed.[/bold red]")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("Pipeline interrupted by user.")
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
