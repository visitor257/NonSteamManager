#!/usr/bin/env python3
"""
修复按钮显示问题的游戏下载客户端
"""

import sys
import os
import json
import time
import hashlib
import random
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import urllib.parse
from downloader import download_game

import requests
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QLabel, QPushButton, QProgressBar,
    QTextEdit, QGroupBox, QTreeWidget, QTreeWidgetItem, QSplitter,
    QFileDialog, QMessageBox, QLineEdit, QFormLayout, QTabWidget,
    QScrollArea, QFrame, QGridLayout, QSizePolicy, QStatusBar,
    QCheckBox, QToolButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QInputDialog, QComboBox,
    QStyledItemDelegate, QStyleOptionViewItem, QStyle
)
from PySide6.QtCore import Qt, Signal, Slot, QThread, QPropertyAnimation, QEasingCurve, QTimer, QSize, QObject
from PySide6.QtGui import QFont, QIcon, QPixmap, QPalette, QColor, QAction, QPainter, QPen, QBrush

# 尝试导入appdata模块
try:
    from appdata import read_binaryVDF, write_binaryVDF, get_appdata, get_grid_id
    APPDATA_AVAILABLE = True
    print("✓ appdata模块已安装，支持Steam VDF功能")
except ImportError:
    APPDATA_AVAILABLE = False
    print("⚠ appdata模块未安装，Steam VDF功能将不可用")
    print("请安装: pip install appdata")



CONFIG_FILE = "config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_config(data):
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"保存配置失败: {e}")

def calculate_file_hash(filepath: str) -> str:
    """计算文件 SHA256 哈希"""
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


class DownloadWorker(QObject):
    """下载工作线程（与UI解耦）"""
    progress = Signal(int, int)      # current, total
    status = Signal(str)
    finished = Signal()
    error = Signal(str)

    def __init__(self, server_url, api_key, game, install_dir):
        super().__init__()
        self.server_url = server_url
        self.api_key = api_key
        self.game = game
        self.install_dir = install_dir

    def run(self):
        try:
            from downloader import download_game
            download_game(
                server_url=self.server_url,
                api_key=self.api_key,
                game=self.game,
                install_dir=self.install_dir,
                progress_callback=self._on_progress,
                status_callback=self._on_status
            )
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))

    def _on_progress(self, current, total):
        self.progress.emit(current, total)

    def _on_status(self, msg):
        self.status.emit(msg)


# ==================== 现代化主题 ====================
class ModernTheme:
    """现代化主题"""

    @staticmethod
    def apply(app):
        """应用现代化主题"""
        # 创建现代化的暗色调色板
        palette = QPalette()

        # 基础颜色
        dark_bg = QColor(20, 20, 20)
        darker_bg = QColor(15, 15, 15)
        card_bg = QColor(30, 30, 30)
        accent_color = QColor(0, 120, 215)  # 蓝色
        text_color = QColor(240, 240, 240)
        muted_text = QColor(150, 150, 150)

        # 设置调色板
        palette.setColor(QPalette.Window, dark_bg)
        palette.setColor(QPalette.WindowText, text_color)
        palette.setColor(QPalette.Base, darker_bg)
        palette.setColor(QPalette.AlternateBase, card_bg)
        palette.setColor(QPalette.ToolTipBase, card_bg)
        palette.setColor(QPalette.ToolTipText, text_color)
        palette.setColor(QPalette.Text, text_color)
        palette.setColor(QPalette.Button, QColor(40, 40, 40))
        palette.setColor(QPalette.ButtonText, text_color)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Link, accent_color)
        palette.setColor(QPalette.Highlight, accent_color)
        palette.setColor(QPalette.HighlightedText, Qt.white)

        app.setPalette(palette)

        # 现代化的样式表
        style = """
            /* ===== 主窗口 ===== */
            QMainWindow {
                background-color: #141414;
            }
            
            /* ===== 选项卡 ===== */
            QTabWidget::pane {
                border: none;
                background-color: transparent;
            }
            
            QTabBar {
                background-color: #1a1a1a;
                border-bottom: 1px solid #2a2a2a;
            }
            
            QTabBar::tab {
                background-color: transparent;
                color: #aaa;
                padding: 12px 24px;
                margin-right: 0px;
                border: none;
                font-weight: 500;
                font-size: 13px;
                min-width: 100px;
            }
            
            QTabBar::tab:selected {
                background-color: #0078d7;
                color: white;
                border-radius: 0px;
            }
            
            QTabBar::tab:hover:!selected {
                background-color: #252525;
                color: #ddd;
            }
            
            /* ===== 卡片 ===== */
            .card {
                background-color: #1e1e1e;
                border: 1px solid #2a2a2a;
                border-radius: 8px;
            }
            
            /* ===== 按钮 ===== */
            QPushButton {
                background-color: #2d2d2d;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: 500;
                min-height: 28px;
                min-width: 70px;
                font-size: 12px;
            }
            
            QPushButton:hover {
                background-color: #353535;
                border-color: #0078d7;
            }
            
            QPushButton:pressed {
                background-color: #252525;
            }
            
            QPushButton:disabled {
                background-color: #1a1a1a;
                color: #666;
                border-color: #2a2a2a;
            }
            
            QPushButton.primary {
                background-color: #0078d7;
                color: white;
                border: none;
                font-weight: 600;
            }
            
            QPushButton.primary:hover {
                background-color: #0066b3;
            }
            
            QPushButton.success {
                background-color: #107c10;
                color: white;
                border: none;
            }
            
            QPushButton.success:hover {
                background-color: #0e6b0e;
            }
            
            QPushButton.danger {
                background-color: #d13438;
                color: white;
                border: none;
            }
            
            QPushButton.danger:hover {
                background-color: #b0262a;
            }
            
            /* 表格中的按钮 */
            QTableWidget QPushButton {
                padding: 4px 8px;
                min-height: 24px;
                min-width: 60px;
                font-size: 11px;
            }
            
            /* ===== 输入框 ===== */
            QLineEdit, QTextEdit, QPlainTextEdit {
                background-color: #252525;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                padding: 8px 12px;
                selection-background-color: #0078d7;
            }
            
            QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
                border-color: #0078d7;
                background-color: #2a2a2a;
            }
            
            /* ===== 表格 ===== */
            QTableWidget {
                background-color: transparent;
                border: 1px solid #2a2a2a;
                border-radius: 4px;
                alternate-background-color: rgba(255, 255, 255, 0.05);
                gridline-color: #2a2a2a;
            }
            
            QTableWidget::item {
                padding: 8px 4px;
                border: none;
            }
            
            QTableWidget::item:selected {
                background-color: rgba(0, 120, 215, 0.3);
                color: white;
            }
            
            QHeaderView::section {
                background-color: #252525;
                color: #ddd;
                padding: 12px 8px;
                border: none;
                border-right: 1px solid #2a2a2a;
                border-bottom: 1px solid #2a2a2a;
                font-weight: 600;
                font-size: 12px;
            }
            
            QHeaderView::section:last {
                border-right: none;
            }
            
            /* 设置行高 */
            QTableWidget {
                font-size: 12px;
            }
            
            /* ===== 复选框 ===== */
            QCheckBox {
                spacing: 6px;
                color: #f0f0f0;
                font-size: 12px;
            }
            
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 2px solid #3a3a3a;
                border-radius: 3px;
                background-color: #252525;
            }
            
            QCheckBox::indicator:checked {
                background-color: #0078d7;
                border-color: #0078d7;
            }
            
            /* ===== 组合框 ===== */
            QComboBox {
                background-color: #252525;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                padding: 8px 12px;
                min-height: 32px;
                font-size: 12px;
            }
            
            QComboBox:hover {
                border-color: #0078d7;
            }
            
            QComboBox::drop-down {
                border: none;
            }
            
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #aaa;
            }
            
            /* ===== 标签 ===== */
            QLabel {
                color: #f0f0f0;
            }
            
            .title {
                font-size: 18px;
                font-weight: 600;
                color: white;
            }
            
            .subtitle {
                font-size: 14px;
                font-weight: 500;
                color: #d0d0d0;
            }
            
            .muted {
                color: #999;
                font-size: 12px;
            }
            
            /* ===== 进度条 ===== */
            QProgressBar {
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                text-align: center;
                background-color: #252525;
                height: 20px;
                font-size: 11px;
            }
            
            QProgressBar::chunk {
                background-color: qlineargradient(
                    spread:pad, x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0078d7, stop:1 #0098f7
                );
                border-radius: 3px;
            }
            
            /* ===== 状态栏 ===== */
            QStatusBar {
                background-color: #1a1a1a;
                color: #aaa;
                border-top: 1px solid #2a2a2a;
                font-size: 11px;
            }
            
            /* ===== 工具按钮 ===== */
            QToolButton {
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
                padding: 6px;
            }
            
            QToolButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
                border-color: #3a3a3a;
            }
        """

        app.setStyleSheet(style)
        app.setStyle("Fusion")

