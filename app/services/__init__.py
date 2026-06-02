"""服务层 -- 抽象数据库调用，提供可测试的服务接口。

此包将 AppDatabase 的直接调用封装为面向业务的服务接口，
使 widget 不再直接依赖数据库实现细节。
"""

from app.services.achievement_service import AchievementService
from app.services.base import BaseService
from app.services.bookmark_service import BookmarkService
from app.services.config_service import ConfigService
from app.services.lesson_service import LessonService
from app.services.mentor_service import MentorService
from app.services.note_service import NoteService
from app.services.practice_data_service import PracticeDataService
from app.services.review_service import ReviewService

__all__ = [
    "BaseService",
    "AchievementService",
    "BookmarkService",
    "ConfigService",
    "LessonService",
    "MentorService",
    "NoteService",
    "PracticeDataService",
    "ReviewService",
]
