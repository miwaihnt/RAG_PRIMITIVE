import logging
import sys
from rich.logging import RichHandler


def setup_logging(level: str = "INFO"):
    """
    プロジェクト全体のロギング設定を初期化する。
    Rich を使用して、コンソール出力を視覚的に分かりやすくする。
    """
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, markup=True)]
    )

    # 外部ライブラリのログがうるさい場合はここで調整
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("torch").setLevel(logging.WARNING)

    logger = logging.getLogger("rag_primitive")
    logger.info("Logging setup complete. [bold green]Ready to RAG![/bold green]")
