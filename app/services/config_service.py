"""配置服务 -- 管理 API 配置和数据导入导出。"""

from __future__ import annotations

from app.database import AppDatabase
from app.services.base import BaseService
from app.utils.events import DataExportedEvent, DataImportedEvent, DataResetEvent


class ConfigService(BaseService):
    """配置与数据管理服务。"""

    def __init__(self, db: AppDatabase) -> None:
        super().__init__(db)

    # ── API Config ─────────────────────────────────────────────────────────

    def save_api_config(self, host: str, api_key: str, model: str) -> None:
        """保存 API 配置。"""
        self._db.save_api_config(host, api_key, model)

    def load_api_config(self) -> tuple[str, str, str]:
        """加载 API 配置。"""
        return self._db.load_api_config()

    # ── Data lifecycle ─────────────────────────────────────────────────────

    def reset_all(self) -> None:
        """重置所有学习数据。"""
        self._db.reset_learning_progress()
        self._publish(DataResetEvent())

    def export_json(self) -> dict:
        """导出数据为 JSON 字典。"""
        data = self._db.export_progress_json()
        self._publish(DataExportedEvent(format="json"))
        return data

    def import_json(self, data: dict) -> int:
        """从 JSON 导入数据。

        Returns:
            导入的记录总数。
        """
        count = self._db.import_progress_json(data)
        self._publish(DataImportedEvent(record_count=count))
        return count