# ==================== Steam VDF 管理器 ====================
class SteamVDFManager:
    """Steam VDF 文件管理器"""

    def __init__(self):
        self.vdf_path = ""
        self.vdf_data = None

    def load_vdf(self, path: str) -> bool:
        """加载VDF文件"""
        if not APPDATA_AVAILABLE:
            return False

        try:
            if not os.path.exists(path):
                return False

            self.vdf_data = read_binaryVDF(path)
            self.vdf_path = path
            return True
        except Exception as e:
            print(f"加载VDF文件失败: {e}")
            return False

    def save_vdf(self) -> bool:
        """保存VDF文件"""
        if not APPDATA_AVAILABLE or not self.vdf_data or not self.vdf_path:
            return False

        try:
            write_binaryVDF(self.vdf_data, self.vdf_path, backup=True)
            return True
        except Exception as e:
            print(f"保存VDF文件失败: {e}")
            return False

    def get_steam_games(self) -> List[Dict]:
        """获取Steam库中的游戏列表"""
        if not self.vdf_data or 'shortcuts' not in self.vdf_data:
            return []

        games = []
        for key, game_data in self.vdf_data['shortcuts'].items():
            game_data['_key'] = key
            games.append(game_data)

        return games

    def get_next_key(self) -> str:
        """获取下一个可用的key"""
        if not self.vdf_data or 'shortcuts' not in self.vdf_data:
            return "0"

        shortcuts = self.vdf_data['shortcuts']
        max_key = -1
        for key in shortcuts.keys():
            try:
                key_int = int(key)
                if key_int > max_key:
                    max_key = key_int
            except ValueError:
                continue

        return str(max_key + 1)

    def add_game(self, app_name: str, exe_path: str, start_dir: str = "", icon: str = "") -> bool:
        if not APPDATA_AVAILABLE or not self.vdf_data:
            return False
    
        try:
            if 'shortcuts' not in self.vdf_data:
                self.vdf_data['shortcuts'] = {}
    
            next_key = self.get_next_key()
            game_dir = Path(exe_path).parent
    
            # === 1. 加载 .addSteam.json ===
            add_steam_file = game_dir / ".addSteam.json"
            add_steam_config = {}
            if add_steam_file.exists():
                try:
                    with open(add_steam_file, 'r', encoding='utf-8') as f:
                        add_steam_config = json.load(f)
                except Exception as e:
                    print(f"加载 .addSteam.json 失败: {e}")
    
            # === 2. 确定 icon ===
            final_icon = icon
            if add_steam_config and add_steam_config.get("exeIcon"):
                exe_icon_path = game_dir / add_steam_config["exeIcon"]
                if exe_icon_path.exists():
                    final_icon = str(exe_icon_path)
    
            # === 3. 创建基础游戏数据（使用负数 appid）===
            basic_data = self._create_basic_game_data(app_name, exe_path, start_dir, final_icon)
            oldid = basic_data['appid']
            self.vdf_data['shortcuts'][next_key] = basic_data
            if not self.save_vdf():
                return False
    
            # === 4. 保存 (vkey, oldid) 到临时文件 ===
            pending_file = Path(self.vdf_path).parent / ".steam_pending.json"
            pending_data = {}
            if pending_file.exists():
                try:
                    with open(pending_file, 'r', encoding='utf-8') as f:
                        pending_data = json.load(f)
                except:
                    pass
            pending_data[next_key] = {
                "oldid": oldid,
                "game_name": app_name,
                "timestamp": time.time()
            }
            with open(pending_file, 'w', encoding='utf-8') as f:
                json.dump(pending_data, f, indent=2, ensure_ascii=False)

            # === 5. 复制资源文件 ===
            if add_steam_config:
                try:
                    grid_dir = Path(self.vdf_path).parent / "grid"
                    grid_dir.mkdir(exist_ok=True)
            
                    # 判断是否可以直接使用 gridID（即 oldid 是负数）
                    if oldid < 0:
                        # 直接使用 oldid 计算 gridID
                        from appdata import get_grid_id
                        grid_id = get_grid_id(oldid)
                        mappings = {
                            "cover":      f"{grid_id}p",
                            "bg":         f"{grid_id}_hero",
                            "icon":       f"{grid_id}_logo",
                            "wideCover":  f"{grid_id}",
                        }
                        pending_needed = False
                    else:
                        # 非负数（理论上不会发生），走 pending 流程
                        mappings = {
                            "cover":      f"id{next_key}p",
                            "bg":         f"id{next_key}_hero",
                            "icon":       f"id{next_key}_logo",
                            "wideCover":  f"id{next_key}",
                        }
                        pending_needed = True
            
                    for key, base_name in mappings.items():
                        if key in add_steam_config:
                            src_rel = add_steam_config[key]
                            if not src_rel:
                                continue
                            src_path = game_dir / src_rel
                            if not src_path.exists():
                                continue
                            suffix = src_path.suffix.lower()
                            dst_path = grid_dir / (base_name + suffix)
                            import shutil
                            shutil.copy2(src_path, dst_path)
                            print(f"[Steam Grid] 已复制 {key}: {dst_path.name}")
            
                    # 只有在需要 pending 时才保存记录
                    if pending_needed:
                        pending_file = Path(self.vdf_path).parent / ".steam_pending.json"
                        pending_data = {}
                        if pending_file.exists():
                            try:
                                with open(pending_file, 'r', encoding='utf-8') as f:
                                    pending_data = json.load(f)
                            except:
                                pass
                        pending_data[next_key] = {
                            "oldid": oldid,
                            "game_name": app_name,
                            "timestamp": time.time()
                        }
                        with open(pending_file, 'w', encoding='utf-8') as f:
                            json.dump(pending_data, f, indent=2, ensure_ascii=False)
            
                except Exception as e:
                    print(f"复制资源失败: {e}")
    
            return True
    
        except Exception as e:
            print(f"添加游戏失败: {e}")
            return False

    def _create_basic_game_data(self, app_name: str, exe_path: str, start_dir: str = "", icon: str = "") -> Dict:
        """创建基本的游戏数据"""
        if not start_dir:
            start_dir = os.path.dirname(exe_path)

        appid = random.randint(-2147483648, -1)

        if ' ' in exe_path and not (exe_path.startswith('"') and exe_path.endswith('"')):
            exe_path = f'"{exe_path}"'

        if ' ' in start_dir and not (start_dir.startswith('"') and start_dir.endswith('"')):
            start_dir = f'"{start_dir}"'

        return {
            'appid': appid,
            'AppName': app_name,
            'Exe': exe_path,
            'StartDir': start_dir,
            'icon': icon,
            'ShortcutPath': '',
            'LaunchOptions': '',
            'IsHidden': 0,
            'AllowDesktopConfig': 1,
            'AllowOverlay': 1,
            'OpenVR': 0,
            'Devkit': 0,
            'DevkitGameID': '',
            'DevkitOverrideAppID': 0,
            'LastPlayTime': 0,
            'FlatpakAppID': '',
            'sortas': '',
            'tags': {}
        }

