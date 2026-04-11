from typing import Optional
from pydantic import BaseModel, Field


class Chunk(BaseModel):
    """
    チャンキングされた後の1単位を表現するスキーマ。
    RAGの検索対象（ベクトル化対象）となる最小単位。
    """
    chunk_id: str = Field(..., description="Content-based ID (MD5 hash)")
    speech_id: str = Field(..., description="元となる発言ID")
    content: str = Field(..., description="チャンク化されたテキスト本体")
    chunk_index: int = Field(..., description="発言内でのチャンクの順番")
    
    # 検索結果に「誰がいつ話したか」を出すためにメタデータを非正規化して保持する
    speaker: str = Field(..., description="発言者名")
    date: str = Field(..., description="開催日 (YYYY-MM-DD)")
    meeting_name: str = Field(..., description="会議名")

    class Config:
        populate_by_name = True
