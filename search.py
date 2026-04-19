import asyncio
import logging
import sys
import time
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from rag_primitive.core.logging import setup_logging
from rag_primitive.embedding.model import SpeechEmbedder
from rag_primitive.storage.lancedb_client import LanceDBClient

# コンソールの初期化
console = Console()
logger = logging.getLogger("rag_primitive.search")


async def perform_search(query_text: str, top_k: int = 3):
    """
    ユーザーの質問に対してベクトル検索を実行する。
    """
    # 1. 準備 (Embedder と DB Client)
    embedder = SpeechEmbedder()
    client = LanceDBClient()

    # 2. クエリのベクトル化 (is_query=True を忘れずに！)
    console.print(f"\n[bold yellow]Query:[/bold yellow] {query_text}")
    with console.status("[bold green]Vectorizing query...[/bold green]"):
        # torch.Tensor -> numpy -> list に変換
        # encode_single は (1, dimension) のテンソルを返すので、最初の1件を取るわ
        embeddings_tensor = embedder.encode_single(query_text, is_query=True)
        query_vector = embeddings_tensor.cpu().numpy().tolist()[0]

    # 3. LanceDB で検索
    with console.status("[bold green]Searching in LanceDB...[/bold green]"):
        results = client.search(query_vector, limit=top_k)

    # 4. 結果の表示
    if not results:
        console.print("[bold red]No results found.[/bold red]")
        return

    console.print(f"\n[bold cyan]Found {len(results)} relevant chunks:[/bold cyan]\n")
    
    for i, res in enumerate(results):
        # 距離（スコア）の取得
        score = res.get("_distance", 0.0)
        
        # メタデータ用のテーブルを作成
        # Panel の中に Table を入れる時は、box の設定に気をつけなさい！
        meta_table = Table(show_header=False, box=box.SIMPLE_HEAD, padding=(0, 1))
        meta_table.add_row("[bold magenta]Speaker:[/bold magenta]", res['speaker'])
        meta_table.add_row("[bold magenta]Date:[/bold magenta]", res['date'])
        meta_table.add_row("[bold magenta]Meeting:[/bold magenta]", res['meeting_name'])
        meta_table.add_row("[bold magenta]Distance:[/bold magenta]", f"{score:.4f}")

        # 結果をパネルで表示
        # content をメインにして、メタデータをテーブルで添えるのよ
        console.print(Panel(
            f"{res['content']}",
            title=f"[bold green]Result #{i+1}[/bold green]",
            expand=False,
            border_style="cyan"
        ))
        console.print(meta_table)
        console.print("-" * 40)


async def main():
    setup_logging()
    
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = console.input("[bold yellow]Enter your question about the Diet proceedings:[/bold yellow] ")

    if not query.strip():
        console.print("[red]Query cannot be empty![/red]")
        return

    await perform_search(query)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Search interrupted.[/yellow]")
    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}")
