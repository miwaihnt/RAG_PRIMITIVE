from typing import List, Optional
from pydantic import BaseModel, Field


class SpeechRecord(BaseModel):
    """
    国会会議録APIの「発言」単位のデータモデル。
    """
    speech_id: str = Field(..., alias="speechID", description="発言ID (例: 122104339X00320260312-1)")
    speech_order: int = Field(..., alias="speechOrder", description="発言番号")
    speaker: str = Field(..., description="発言者名")
    speaker_yomi: Optional[str] = Field(None, alias="speakerYomi", description="発言者よみ")
    speaker_group: Optional[str] = Field(None, alias="speakerGroup", description="発言者所属会派")
    speaker_position: Optional[str] = Field(None, alias="speakerPosition", description="発言者肩書き")
    speaker_role: Optional[str] = Field(None, alias="speakerRole", description="発言者役職")
    speech: str = Field(..., description="発言内容")

    class Config:
        populate_by_name = True


class MeetingRecord(BaseModel):
    """
    国会会議録APIの「会議」単位のデータモデル。
    """
    issue_id: str = Field(..., alias="issueID", description="会議録ID")
    image_kind: str = Field(..., alias="imageKind", description="イメージ種別")
    search_object: int = Field(..., alias="searchObject", description="検索対象")
    session: int = Field(..., description="国会回次")
    # house は nameOfHouse と被るし、API側で返ってきていないようなので一旦削除するか Optional に。
    # 生レスポンスでは nameOfHouse はあるが house はない。
    name_of_house: str = Field(..., alias="nameOfHouse", description="院名（正式名称）")
    name_of_meeting: str = Field(..., alias="nameOfMeeting", description="会議名")
    issue: str = Field(..., description="号数")
    date: str = Field(..., description="開催年月日 (YYYY-MM-DD)")
    closing: Optional[str] = Field(None, description="閉会中フラグ")
    speech_records: List[SpeechRecord] = Field(default_factory=list, alias="speechRecord", description="発言リスト")

    class Config:
        populate_by_name = True


class MeetingResponse(BaseModel):
    """
    国会会議録APIの「会議単位出力」全体のレスポンスモデル。
    """
    number_of_records: int = Field(..., alias="numberOfRecords", description="総件数")
    next_record_position: Optional[int] = Field(None, alias="nextRecordPosition", description="次開始位置")
    meeting_records: List[MeetingRecord] = Field(default_factory=list, alias="meetingRecord", description="会議リスト")

    class Config:
        populate_by_name = True