# ==================== 服务器管理器 ====================
class ServerManager:
    """服务器管理器"""

    def __init__(self):
        self.servers_file = "servers.json"
        self.servers = self.load_servers()

    def load_servers(self) -> List[Dict]:
        """加载服务器列表"""
        if not os.path.exists(self.servers_file):
            return []

        try:
            with open(self.servers_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载服务器列表失败: {e}")
            return []

    def save_servers(self):
        """保存服务器列表"""
        try:
            with open(self.servers_file, 'w', encoding='utf-8') as f:
                json.dump(self.servers, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存服务器列表失败: {e}")

    def add_server(self, name: str, url: str, api_key: str) -> bool:
        """添加服务器"""
        server = {
            'id': str(len(self.servers) + 1),
            'name': name,
            'url': url.rstrip('/'),
            'api_key': api_key,
            'enabled': True
        }

        self.servers.append(server)
        self.save_servers()
        return True

    def remove_server(self, server_id: str) -> bool:
        """移除服务器"""
        self.servers = [s for s in self.servers if s['id'] != server_id]
        self.save_servers()
        return True

    def get_server(self, server_id: str) -> Optional[Dict]:
        """获取服务器信息"""
        for server in self.servers:
            if server['id'] == server_id:
                return server
        return None

# ==================== 游戏客户端 ====================
class GameClient:
    """游戏客户端"""

    def __init__(self, server_url: str, api_key: str):
        self.server_url = server_url.rstrip('/')
        self.headers = {'X-API-Key': api_key}
        self.timeout = 10

    def get_games(self) -> List[Dict]:
        """获取游戏列表"""
        try:
            response = requests.get(
                f"{self.server_url}/games",
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()  # 检查 HTTP 状态码（4xx/5xx 会抛出异常）
    
            # 尝试解析 JSON
            data = response.json()
    
            # 验证数据结构
            if isinstance(data, dict):
                games = data.get('games', [])
            elif isinstance(data, list):
                games = data
            else:
                raise ValueError("响应格式无效：既不是对象也不是数组")
    
            # 验证每个游戏是否包含必要字段（至少要有 name 和 id）
            valid_games = []
            for g in games:
                if isinstance(g, dict) and 'name' in g and ('id' in g or 'url' in g):
                    valid_games.append(g)
                else:
                    print(f"跳过无效游戏条目: {g}")
    
            return valid_games
    
        except requests.exceptions.Timeout:
            raise Exception("请求超时")
        except requests.exceptions.ConnectionError:
            raise Exception("无法连接到服务器")
        except requests.exceptions.HTTPError as e:
            raise Exception(f"HTTP 错误: {e.response.status_code}")
        except ValueError as e:
            raise Exception(f"响应解析失败: {str(e)}")
        except Exception as e:
            raise Exception(f"获取游戏列表失败: {e}")

# ==================== 下载管理器 ====================
class DownloadManager:
    """下载管理器"""

    def __init__(self):
        self.downloads_dir = Path.home() / "Downloads" / "GameDownloads"
        self.downloads_dir.mkdir(parents=True, exist_ok=True)

        self.progress_file = ".downloads.json"
        self.downloads = self.load_downloads()

    def load_downloads(self) -> Dict:
        """加载下载记录"""
        if not os.path.exists(self.progress_file):
            return {}

        try:
            with open(self.progress_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载下载记录失败: {e}")
            return {}

    def save_downloads(self):
        """保存下载记录"""
        try:
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(self.downloads, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存下载记录失败: {e}")

    def get_downloaded_games(self) -> List[Dict]:
        """获取已下载的游戏"""
        games = []

        for game_dir in self.downloads_dir.iterdir():
            if game_dir.is_dir():
                # 检查目录是否包含游戏文件
                exe_files = list(game_dir.rglob("*.exe"))
                if exe_files:
                    game_info = {
                        'id': game_dir.name,
                        'name': game_dir.name,
                        'path': str(game_dir),
                        'exe_path': str(exe_files[0]) if exe_files else "",
                        'size': self.get_folder_size(game_dir),
                        'downloaded_at': game_dir.stat().st_mtime
                    }
                    games.append(game_info)

        return sorted(games, key=lambda x: x['downloaded_at'], reverse=True)

    def get_folder_size(self, path: Path) -> int:
        """获取文件夹大小"""
        total_size = 0
        for file in path.rglob("*"):
            if file.is_file():
                total_size += file.stat().st_size
        return total_size

# ==================== 主窗口 ====================
class MainWindow(QMainWindow):
    """主窗口 - 四标签页布局"""

    def __init__(self):
        super().__init__()
        self.steam_manager = SteamVDFManager()
        self.server_manager = ServerManager()
        self.download_manager = DownloadManager()
        self.current_vdf_path = ""

        self.setup_ui()
        self.load_initial_data()

        self.vdf_watcher_timer = None
        self.vdf_last_hash = None

    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle("Non Steam Manager")
        self.setGeometry(100, 100, 1200, 800)

        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 创建选项卡
        self.tab_widget = QTabWidget()
        self.tab_widget.setObjectName("mainTabs")

        # 创建四个标签页
        self.create_steam_tab()
        self.create_downloaded_tab()
        self.create_download_tab()
        self.create_settings_tab()

        layout.addWidget(self.tab_widget)

        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("就绪")
        self.status_bar.addWidget(self.status_label)

        # 应用主题
        ModernTheme.apply(QApplication.instance())

    def refresh_current_server_view(self):
        """根据当前服务器选择刷新游戏列表"""
        server_id = self.server_combo.currentData()
        if server_id == "all":
            self.refresh_all_servers_games()
        elif server_id:
            self.refresh_server_games()
        else:
            self.server_table.setRowCount(0)
            self.status_label.setText("请选择服务器")

    def start_vdf_watcher(self):
        """启动 VDF 文件监听器"""
        if not self.current_vdf_path:
            return
        self.vdf_last_hash = calculate_file_hash(self.current_vdf_path)
        self.vdf_watcher_timer = QTimer(self)
        self.vdf_watcher_timer.timeout.connect(self.check_vdf_change)
        self.vdf_watcher_timer.start(5000)  # 每5秒检查一次
    
    def check_vdf_change(self):
        """检查 VDF 是否被 Steam 修改"""
        if not os.path.exists(self.current_vdf_path):
            return
        current_hash = calculate_file_hash(self.current_vdf_path)
        if current_hash != self.vdf_last_hash:
            self.vdf_last_hash = current_hash
            self.handle_vdf_updated()
    
    def handle_vdf_updated(self):
        """处理 VDF 更新：检查 pending 记录并重命名 grid 文件"""
        pending_file = Path(self.current_vdf_path).parent / ".steam_pending.json"
        if not pending_file.exists():
            return
    
        try:
            with open(pending_file, 'r', encoding='utf-8') as f:
                pending_data = json.load(f)
        except:
            return
    
        # 重新加载 VDF
        if not self.steam_manager.load_vdf(self.current_vdf_path):
            return
    
        updated = False
        grid_dir = Path(self.current_vdf_path).parent / "grid"
        from appdata import get_grid_id
    
        for vkey, info in list(pending_data.items()):
            oldid = info["oldid"]
            shortcut = self.steam_manager.vdf_data['shortcuts'].get(vkey)
            if not shortcut:
                continue
            newid = shortcut.get('appid')
            if newid != oldid and newid is not None:
                # 获取真实 grid ID
                grid_id = get_grid_id(newid)
                print(f"[Steam Grid] 发现新 appid: {newid} → grid_id: {grid_id}")
    
                # 重命名所有 id<vkey>* 文件
                if grid_dir.exists():
                    for file in grid_dir.iterdir():
                        if file.is_file() and file.name.startswith(f"id{vkey}"):
                            # 提取后缀
                            suffix = file.suffix.lower()
                            if "p" in file.stem and file.stem.endswith("p"):
                                new_name = f"{grid_id}p{suffix}"
                            elif "_hero" in file.stem:
                                new_name = f"{grid_id}_hero{suffix}"
                            elif "_logo" in file.stem:
                                new_name = f"{grid_id}_logo{suffix}"
                            else:
                                new_name = f"{grid_id}{suffix}"
                            new_path = grid_dir / new_name
                            try:
                                file.rename(new_path)
                                print(f"[Steam Grid] 重命名: {file.name} → {new_name}")
                            except Exception as e:
                                print(f"重命名失败: {e}")
    
                # 清理该条目
                del pending_data[vkey]
                updated = True
    
        # 保存或删除 pending 文件
        if updated:
            if pending_data:
                with open(pending_file, 'w', encoding='utf-8') as f:
                    json.dump(pending_data, f, indent=2, ensure_ascii=False)
            else:
                pending_file.unlink(missing_ok=True)
    
            # 刷新 Steam 标签页
            self.load_steam_games()

    def create_steam_tab(self):
        """创建Steam内标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)

        # 标题和VDF选择
        header_layout = QHBoxLayout()

        title_label = QLabel("Steam库内游戏")
        title_label.setProperty("class", "title")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # VDF路径显示
        self.vdf_path_label = QLabel("未选择shortcuts.vdf")
        self.vdf_path_label.setProperty("class", "muted")
        header_layout.addWidget(self.vdf_path_label)

        # 浏览按钮
        self.browse_vdf_btn = QPushButton("选择shortcuts.vdf")
        self.browse_vdf_btn.setProperty("class", "primary")
        self.browse_vdf_btn.clicked.connect(self.browse_vdf_file)
        header_layout.addWidget(self.browse_vdf_btn)

        # 刷新按钮
        self.refresh_steam_btn = QPushButton("刷新")
        self.refresh_steam_btn.clicked.connect(self.load_steam_games)
        # 不设置 class="primary"，使用默认样式
        header_layout.addWidget(self.refresh_steam_btn)

        layout.addLayout(header_layout)

        # Steam游戏列表
        steam_group = QGroupBox("Steam库内游戏")
        steam_layout = QVBoxLayout(steam_group)

        # 搜索框
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("搜索:"))

        self.steam_search_input = QLineEdit()
        self.steam_search_input.setPlaceholderText("搜索游戏...")
        self.steam_search_input.textChanged.connect(self.filter_steam_games)
        search_layout.addWidget(self.steam_search_input)

        steam_layout.addLayout(search_layout)

        # 游戏表格
        self.steam_table = QTableWidget()
        self.steam_table.setColumnCount(4)
        self.steam_table.setHorizontalHeaderLabels(["游戏名称", "可执行文件", "最后游玩", "操作"])
        self.steam_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.steam_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.steam_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.steam_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.steam_table.setAlternatingRowColors(True)
        self.steam_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.steam_table.verticalHeader().setDefaultSectionSize(60)  # 增加行高
        self.steam_table.verticalHeader().setVisible(False)  # 隐藏垂直表头

        # 设置表格样式
        self.steam_table.setShowGrid(False)

        steam_layout.addWidget(self.steam_table)

        layout.addWidget(steam_group)

        # 统计信息
        stats_layout = QHBoxLayout()
        self.steam_stats_label = QLabel("总共 0 个游戏")
        self.steam_stats_label.setProperty("class", "muted")
        stats_layout.addWidget(self.steam_stats_label)
        stats_layout.addStretch()

        layout.addLayout(stats_layout)

        self.tab_widget.addTab(widget, "Steam内")

    def create_downloaded_tab(self):
        """创建已下载标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)

        # 标题
        title_label = QLabel("已下载的游戏")
        title_label.setProperty("class", "title")
        layout.addWidget(title_label)

        # 控制按钮
        control_layout = QHBoxLayout()

        self.refresh_downloaded_btn = QPushButton("刷新列表")
        self.refresh_downloaded_btn.clicked.connect(self.refresh_downloaded_games)
        control_layout.addWidget(self.refresh_downloaded_btn)

        self.select_all_btn = QPushButton("全选")
        self.select_all_btn.clicked.connect(self.select_all_downloaded)
        control_layout.addWidget(self.select_all_btn)

        self.deselect_all_btn = QPushButton("取消全选")
        self.deselect_all_btn.clicked.connect(self.deselect_all_downloaded)
        control_layout.addWidget(self.deselect_all_btn)

        self.add_to_steam_btn = QPushButton("添加到Steam")
        self.add_to_steam_btn.setProperty("class", "primary")
        self.add_to_steam_btn.clicked.connect(self.add_selected_to_steam)
        control_layout.addWidget(self.add_to_steam_btn)

        control_layout.addStretch()
        layout.addLayout(control_layout)

        # 已下载游戏列表
        downloaded_group = QGroupBox("已下载的游戏")
        downloaded_layout = QVBoxLayout(downloaded_group)

        # 搜索框
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("搜索:"))

        self.downloaded_search_input = QLineEdit()
        self.downloaded_search_input.setPlaceholderText("搜索游戏...")
        self.downloaded_search_input.textChanged.connect(self.filter_downloaded_games)
        search_layout.addWidget(self.downloaded_search_input)

        downloaded_layout.addLayout(search_layout)

        # 游戏表格
        self.downloaded_table = QTableWidget()
        self.downloaded_table.setColumnCount(6)
        self.downloaded_table.setHorizontalHeaderLabels(["", "游戏名称", "大小", "下载时间", "路径", "操作"])
        self.downloaded_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.downloaded_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.downloaded_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.downloaded_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.downloaded_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.downloaded_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.downloaded_table.horizontalHeader().resizeSection(0, 40)
        self.downloaded_table.setAlternatingRowColors(True)
        self.downloaded_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.downloaded_table.verticalHeader().setDefaultSectionSize(60)  # 增加行高
        self.downloaded_table.verticalHeader().setVisible(False)  # 隐藏垂直表头

        # 设置表格样式
        self.downloaded_table.setShowGrid(False)

        downloaded_layout.addWidget(self.downloaded_table)
        layout.addWidget(downloaded_group)

        # 统计信息
        stats_layout = QHBoxLayout()
        self.downloaded_stats_label = QLabel("总共 0 个游戏，选中 0 个")
        self.downloaded_stats_label.setProperty("class", "muted")
        stats_layout.addWidget(self.downloaded_stats_label)
        stats_layout.addStretch()

        layout.addLayout(stats_layout)

        self.tab_widget.addTab(widget, "已下载")

    def create_download_tab(self):
        """创建下载标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)

        # 标题
        title_label = QLabel("下载游戏")
        title_label.setProperty("class", "title")
        layout.addWidget(title_label)

        # 服务器选择
        server_layout = QHBoxLayout()
        server_layout.addWidget(QLabel("服务器:"))

        self.server_combo = QComboBox()
        self.server_combo.currentIndexChanged.connect(self.on_server_changed)
        server_layout.addWidget(self.server_combo)
        

        self.refresh_server_btn = QPushButton("刷新服务器")
        # self.refresh_server_btn.clicked.connect(self.refresh_server_games)
        self.refresh_server_btn.clicked.connect(self.refresh_current_server_view)
        server_layout.addWidget(self.refresh_server_btn)

        server_layout.addStretch()
        layout.addLayout(server_layout)

        # 游戏列表区域
        games_group = QGroupBox("服务器游戏列表")
        games_layout = QVBoxLayout(games_group)

        # 搜索框
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("搜索:"))

        self.server_search_input = QLineEdit()
        self.server_search_input.setPlaceholderText("搜索游戏...")
        self.server_search_input.textChanged.connect(self.filter_server_games)
        search_layout.addWidget(self.server_search_input)

        games_layout.addLayout(search_layout)

        # 游戏表格
        self.server_table = QTableWidget()
        self.server_table.setColumnCount(4)
        self.server_table.setHorizontalHeaderLabels(["游戏名称", "版本", "大小", "操作"])
        self.server_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.server_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.server_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.server_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.server_table.setAlternatingRowColors(True)
        self.server_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.server_table.verticalHeader().setDefaultSectionSize(60)  # 增加行高
        self.server_table.verticalHeader().setVisible(False)  # 隐藏垂直表头

        # 设置表格样式
        self.server_table.setShowGrid(False)

        games_layout.addWidget(self.server_table)
        layout.addWidget(games_group)

        # 下载控制
        download_control_group = QGroupBox("下载控制")
        download_control_layout = QVBoxLayout(download_control_group)

        # 安装目录
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(QLabel("安装目录:"))

        self.install_dir_input = QLineEdit(str(self.download_manager.downloads_dir))
        dir_layout.addWidget(self.install_dir_input)

        self.browse_dir_btn = QPushButton("浏览")
        self.browse_dir_btn.clicked.connect(self.browse_install_dir)
        dir_layout.addWidget(self.browse_dir_btn)

        download_control_layout.addLayout(dir_layout)

        # 下载按钮
        self.download_btn = QPushButton("开始下载")
        self.download_btn.setProperty("class", "primary")
        self.download_btn.clicked.connect(self.start_download)
        self.download_btn.setEnabled(False)
        download_control_layout.addWidget(self.download_btn)

        # 下载进度
        self.download_progress_bar = QProgressBar()
        self.download_progress_bar.setVisible(False)
        download_control_layout.addWidget(self.download_progress_bar)

        self.download_status_label = QLabel("")
        self.download_status_label.setProperty("class", "muted")
        download_control_layout.addWidget(self.download_status_label)

        layout.addWidget(download_control_group)

        self.tab_widget.addTab(widget, "下载")

    def create_settings_tab(self):
        """创建设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)

        # 标题
        title_label = QLabel("设置")
        title_label.setProperty("class", "title")
        layout.addWidget(title_label)

        # 服务器设置
        server_settings_group = QGroupBox("服务器管理")
        server_settings_layout = QVBoxLayout(server_settings_group)

        # 添加服务器表单
        form_layout = QFormLayout()

        self.server_name_input = QLineEdit()
        self.server_name_input.setPlaceholderText("服务器名称")
        form_layout.addRow("名称:", self.server_name_input)

        self.server_url_input = QLineEdit()
        self.server_url_input.setPlaceholderText("http://localhost:8000")
        form_layout.addRow("地址:", self.server_url_input)

        self.server_api_key_input = QLineEdit()
        self.server_api_key_input.setPlaceholderText("API密钥")
        self.server_api_key_input.setEchoMode(QLineEdit.Password)
        form_layout.addRow("API密钥:", self.server_api_key_input)

        server_settings_layout.addLayout(form_layout)

        # 添加服务器按钮
        self.add_server_btn = QPushButton("添加服务器")
        self.add_server_btn.setProperty("class", "primary")
        self.add_server_btn.clicked.connect(self.add_server)
        server_settings_layout.addWidget(self.add_server_btn)

        # 服务器列表
        server_list_group = QGroupBox("服务器列表")
        server_list_layout = QVBoxLayout(server_list_group)

        self.servers_table = QTableWidget()
        self.servers_table.setColumnCount(5)
        self.servers_table.setHorizontalHeaderLabels(["名称", "地址", "状态", "操作"])
        self.servers_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.servers_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.servers_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.servers_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.servers_table.setAlternatingRowColors(True)
        self.servers_table.verticalHeader().setDefaultSectionSize(60)  # 增加行高
        self.servers_table.verticalHeader().setVisible(False)  # 隐藏垂直表头

        # 设置表格样式
        self.servers_table.setShowGrid(False)

        server_list_layout.addWidget(self.servers_table)
        server_settings_layout.addWidget(server_list_group)

        layout.addWidget(server_settings_group)

        # 应用设置
        app_settings_group = QGroupBox("应用程序设置")
        app_settings_layout = QFormLayout(app_settings_group)

        # 默认下载目录
        self.default_dir_input = QLineEdit(str(self.download_manager.downloads_dir))
        app_settings_layout.addRow("默认下载目录:", self.default_dir_input)

        self.browse_default_dir_btn = QPushButton("浏览")
        self.browse_default_dir_btn.clicked.connect(lambda: self.browse_directory(self.default_dir_input))
        app_settings_layout.addRow("", self.browse_default_dir_btn)

        # 自动添加到Steam
        self.auto_add_to_steam_check = QCheckBox("下载完成后自动添加到Steam")
        app_settings_layout.addRow("", self.auto_add_to_steam_check)

        layout.addWidget(app_settings_group)

        # 保存设置按钮
        self.save_settings_btn = QPushButton("保存设置")
        self.save_settings_btn.setProperty("class", "primary")
        self.save_settings_btn.clicked.connect(self.save_settings)
        layout.addWidget(self.save_settings_btn, alignment=Qt.AlignRight)

        layout.addStretch()
        self.tab_widget.addTab(widget, "设置")

    def load_initial_data(self):
        config = load_config()
        self.load_servers()
    
        # 恢复上次服务器选择（但不立即加载游戏！）
        last_server_id = config.get("last_server_id")
        if last_server_id == "all":
            self.server_combo.setCurrentIndex(0)
        else:
            for i in range(self.server_combo.count()):
                if self.server_combo.itemData(i) == last_server_id:
                    self.server_combo.setCurrentIndex(i)
                    break
    
        # 自动加载 VDF（本地文件，不卡）
        last_vdf = config.get("last_vdf_path")
        if last_vdf and os.path.exists(last_vdf):
            self.load_vdf_file(last_vdf)
        else:
            # 尝试默认路径
            if sys.platform == "win32":
                import glob
                for pattern in [
                    r"%ProgramFiles(x86)%\Steam\userdata\*\config\shortcuts.vdf",
                    r"%LOCALAPPDATA%\Steam\userdata\*\config\shortcuts.vdf"
                ]:
                    matches = glob.glob(os.path.expandvars(pattern))
                    if matches:
                        self.load_vdf_file(matches[0])
                        break
    
        self.refresh_downloaded_games()

    def load_vdf_file(self, path: str):
        if self.steam_manager.load_vdf(path):
            self.current_vdf_path = path
            self.vdf_path_label.setText(os.path.basename(path))
            self.load_steam_games()
            self.status_label.setText(f"已加载VDF文件: {path}")
            # 也在这里保存（比如从默认路径加载时）
            config = load_config()
            config["last_vdf_path"] = path
            save_config(config)
        else:
            self.status_label.setText("加载VDF文件失败")

    def load_steam_games(self):
        """加载Steam游戏"""
        if not self.steam_manager.vdf_data:
            # 如果还没加载 VDF，尝试从 current_vdf_path 重新加载
            if self.current_vdf_path and os.path.exists(self.current_vdf_path):
                if not self.steam_manager.load_vdf(self.current_vdf_path):
                    self.status_label.setText("无法加载 VDF 文件")
                    return
            else:
                # 清空表格
                self.steam_table.setRowCount(0)
                self.steam_stats_label.setText("未加载 shortcuts.vdf")
                return
        
        games = self.steam_manager.get_steam_games()

        self.steam_table.setRowCount(len(games))
        for i, game in enumerate(games):
            # 设置行高
            self.steam_table.setRowHeight(i, 60)

            # 游戏名称
            name_item = QTableWidgetItem(game.get('AppName', '未知'))
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.steam_table.setItem(i, 0, name_item)

            # 可执行文件
            exe_item = QTableWidgetItem(game.get('Exe', ''))
            exe_item.setFlags(exe_item.flags() & ~Qt.ItemIsEditable)
            self.steam_table.setItem(i, 1, exe_item)

            # 最后游玩时间
            last_play = game.get('LastPlayTime', 0)
            if last_play > 0:
                time_str = datetime.fromtimestamp(last_play).strftime("%Y-%m-%d %H:%M")
            else:
                time_str = "从未"
            time_item = QTableWidgetItem(time_str)
            time_item.setFlags(time_item.flags() & ~Qt.ItemIsEditable)
            self.steam_table.setItem(i, 2, time_item)

            # 操作按钮
            widget = QWidget()
            layout = QHBoxLayout(widget)
            layout.setContentsMargins(2, 2, 2, 2)  # 减少边距
            layout.setSpacing(2)  # 减少间距

            remove_btn = QPushButton("移除")
            remove_btn.setProperty("class", "danger")
            remove_btn.setFixedSize(60, 24)  # 固定按钮大小
            remove_btn.clicked.connect(lambda checked, g=game: self.remove_from_steam(g))
            layout.addWidget(remove_btn)

            layout.addStretch()
            self.steam_table.setCellWidget(i, 3, widget)

        self.steam_stats_label.setText(f"总共 {len(games)} 个游戏")

    def filter_steam_games(self, text: str):
        """过滤Steam游戏"""
        for i in range(self.steam_table.rowCount()):
            name_item = self.steam_table.item(i, 0)
            exe_item = self.steam_table.item(i, 1)

            if name_item and exe_item:
                name = name_item.text().lower()
                exe = exe_item.text().lower()
                search = text.lower()

                visible = search in name or search in exe
                self.steam_table.setRowHidden(i, not visible)

    def refresh_downloaded_games(self):
        """刷新已下载游戏列表"""
        games = self.download_manager.get_downloaded_games()

        self.downloaded_table.setRowCount(len(games))
        self.downloaded_game_data = []

        for i, game in enumerate(games):
            self.downloaded_game_data.append(game)

            # 设置行高
            self.downloaded_table.setRowHeight(i, 60)

            # 复选框
            widget = QWidget()
            layout = QHBoxLayout(widget)
            layout.setContentsMargins(2, 2, 2, 2)  # 减少边距
            layout.setSpacing(2)  # 减少间距

            checkbox = QCheckBox()
            checkbox.setFixedSize(20, 20)  # 固定复选框大小
            checkbox.stateChanged.connect(self.update_downloaded_stats)
            layout.addWidget(checkbox, alignment=Qt.AlignCenter)
            layout.addStretch()
            self.downloaded_table.setCellWidget(i, 0, widget)

            # 游戏名称
            name_item = QTableWidgetItem(game['name'])
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.downloaded_table.setItem(i, 1, name_item)

            # 大小
            size_item = QTableWidgetItem(self.format_size(game['size']))
            size_item.setFlags(size_item.flags() & ~Qt.ItemIsEditable)
            self.downloaded_table.setItem(i, 2, size_item)

            # 下载时间
            time_item = QTableWidgetItem(datetime.fromtimestamp(game['downloaded_at']).strftime("%Y-%m-%d %H:%M"))
            time_item.setFlags(time_item.flags() & ~Qt.ItemIsEditable)
            self.downloaded_table.setItem(i, 3, time_item)

            # 路径
            path_item = QTableWidgetItem(game['path'])
            path_item.setFlags(path_item.flags() & ~Qt.ItemIsEditable)
            self.downloaded_table.setItem(i, 4, path_item)


            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(2, 2, 2, 2)
            action_layout.setSpacing(2)
            
            delete_btn = QPushButton("删除")
            delete_btn.setProperty("class", "danger")
            delete_btn.setFixedSize(60, 24)
            delete_btn.clicked.connect(lambda checked, g=game: self.delete_downloaded_game(g))
            action_layout.addWidget(delete_btn)
            action_layout.addStretch()

            self.downloaded_table.setCellWidget(i, 5, action_widget)

        self.update_downloaded_stats()

    def delete_downloaded_game(self, game: Dict):
        """删除已下载的游戏"""
        game_path = Path(game['path'])
        if not game_path.exists():
            QMessageBox.warning(self, "警告", f"游戏目录不存在:\n{game_path}")
            return
    
        reply = QMessageBox.question(
            self,
            '确认删除',
            f'确定要删除游戏 "{game["name"]}" 吗？\n\n路径: {game_path}',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                import shutil
                shutil.rmtree(game_path)  # 递归删除整个目录
                self.refresh_downloaded_games()  # 刷新列表
                self.status_label.setText(f"已删除游戏: {game['name']}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除失败:\n{str(e)}")

    def filter_downloaded_games(self, text: str):
        """过滤已下载游戏"""
        for i in range(self.downloaded_table.rowCount()):
            name_item = self.downloaded_table.item(i, 1)
            path_item = self.downloaded_table.item(i, 4)

            if name_item and path_item:
                name = name_item.text().lower()
                path = path_item.text().lower()
                search = text.lower()

                visible = search in name or search in path
                self.downloaded_table.setRowHidden(i, not visible)

    def select_all_downloaded(self):
        """全选已下载游戏"""
        for i in range(self.downloaded_table.rowCount()):
            if not self.downloaded_table.isRowHidden(i):
                widget = self.downloaded_table.cellWidget(i, 0)
                if widget:
                    checkbox = widget.findChild(QCheckBox)
                    if checkbox:
                        checkbox.setChecked(True)

    def deselect_all_downloaded(self):
        """取消全选已下载游戏"""
        for i in range(self.downloaded_table.rowCount()):
            widget = self.downloaded_table.cellWidget(i, 0)
            if widget:
                checkbox = widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(False)

    def update_downloaded_stats(self):
        """更新已下载游戏统计"""
        selected_count = 0
        visible_count = 0
        for i in range(self.downloaded_table.rowCount()):
            if not self.downloaded_table.isRowHidden(i):
                visible_count += 1
                widget = self.downloaded_table.cellWidget(i, 0)
                if widget:
                    checkbox = widget.findChild(QCheckBox)
                    if checkbox and checkbox.isChecked():
                        selected_count += 1

        self.downloaded_stats_label.setText(f"总共 {visible_count} 个游戏，选中 {selected_count} 个")

    def load_servers(self):
        """加载服务器列表"""
        self.server_combo.clear()
        # self.server_combo.addItem("选择服务器...", None)
        self.server_combo.addItem("全部服务器", "all")

        for server in self.server_manager.servers:
            if server.get('enabled', True):
                self.server_combo.addItem(server['name'], server['id'])

        # 更新服务器表格
        self.update_servers_table()

    def on_server_changed(self, index: int):
        server_id = self.server_combo.currentData()
        config = load_config()
        config["last_server_id"] = server_id
        save_config(config)
    
        if server_id == "all":
            self.refresh_all_servers_games()
        elif server_id:
            self.refresh_server_games()

    def refresh_all_servers_games(self):
        all_games = []
        success_count = 0
        for server in self.server_manager.servers:
            if not server.get('enabled', True):
                continue
            try:
                client = GameClient(server['url'], server['api_key'])
                games = client.get_games()
                for g in games:
                    g['_server'] = {
                        'id': server['id'],
                        'name': server['name'],
                        'url': server['url'],
                        'api_key': server['api_key']
                    }
                    all_games.append(g)
                success_count += 1
            except Exception as e:
                print(f"❌ 服务器 {server['name']} 加载失败: {e}")
                # 不中断，继续下一个服务器
    
        # 只有在有有效数据时才更新表格
        self.server_table.setRowCount(len(all_games))
        self.server_game_data = all_games
    
        for i, game in enumerate(all_games):
            self.server_table.setRowHeight(i, 60)
            name_text = f"{game.get('name', '未知')} [{game['_server']['name']}]"
            name_item = QTableWidgetItem(name_text)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.server_table.setItem(i, 0, name_item)
    
            version_item = QTableWidgetItem(game.get('version', '未知'))
            version_item.setFlags(version_item.flags() & ~Qt.ItemIsEditable)
            self.server_table.setItem(i, 1, version_item)
    
            size_item = QTableWidgetItem(self.format_size(game.get('size', 0)))
            size_item.setFlags(size_item.flags() & ~Qt.ItemIsEditable)
            self.server_table.setItem(i, 2, size_item)
    
            widget = QWidget()
            layout = QHBoxLayout(widget)
            layout.setContentsMargins(2, 2, 2, 2)
            layout.setSpacing(2)
            download_btn = QPushButton("下载")
            download_btn.setProperty("class", "primary")
            download_btn.setFixedSize(60, 24)
            download_btn.clicked.connect(lambda checked, g=game: self.prepare_download(g))
            layout.addWidget(download_btn)
            layout.addStretch()
            self.server_table.setCellWidget(i, 3, widget)
    
        self.status_label.setText(f"已加载 {len(all_games)} 个游戏（来自 {success_count} 个服务器）")

    def refresh_server_games(self):
        server_id = self.server_combo.currentData()
        if not server_id or server_id == "all":
            return
    
        server = self.server_manager.get_server(server_id)
        if not server:
            return
    
        try:
            client = GameClient(server['url'], server['api_key'])
            games = client.get_games()
            self.server_table.setRowCount(len(games))
            self.server_game_data = games
    
            for i, game in enumerate(games):
                self.server_table.setRowHeight(i, 60)
                name_item = QTableWidgetItem(game.get('name', '未知'))
                name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
                self.server_table.setItem(i, 0, name_item)
    
                version_item = QTableWidgetItem(game.get('version', '未知'))
                version_item.setFlags(version_item.flags() & ~Qt.ItemIsEditable)
                self.server_table.setItem(i, 1, version_item)
    
                size_item = QTableWidgetItem(self.format_size(game.get('size', 0)))
                size_item.setFlags(size_item.flags() & ~Qt.ItemIsEditable)
                self.server_table.setItem(i, 2, size_item)
    
                widget = QWidget()
                layout = QHBoxLayout(widget)
                layout.setContentsMargins(2, 2, 2, 2)
                layout.setSpacing(2)
                download_btn = QPushButton("下载")
                download_btn.setProperty("class", "primary")
                download_btn.setFixedSize(60, 24)
                download_btn.clicked.connect(lambda checked, g=game: self.prepare_download(g))
                layout.addWidget(download_btn)
                layout.addStretch()
                self.server_table.setCellWidget(i, 3, widget)
    
            self.status_label.setText(f"已加载 {len(games)} 个游戏")
    
        except Exception as e:
            QMessageBox.warning(self, "错误", f"获取游戏列表失败:\n{str(e)}")
            self.server_table.setRowCount(0)  # 清空表格
            self.status_label.setText("加载失败")

    def filter_server_games(self, text: str):
        """过滤服务器游戏"""
        for i in range(self.server_table.rowCount()):
            name_item = self.server_table.item(i, 0)
            version_item = self.server_table.item(i, 1)

            if name_item and version_item:
                name = name_item.text().lower()
                version = version_item.text().lower()
                search = text.lower()

                visible = search in name or search in version
                self.server_table.setRowHidden(i, not visible)

    def update_servers_table(self):
        """更新服务器表格"""
        self.servers_table.setRowCount(len(self.server_manager.servers))

        for i, server in enumerate(self.server_manager.servers):
            # 设置行高
            self.servers_table.setRowHeight(i, 60)

            # 服务器名称
            name_item = QTableWidgetItem(server['name'])
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.servers_table.setItem(i, 0, name_item)

            # 服务器地址
            url_item = QTableWidgetItem(server['url'])
            url_item.setFlags(url_item.flags() & ~Qt.ItemIsEditable)
            self.servers_table.setItem(i, 1, url_item)

            # 状态
            status_item = QTableWidgetItem("启用" if server.get('enabled', True) else "禁用")
            status_item.setFlags(status_item.flags() & ~Qt.ItemIsEditable)
            self.servers_table.setItem(i, 2, status_item)

            # 操作按钮
            widget = QWidget()
            layout = QHBoxLayout(widget)
            layout.setContentsMargins(2, 2, 2, 2)  # 减少边距
            layout.setSpacing(2)  # 减少间距

            test_btn = QPushButton("测试")
            test_btn.setFixedSize(50, 24)  # 固定按钮大小
            test_btn.clicked.connect(lambda checked, s=server: self.test_server(s))
            layout.addWidget(test_btn)

            remove_btn = QPushButton("删除")
            remove_btn.setProperty("class", "danger")
            remove_btn.setFixedSize(50, 24)  # 固定按钮大小
            remove_btn.clicked.connect(lambda checked, s=server: self.remove_server(s))
            layout.addWidget(remove_btn)

            layout.addStretch()
            self.servers_table.setCellWidget(i, 3, widget)

    def browse_vdf_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择shortcuts.vdf文件", "", "shortcuts.vdf (shortcuts.vdf);;所有文件 (*.*)"
        )
        if file_path:
            self.load_vdf_file(file_path)
            # 保存到配置
            config = load_config()
            config["last_vdf_path"] = file_path
            save_config(config)

    def browse_install_dir(self):
        """浏览安装目录"""
        dir_path = QFileDialog.getExistingDirectory(
            self, "选择安装目录",
            str(self.download_manager.downloads_dir)
        )

        if dir_path:
            self.install_dir_input.setText(dir_path)

    def browse_directory(self, target_input: QLineEdit):
        """浏览目录"""
        dir_path = QFileDialog.getExistingDirectory(
            self, "选择目录",
            target_input.text()
        )

        if dir_path:
            target_input.setText(dir_path)

    def prepare_download(self, game: Dict):
        """准备下载游戏"""
        self.selected_game = game
        self.download_btn.setEnabled(True)
        default_path = self.download_manager.downloads_dir / game.get('id', 'game')
        self.install_dir_input.setText(str(default_path))
        self.status_label.setText(f"准备下载: {game.get('name')}")

    def start_download(self):
        if not hasattr(self, 'selected_game'):
            return

        # ✅ 显示进度控件
        self.download_progress_bar.setVisible(True)
        self.download_progress_bar.setValue(0)
        self.download_status_label.setText("准备下载...")
        self.download_btn.setEnabled(False)  # 防止重复点击
    
        install_dir = Path(self.install_dir_input.text())
        game = self.selected_game
    
        # 优先从游戏自身获取服务器信息（用于“全部服务器”模式）
        if '_server' in game:
            server_info = game['_server']
            server_url = server_info['url']
            api_key = server_info['api_key']
        else:
            # 否则从下拉框获取（兼容单服务器模式）
            server_id = self.server_combo.currentData()
            if not server_id or server_id == "all":
                QMessageBox.warning(self, "错误", "请选择一个有效的服务器")
                return
            server = self.server_manager.get_server(server_id)
            if not server:
                return
            server_url = server['url']
            api_key = server['api_key']

        # 创建工作线程
        self.download_thread = QThread()
        self.worker = DownloadWorker(
            server_url=server_url,
            api_key=api_key,
            game=game,
            install_dir=install_dir
        )
    
        # ✅ 确保所有信号都连接
        self.worker.progress.connect(self.on_download_progress)
        self.worker.status.connect(self.on_download_status)
        self.worker.finished.connect(self.on_download_finished)
        self.worker.error.connect(self.on_download_error)
    
        # ✅ 关键：确保线程清理
        self.worker.finished.connect(self.download_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.download_thread.finished.connect(self.download_thread.deleteLater)
    
        self.download_thread.started.connect(self.worker.run)
        self.worker.moveToThread(self.download_thread)
        self.download_thread.start()  # 启动线程


    @Slot(int, int)
    def on_download_progress(self, current, total):
        if total <= 0:
            pct = 100
        else:
            pct = int(current / total * 100)
        self.download_progress_bar.setValue(pct)
    
    @Slot(str)
    def on_download_status(self, msg):
        self.download_status_label.setText(msg)

    @Slot()
    def on_download_finished(self):
        self.refresh_downloaded_games()
        self.status_label.setText("下载完成！")
        self.download_btn.setEnabled(True)
        # 可稍等2秒再隐藏，让用户看到100%
        QTimer.singleShot(2000, lambda: self.download_progress_bar.setVisible(False))

    @Slot(str)
    def on_download_error(self, error_msg):
        self.download_status_label.setText(f"下载失败: {error_msg}")
        QMessageBox.critical(self, "错误", error_msg)
        self.download_btn.setEnabled(True)
        self.download_progress_bar.setVisible(False)


    def add_server(self):
        """添加服务器"""
        name = self.server_name_input.text().strip()
        url = self.server_url_input.text().strip()
        api_key = self.server_api_key_input.text().strip()

        if not all([name, url, api_key]):
            QMessageBox.warning(self, "错误", "请填写所有字段")
            return

        if self.server_manager.add_server(name, url, api_key):
            self.load_servers()
            self.server_name_input.clear()
            self.server_url_input.clear()
            self.server_api_key_input.clear()
            self.status_label.setText(f"已添加服务器: {name}")

    def test_server(self, server: Dict):
        try:
            client = GameClient(server['url'], server['api_key'])
            games = client.get_games()
            # 即使 games 为空，只要没抛异常，就算连接成功
            QMessageBox.information(self, "成功", f"服务器连接成功！\n找到 {len(games)} 个游戏")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"服务器连接失败:\n{str(e)}")

    def remove_server(self, server: Dict):
        """移除服务器"""
        reply = QMessageBox.question(
            self, '确认',
            f'确定要删除服务器 "{server["name"]}" 吗？',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.server_manager.remove_server(server['id'])
            self.load_servers()
            self.status_label.setText(f"已删除服务器: {server['name']}")

    def add_selected_to_steam(self):
        """添加选中的游戏到Steam"""
        if not self.current_vdf_path:
            QMessageBox.warning(self, "错误", "请先选择shortcuts.vdf文件")
            return

        added_count = 0
        for i in range(self.downloaded_table.rowCount()):
            widget = self.downloaded_table.cellWidget(i, 0)
            if widget and not self.downloaded_table.isRowHidden(i):
                checkbox = widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    game = self.downloaded_game_data[i]

                    # 查找可执行文件
                    exe_path = game.get('exe_path', '')
                    if not exe_path:
                        exe_files = list(Path(game['path']).rglob("*.exe"))
                        if exe_files:
                            exe_path = str(exe_files[0])

                    if exe_path and self.steam_manager.add_game(game['name'], exe_path):
                        added_count += 1

        # 在 add_selected_to_steam 中
        if added_count > 0:
            self.load_steam_games()
            self.status_label.setText(f"已添加 {added_count} 个游戏到Steam")
        
            # 检查是否有任何游戏走了 pending 流程（即 oldid >= 0）
            # 但目前所有都是负数，所以通常不需要提示“不要关闭”
            # 为兼容性，仍保留提示
        
            msg = QMessageBox(self)
            msg.setWindowTitle("添加成功")
            msg.setText("添加完成，现可在Steam内启动游戏。\n"
                        "封面、图标等资源已写入（如存在 .addSteam.json）。")
            msg.setIcon(QMessageBox.Information)
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec()
        
            # 仅当存在 pending 记录时才启动监听器
            pending_file = Path(self.current_vdf_path).parent / ".steam_pending.json"
            if pending_file.exists():
                self.start_vdf_watcher()
        else:
            self.status_label.setText("没有可添加的游戏")

    def remove_from_steam(self, game: Dict):
        """从Steam移除游戏，并清理grid资源"""
        reply = QMessageBox.question(
            self, '确认',
            f'确定要从Steam移除游戏 "{game.get("AppName")}" 吗？\n'
            f'同时会删除其在 grid/ 文件夹中的封面、背景等资源。',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
    
        # 1. 从 VDF 中移除
        if 'shortcuts' in self.steam_manager.vdf_data and '_key' in game:
            appid = game.get('appid')
            del self.steam_manager.vdf_data['shortcuts'][game['_key']]
            self.steam_manager.save_vdf()
    
            # 2. 清理 grid 文件（仅当 appdata 可用且 appid 存在）
            if APPDATA_AVAILABLE and appid is not None:
                try:
                    from appdata import get_grid_id
                    grid_id = get_grid_id(appid)
                    grid_dir = Path(self.current_vdf_path).parent / "grid"
                    if grid_dir.exists():
                        deleted_count = 0
                        for file in grid_dir.iterdir():
                            if file.is_file() and file.name.startswith(str(grid_id)):
                                file.unlink()
                                deleted_count += 1
                                print(f"[Steam Grid] 已删除: {file.name}")
                        if deleted_count > 0:
                            self.status_label.setText(f"已移除游戏并清理 {deleted_count} 个 grid 文件")
                        else:
                            self.status_label.setText("已移除游戏（无匹配的 grid 文件）")
                    else:
                        self.status_label.setText("已移除游戏（grid 目录不存在）")
                except Exception as e:
                    print(f"清理 grid 文件失败: {e}")
                    self.status_label.setText("已移除游戏，但清理 grid 文件失败")
            else:
                self.status_label.setText("已移除游戏")
    
            # 3. 刷新 UI
            self.load_steam_games()
        else:
            QMessageBox.warning(self, "错误", "无法找到游戏条目")

    def save_settings(self):
        """保存设置"""
        # 保存下载目录
        new_dir = Path(self.default_dir_input.text())
        if new_dir != self.download_manager.downloads_dir:
            self.download_manager.downloads_dir = new_dir
            new_dir.mkdir(parents=True, exist_ok=True)

        self.status_label.setText("设置已保存")

    def format_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"

def main():
    """主函数"""
    app = QApplication(sys.argv)

    # 设置应用程序信息
    app.setApplicationName("Non Steam Manager")
    app.setOrganizationName("NonSteamManager")

    # 创建并显示主窗口
    window = MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()