from typing import List, Dict, Any
from pydantic import BaseModel


class SystemStatsResponse(BaseModel):
    total_users: int
    total_apps: int
    total_downloads: int
    active_sessions: int


class DownloadStatItem(BaseModel):
    date: str
    count: int


class CategoryDownloadStat(BaseModel):
    category_name: str
    count: int


class DashboardAnalyticsResponse(BaseModel):
    system_stats: SystemStatsResponse
    download_history: List[DownloadStatItem]
    category_distribution: List[CategoryDownloadStat]
    popular_apps: List[Dict[str, Any]]
