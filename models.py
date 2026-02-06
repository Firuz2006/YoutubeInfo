from pydantic import BaseModel


class ChannelInfo(BaseModel):
    channel_id: str
    name: str
    url: str
    subscriber_count: int | None = None
    total_views: int | None = None
    video_count: int | None = None
    avg_views: int | None = None
    recent_video_titles: list[str] = []


class AnalysisResult(BaseModel):
    channel_id: str
    niche: str
    why_partner_fit: str


class ChannelReport(BaseModel):
    channel: ChannelInfo
    analysis: AnalysisResult | None = None
