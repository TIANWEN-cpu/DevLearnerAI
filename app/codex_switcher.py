import base64
import ctypes
import json
import os
import subprocess
import sys
import uuid
from ctypes import wintypes
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


APP_TITLE = "Codex 一键切号器"
FONT_FAMILY = "Microsoft YaHei UI"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

CODEX_DIR = Path.home() / ".codex"
AUTH_PATH = CODEX_DIR / "auth.json"
CAP_SID_PATH = CODEX_DIR / "cap_sid"


def _app_data_root() -> Path:
    appdata = os.getenv("APPDATA") or os.getenv("LOCALAPPDATA")
    if appdata:
        return Path(appdata) / "CodexAccountSwitcher"
    return Path.home() / ".codex-account-switcher"


DATA_DIR = _app_data_root()
STORE_PATH = DATA_DIR / "profiles.json"

DEFAULT_STYLE = """
QMainWindow {
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 1,
        stop: 0 #eef6ff,
        stop: 0.55 #f9fbff,
        stop: 1 #fff9f0
    );
}
QWidget {
    font-family: "Microsoft YaHei UI";
    color: #17324d;
    font-size: 14px;
}
QFrame[card="true"] {
    background: rgba(255, 255, 255, 0.94);
    border: 1px solid rgba(32, 86, 151, 0.12);
    border-radius: 20px;
}
QLabel[title="true"] {
    font-size: 28px;
    font-weight: 700;
    color: #123154;
}
QLabel[muted="true"] {
    color: #60758f;
}
QListWidget {
    background: #ffffff;
    border: 1px solid rgba(32, 86, 151, 0.12);
    border-radius: 16px;
    padding: 10px;
}
QListWidget::item {
    border-radius: 12px;
    padding: 12px;
    margin: 4px 0;
}
QListWidget::item:selected {
    background: #dbeafe;
    color: #0f3f77;
}
QPushButton {
    background: #2563eb;
    color: white;
    border: none;
    border-radius: 14px;
    padding: 10px 18px;
    min-height: 42px;
    font-weight: 600;
}
QPushButton:hover {
    background: #1d4ed8;
}
QPushButton[variant="secondary"] {
    background: #ffffff;
    color: #17324d;
    border: 1px solid rgba(32, 86, 151, 0.16);
}
QPushButton[variant="danger"] {
    background: #dc2626;
}
"""


class DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_byte)),
    ]


crypt32 = ctypes.windll.crypt32
kernel32 = ctypes.windll.kernel32

CRYPTPROTECT_UI_FORBIDDEN = 0x01


def _blob_from_bytes(raw: bytes) -> DATA_BLOB:
    if not raw:
        return DATA_BLOB(0, None)
    buffer = (ctypes.c_byte * len(raw)).from_buffer_copy(raw)
    return DATA_BLOB(len(raw), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte)))


def _bytes_from_blob(blob: DATA_BLOB) -> bytes:
    if not blob.cbData:
        return b""
    return ctypes.string_at(blob.pbData, blob.cbData)


def protect_text(value: str) -> str:
    raw = value.encode("utf-8")
    in_blob = _blob_from_bytes(raw)
    out_blob = DATA_BLOB()
    success = crypt32.CryptProtectData(
        ctypes.byref(in_blob),
        "CodexAccountSwitcher",
        None,
        None,
        None,
        CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(out_blob),
    )
    if not success:
        raise ctypes.WinError()
    try:
        protected = _bytes_from_blob(out_blob)
    finally:
        kernel32.LocalFree(out_blob.pbData)
    return base64.b64encode(protected).decode("ascii")


def unprotect_text(value: str) -> str:
    raw = base64.b64decode(value.encode("ascii"))
    in_blob = _blob_from_bytes(raw)
    out_blob = DATA_BLOB()
    success = crypt32.CryptUnprotectData(
        ctypes.byref(in_blob),
        None,
        None,
        None,
        None,
        CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(out_blob),
    )
    if not success:
        raise ctypes.WinError()
    try:
        decrypted = _bytes_from_blob(out_blob)
    finally:
        kernel32.LocalFree(out_blob.pbData)
    return decrypted.decode("utf-8")


