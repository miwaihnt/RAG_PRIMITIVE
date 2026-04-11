import hashlib
import logging
from typing import Generator, List
from langchain_text_splitters import RecursiveCharacterTextSplitter

from rag_primitive.core.config import settings
from rag_primitive.schemas.speech import MeetingRecord, SpeechRecord
from rag_primitive.schemas.chunk import Chunk

logger = logging.getLogger(__name__)


class SpeechChunker:
    """
    国会会議録の発言データを、RAGに最適なサイズにチャンキングする。
    「Phase 2: Processing」の責任を負う。
    """

    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        # 設定ファイルからデフォルト値を取得（シニアの柔軟性よ！）
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP

        # 日本語に特化したセパレータの優先順位
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", "。", "、", " ", ""],
            add_start_index=True,
        )

    def generate_chunks(self, meeting: MeetingRecord) -> Generator[Chunk, None, None]:
        """
        1つの会議録（MeetingRecord）から全発言を抽出し、チャンク化して yield する。
        """
        for speech in meeting.speech_records:
            # 発言単位でチャンキング
            # LangChain の splitter は Document オブジェクト等を期待するが、ここではシンプルに文字列を渡すわ。
            texts = self.splitter.split_text(speech.speech)
            
            for i, text in enumerate(texts):
                # チャンク内容に基づいてユニークなID（MD5）を生成
                # issue_id + speech_id + content のハッシュ。
                # これにより、再実行時も同じデータなら同じ ID になる（べき等性）。
                hasher = hashlib.md5()
                hasher.update(f"{meeting.issue_id}{speech.speech_id}{text}".encode("utf-8"))
                chunk_id = hasher.hexdigest()

                yield Chunk(
                    chunk_id=chunk_id,
                    speech_id=speech.speech_id,
                    content=text,
                    chunk_index=i,
                    speaker=speech.speaker,
                    date=meeting.date,
                    meeting_name=meeting.name_of_meeting
                )

    def process_batch(self, meetings: List[MeetingRecord]) -> List[Chunk]:
        """
        複数の会議録をまとめてバッチ処理する。
        (将来的なスループット向上のためのインターフェース)
        """
        all_chunks = []
        for meeting in meetings:
            all_chunks.extend(list(self.generate_chunks(meeting)))
        return all_chunks
