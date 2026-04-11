import logging
import torch
from typing import List, Union
from sentence_transformers import SentenceTransformer

from rag_primitive.core.config import settings

logger = logging.getLogger(__name__)


class SpeechEmbedder:
    """
    チャンク化されたテキストをベクトル（Embedding）に変換する。
    「Phase 2: Processing」の推論部分を担う。
    """

    def __init__(self, model_name: str = None):
        # 1. デバイスの自動選択 (MPS, CUDA, CPU)
        if torch.backends.mps.is_available():
            self.device = "mps"
        elif torch.cuda.is_available():
            self.device = "cuda"
        else:
            self.device = "cpu"
        
        logger.info(f"Initializing embedder on device: [bold cyan]{self.device}[/bold cyan]")

        # 2. モデルのロード (HuggingFace から自動ダウンロード)
        self.model_name = model_name or settings.EMBEDDING_MODEL_NAME
        self.model = SentenceTransformer(self.model_name, device=self.device)
        
        # 3. モデルの次元数を確認 (E5-small なら 384)
        self.dimension = self.model.get_sentence_embedding_dimension()
        logger.info(f"Model loaded: {self.model_name} (Dimension: {self.dimension})")

    def encode(self, texts: List[str], is_query: bool = False) -> torch.Tensor:
        """
        テキストのリストをベクトルに変換する。
        multilingual-e5 の特性に合わせ、自動的に prefix (query:/passage:) を付与する。
        """
        # Prefix の付与 (E5 独自の掟よ！)
        prefix = "query: " if is_query else "passage: "
        prefixed_texts = [f"{prefix}{t}" for t in texts]

        # 推論実行 (torch tensor で返す)
        # convert_to_tensor=True にすることで、後続の LanceDB (Arrow) への変換を効率化する
        with torch.no_grad():
            embeddings = self.model.encode(
                prefixed_texts, 
                batch_size=settings.BATCH_SIZE,
                show_progress_bar=False,
                convert_to_tensor=True,
                device=self.device
            )
        
        return embeddings

    def encode_single(self, text: str, is_query: bool = False) -> torch.Tensor:
        """1つのテキストをベクトル化する。"""
        return self.encode([text], is_query=is_query)