def now_text() -> str:
    return datetime.now().strftime(DATE_FORMAT)


def decode_jwt_payload(token: str) -> Dict[str, str]:
    parts = token.split(".")
    if len(parts) < 2:
        return {}
    payload = parts[1]
    payload += "=" * (-len(payload) % 4)
    try:
        raw = base64.urlsafe_b64decode(payload.encode("ascii"))
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return {}


@dataclass
class ActiveAccount:
    name: str
    email: str
    account_id: str
    auth_text: str
    cap_sid_text: str

    @property
    def label(self) -> str:
        if self.name and self.email:
            return f"{self.name} ({self.email})"
        return self.email or self.name or self.account_id or "未识别账号"


class ProfileStore:
    def __init__(self, store_path: Path):
        self.store_path = store_path
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.store_path.exists():
            self.save({"version": 1, "profiles": []})

    def load(self) -> Dict[str, object]:
        try:
            with self.store_path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except FileNotFoundError:
            data = {"version": 1, "profiles": []}
        if "profiles" not in data or not isinstance(data["profiles"], list):
            data["profiles"] = []
        return data

    def save(self, data: Dict[str, object]) -> None:
        with self.store_path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)

    def profiles(self) -> List[Dict[str, object]]:
        return self.load()["profiles"]

    def upsert(self, profile: Dict[str, object]) -> None:
        data = self.load()
        profiles = data["profiles"]
        for index, existing in enumerate(profiles):
            if existing.get("id") == profile["id"]:
                profiles[index] = profile
                break
        else:
            profiles.append(profile)
        profiles.sort(key=lambda item: str(item.get("updated_at", "")), reverse=True)
        self.save(data)

    def delete(self, profile_id: str) -> None:
        data = self.load()
        data["profiles"] = [
            profile for profile in data["profiles"] if profile.get("id") != profile_id
        ]
        self.save(data)

    def find_by_account(self, account_id: str) -> Optional[Dict[str, object]]:
        if not account_id:
            return None
        for profile in self.profiles():
            if profile.get("account_id") == account_id:
                return profile
        return None

    def by_id(self, profile_id: str) -> Optional[Dict[str, object]]:
        for profile in self.profiles():
            if profile.get("id") == profile_id:
                return profile
        return None


class CodexAccountService:
    def __init__(self):
        self.store = ProfileStore(STORE_PATH)

    def get_active_account(self) -> Optional[ActiveAccount]:
        if not AUTH_PATH.exists():
            return None
        auth_text = AUTH_PATH.read_text(encoding="utf-8")
        cap_sid_text = CAP_SID_PATH.read_text(encoding="utf-8") if CAP_SID_PATH.exists() else ""
        auth_data = json.loads(auth_text)
        payload = decode_jwt_payload(auth_data.get("tokens", {}).get("id_token", ""))
        return ActiveAccount(
            name=str(payload.get("name", "")).strip(),
            email=str(payload.get("email", "")).strip(),
            account_id=str(auth_data.get("tokens", {}).get("account_id", "")).strip()
            or str(payload.get("sub", "")).strip(),
            auth_text=auth_text,
            cap_sid_text=cap_sid_text,
        )

    def build_profile_payload(self, alias: str, active: ActiveAccount) -> Dict[str, object]:
        existing = self.store.find_by_account(active.account_id)
        profile_id = existing["id"] if existing else str(uuid.uuid4())
        created_at = existing.get("created_at", now_text()) if existing else now_text()
        return {
            "id": profile_id,
            "alias": alias,
            "name": active.name,
            "email": active.email,
            "account_id": active.account_id,
            "created_at": created_at,
            "updated_at": now_text(),
            "auth_blob": protect_text(active.auth_text),
            "cap_sid_blob": protect_text(active.cap_sid_text),
        }

    def save_current_as_profile(self, alias: str) -> Dict[str, object]:
        active = self.get_active_account()
        if not active:
            raise RuntimeError("没有检测到当前 Codex 登录信息，请先登录一个账号。")
        profile = self.build_profile_payload(alias, active)
        self.store.upsert(profile)
        return profile

    def ensure_unsaved_active_snapshot(self, target_profile_id: str) -> None:
        active = self.get_active_account()
        if not active or not active.account_id:
            return
        existing = self.store.find_by_account(active.account_id)
        if existing and existing.get("id") == target_profile_id:
            return
        if existing:
            return
        alias = f"自动备份 {active.email or active.name or active.account_id} {datetime.now().strftime('%m-%d %H:%M')}"
        profile = self.build_profile_payload(alias, active)
        self.store.upsert(profile)

    def restore_profile(self, profile_id: str) -> Dict[str, object]:
        profile = self.store.by_id(profile_id)
        if not profile:
            raise RuntimeError("找不到选中的账号档案。")
        CODEX_DIR.mkdir(parents=True, exist_ok=True)
        auth_text = unprotect_text(str(profile["auth_blob"]))
        cap_sid_text = unprotect_text(str(profile["cap_sid_blob"]))
        AUTH_PATH.write_text(auth_text, encoding="utf-8")
        CAP_SID_PATH.write_text(cap_sid_text, encoding="utf-8")
        return profile

    def list_profiles(self) -> List[Dict[str, object]]:
        return self.store.profiles()

    def delete_profile(self, profile_id: str) -> None:
        self.store.delete(profile_id)

    def stop_codex(self) -> None:
        for image_name in ("Codex.exe", "codex.exe"):
            subprocess.run(
                ["taskkill", "/IM", image_name, "/F"],
                capture_output=True,
                text=True,
                check=False,
            )

    def locate_codex_app_id(self) -> Optional[str]:
        script = (
            "Get-StartApps | Where-Object { $_.Name -eq 'Codex' } | "
            "Select-Object -First 1 -ExpandProperty AppID"
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
            check=False,
            encoding="utf-8",
        )
        app_id = (result.stdout or "").strip()
        return app_id or None

    def start_codex(self) -> bool:
        app_id = self.locate_codex_app_id()
        if app_id:
            target = f"shell:AppsFolder\\{app_id}"
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", f'Start-Process "{target}"'],
                capture_output=True,
                text=True,
                check=False,
                encoding="utf-8",
            )
            if result.returncode == 0:
                return True

        fallback_paths = [
            Path(os.getenv("LOCALAPPDATA", "")) / "Programs" / "Codex" / "Codex.exe",
            Path(
                r"C:\Program Files\WindowsApps\OpenAI.Codex_26.325.3894.0_x64__2p2nqsd0c76g0\app\Codex.exe"
            ),
        ]
        for candidate in fallback_paths:
            if candidate.exists():
                try:
                    subprocess.Popen([str(candidate)])
                    return True
                except Exception:
                    continue
        return False


class ProfileListItem(QListWidgetItem):
    def __init__(self, profile: Dict[str, object]):
        alias = str(profile.get("alias", "未命名账号"))
        email = str(profile.get("email", ""))
        updated_at = str(profile.get("updated_at", ""))
        detail = email or str(profile.get("name", "")) or str(profile.get("account_id", ""))
        text = f"{alias}\n{detail}\n最近保存：{updated_at}"
        super().__init__(text)
        self.profile_id = str(profile.get("id", ""))
        self.setData(Qt.UserRole, self.profile_id)


class CodexSwitcherWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.service = CodexAccountService()
        self.setWindowTitle(APP_TITLE)
        self.setMinimumSize(1080, 720)
        self.resize(1220, 790)
        self.setStyleSheet(DEFAULT_STYLE)
        self._build_ui()
        self.refresh_all()

    def _build_ui(self) -> None:
        root = QWidget()
        outer = QHBoxLayout(root)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(20)

        outer.addWidget(self._build_left_panel(), 1)
        outer.addWidget(self._build_right_panel(), 1)
        self.setCentralWidget(root)

    def _build_left_panel(self) -> QFrame:
        card = QFrame()
        card.setProperty("card", True)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(14)

        title = QLabel("已保存账号")
        title.setProperty("title", True)
        layout.addWidget(title)

        desc = QLabel("先在 Codex 里登录目标账号，再点“保存当前账号”；以后就可以直接一键切换。")
        desc.setProperty("muted", True)
        desc.setWordWrap(True)
        layout.addWidget(desc)

        self.profile_count_label = QLabel("")
        self.profile_count_label.setProperty("muted", True)
        layout.addWidget(self.profile_count_label)

        self.profile_list = QListWidget()
        self.profile_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.profile_list.itemSelectionChanged.connect(self.update_selected_profile_summary)
        layout.addWidget(self.profile_list, 1)

        button_row = QHBoxLayout()
        button_row.setSpacing(10)

        self.refresh_button = QPushButton("刷新")
        self.refresh_button.setProperty("variant", "secondary")
        self.refresh_button.clicked.connect(self.refresh_all)
        button_row.addWidget(self.refresh_button)

        self.delete_button = QPushButton("删除档案")
        self.delete_button.setProperty("variant", "danger")
        self.delete_button.clicked.connect(self.delete_selected_profile)
        button_row.addWidget(self.delete_button)

        layout.addLayout(button_row)
        return card

    def _build_right_panel(self) -> QFrame:
        card = QFrame()
        card.setProperty("card", True)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(16)

        header = QLabel("当前状态")
        header.setProperty("title", True)
        layout.addWidget(header)

        self.active_account_label = QLabel("")
        self.active_account_label.setFont(QFont(FONT_FAMILY, 12))
        self.active_account_label.setWordWrap(True)
        layout.addWidget(self.active_account_label)

        self.selected_profile_label = QLabel("")
        self.selected_profile_label.setProperty("muted", True)
        self.selected_profile_label.setWordWrap(True)
        layout.addWidget(self.selected_profile_label)

        tip_box = QLabel(
            "使用建议：\n"
            "1. 先在 Codex 官方客户端里登录一个账号。\n"
            "2. 回到这里点击“保存当前账号”。\n"
            "3. 以后选中任意档案，点“一键切换”即可。"
        )
        tip_box.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        tip_box.setWordWrap(True)
        tip_box.setStyleSheet(
            "background:#f7fbff;border:1px solid rgba(32,86,151,0.10);"
            "border-radius:16px;padding:16px;color:#4d6580;"
        )
        layout.addWidget(tip_box)

        self.save_current_button = QPushButton("保存当前账号")
        self.save_current_button.clicked.connect(self.save_current_profile)
        layout.addWidget(self.save_current_button)

        self.switch_button = QPushButton("一键切换到所选账号")
        self.switch_button.clicked.connect(self.switch_selected_profile)
        layout.addWidget(self.switch_button)

        self.relaunch_button = QPushButton("仅重新打开 Codex")
        self.relaunch_button.setProperty("variant", "secondary")
        self.relaunch_button.clicked.connect(self.relaunch_codex)
        layout.addWidget(self.relaunch_button)

        layout.addStretch()
        return card

    def refresh_all(self) -> None:
        self.refresh_active_account()
        self.refresh_profile_list()
        self.update_selected_profile_summary()

    def refresh_active_account(self) -> None:
        try:
            active = self.service.get_active_account()
        except Exception as exc:
            self.active_account_label.setText(f"读取当前登录信息失败：{exc}")
            return

        if not active:
            self.active_account_label.setText("当前没有检测到 `.codex/auth.json`，请先打开 Codex 登录账号。")
            return

        lines = [
            f"当前账号：{active.label}",
            f"账号 ID：{active.account_id or '未识别'}",
            f"认证文件：{AUTH_PATH}",
        ]
        self.active_account_label.setText("\n".join(lines))

    def refresh_profile_list(self) -> None:
        selected_id = self.selected_profile_id()
        self.profile_list.clear()
        profiles = self.service.list_profiles()
        self.profile_count_label.setText(f"已保存 {len(profiles)} 个账号档案")
        selected_row = -1
        for index, profile in enumerate(profiles):
            item = ProfileListItem(profile)
            self.profile_list.addItem(item)
            if profile.get("id") == selected_id:
                selected_row = index
        if self.profile_list.count():
            if selected_row >= 0:
                self.profile_list.setCurrentRow(selected_row)
            else:
                self.profile_list.setCurrentRow(0)

    def selected_profile_id(self) -> Optional[str]:
        item = self.profile_list.currentItem()
        if not item:
            return None
        return item.data(Qt.UserRole)

    def selected_profile(self) -> Optional[Dict[str, object]]:
        profile_id = self.selected_profile_id()
        if not profile_id:
            return None
        return self.service.store.by_id(profile_id)

    def update_selected_profile_summary(self) -> None:
        profile = self.selected_profile()
        if not profile:
            self.selected_profile_label.setText("未选择账号档案。")
            self.delete_button.setEnabled(False)
            self.switch_button.setEnabled(False)
            return
        self.delete_button.setEnabled(True)
        self.switch_button.setEnabled(True)
        lines = [
            f"将要切换到：{profile.get('alias', '未命名账号')}",
            f"邮箱：{profile.get('email', '未记录')}",
            f"最近保存：{profile.get('updated_at', '未知')}",
        ]
        self.selected_profile_label.setText("\n".join(lines))

    def ask_alias(self, default_value: str) -> Optional[str]:
        alias, ok = QInputDialog.getText(self, "保存当前账号", "给这个账号起个名字：", text=default_value)
        if not ok:
            return None
        alias = alias.strip()
        if not alias:
            QMessageBox.warning(self, APP_TITLE, "账号名称不能为空。")
            return None
        return alias

    def save_current_profile(self) -> None:
        try:
            active = self.service.get_active_account()
            if not active:
                raise RuntimeError("当前没有检测到 Codex 登录信息。")
            suggested = active.label
            alias = self.ask_alias(suggested)
            if not alias:
                return
            profile = self.service.save_current_as_profile(alias)
        except Exception as exc:
            QMessageBox.critical(self, APP_TITLE, f"保存失败：{exc}")
            return

        self.refresh_all()
        profile_name = profile.get("alias", "该账号")
        QMessageBox.information(self, APP_TITLE, f"保存成功：{profile_name}")

    def switch_selected_profile(self) -> None:
        profile = self.selected_profile()
        if not profile:
            QMessageBox.warning(self, APP_TITLE, "请先选择一个账号档案。")
            return

        alias = profile.get("alias", "未命名账号")
        answer = QMessageBox.question(
            self,
            APP_TITLE,
            f"切换到“{alias}”前会自动关闭正在运行的 Codex，并在切换后重新打开。是否继续？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if answer != QMessageBox.Yes:
            return

        try:
            self.service.ensure_unsaved_active_snapshot(str(profile.get("id", "")))
            self.service.stop_codex()
            self.service.restore_profile(str(profile.get("id", "")))
            reopened = self.service.start_codex()
        except Exception as exc:
            QMessageBox.critical(self, APP_TITLE, f"切换失败：{exc}")
            return

        self.refresh_all()
        if reopened:
            QMessageBox.information(self, APP_TITLE, f"已切换到：{alias}\nCodex 已尝试自动重新打开。")
        else:
            QMessageBox.information(
                self,
                APP_TITLE,
                f"已切换到：{alias}\n没有成功自动拉起 Codex，请手动打开一次。",
            )

    def delete_selected_profile(self) -> None:
        profile = self.selected_profile()
        if not profile:
            return

        alias = profile.get("alias", "未命名账号")
        answer = QMessageBox.question(
            self,
            APP_TITLE,
            f"确定删除账号档案“{alias}”吗？这不会影响当前 Codex 已登录状态。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        try:
            self.service.delete_profile(str(profile.get("id", "")))
        except Exception as exc:
            QMessageBox.critical(self, APP_TITLE, f"删除失败：{exc}")
            return
        self.refresh_all()

    def relaunch_codex(self) -> None:
        try:
            self.service.stop_codex()
            reopened = self.service.start_codex()
        except Exception as exc:
            QMessageBox.critical(self, APP_TITLE, f"操作失败：{exc}")
            return

        if reopened:
            QMessageBox.information(self, APP_TITLE, "Codex 已尝试重新打开。")
        else:
            QMessageBox.warning(self, APP_TITLE, "没有找到 Codex 启动入口，请手动打开。")


def run() -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_TITLE)
    app.setStyle("Fusion")
    window = CodexSwitcherWindow()
    window.show()
    return app.exec_()
