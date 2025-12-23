#!/usr/bin/env python3
"""
基于文件顺序的进度控制下载服务器
支持configToClient配置字段
"""

import json
import os
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import logging
from datetime import datetime
from fastapi import FastAPI, HTTPException, Query, Depends, Header
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import aiofiles
from pydantic import BaseModel
from typing import Dict, List, Optional, Any

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("GameDownloadServer")

# 数据模型
class GameInfo(BaseModel):
    """游戏信息"""
    id: str
    name: str
    version: str
    description: Optional[str] = None
    directory: str
    configToClient: Optional[Dict[str, Any]] = None  # 新增字段

class FileInfo(BaseModel):
    """文件信息"""
    path: str
    size: int
    checksum: str
    relative_path: str
    is_dir: bool = False

class GameFileList(BaseModel):
    """游戏文件列表"""
    game_id: str
    game_name: str
    files: List[Dict]
    total_files: int
    total_size: int
    file_tree: List[Dict]
    configToClient: Optional[Dict[str, Any]] = None  # 新增字段

class DownloadStartInfo(BaseModel):
    """下载起始信息"""
    game_id: str
    start_file_index: int
    start_file_path: str
    start_file_offset: int
    files: List[Dict]
    message: str
    configToClient: Optional[Dict[str, Any]] = None  # 新增字段

class GameDownloadServer:
    """游戏下载服务器"""

    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.config = self._load_config()
        self.start_time = datetime.now()

        # 初始化FastAPI应用
        self.app = FastAPI(
            title="Game Download Server",
            description="基于文件顺序的进度控制下载服务器",
            version="4.0.0"
        )

        # 添加CORS中间件
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # 设置路由
        self._setup_routes()

    def _load_config(self) -> dict:
        """加载配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # 验证游戏目录存在
            for game in config.get('games', []):
                game_dir = game.get('directory')
                if game_dir and not os.path.exists(game_dir):
                    logger.warning(f"游戏目录不存在: {game_dir}")

            logger.info(f"配置文件加载成功，共 {len(config.get('games', []))} 个游戏")
            return config

        except FileNotFoundError:
            logger.error(f"配置文件不存在: {self.config_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"配置文件格式错误: {e}")
            raise

    def _verify_api_key(self, api_key: Optional[str] = Header(None, alias="X-API-Key")) -> bool:
        """验证API密钥"""
        # 检查是否需要验证
        if not self.config.get('server', {}).get('verify', True):
            return True

        secret_key = self.config.get('server', {}).get('secret_key')
        if not secret_key:
            logger.warning("服务器未配置密钥")
            return True

        if api_key == secret_key:
            return True

        logger.warning(f"无效的API密钥尝试: {api_key[:8] if api_key else 'None'}...")
        return False

    def _get_game_info(self, game_id: str) -> Optional[Dict]:
        """获取游戏信息"""
        for game in self.config.get('games', []):
            if game.get('id') == game_id:
                return game
        return None

    def _scan_game_files(self, game_info: Dict) -> Tuple[List[Dict], List[Dict]]:
        """扫描游戏目录，获取文件列表和树形结构"""
        game_dir = game_info.get('directory')
        if not game_dir or not os.path.exists(game_dir):
            return [], []

        files = []
        file_tree = []
        base_path = Path(game_dir)

        def build_tree(current_path: Path, relative_path: str = "") -> List[Dict]:
            """构建目录树"""
            tree = []

            # 获取所有条目并排序：目录在前，文件在后
            entries = sorted(list(current_path.iterdir()),
                             key=lambda x: (not x.is_dir(), x.name.lower()))

            for entry in entries:
                relative = entry.relative_to(base_path)
                rel_str = str(relative).replace('\\', '/')

                if entry.is_file():
                    # 计算文件哈希
                    file_hash = self._calculate_file_hash(entry)
                    file_size = entry.stat().st_size

                    # 添加到文件列表
                    files.append({
                        'path': rel_str,
                        'size': file_size,
                        'checksum': f"sha256:{file_hash}",
                        'relative_path': rel_str,
                        'download_url': f"/download/file/{game_info['id']}/{rel_str}"
                    })

                    # 添加到树结构
                    tree.append({
                        'name': entry.name,
                        'path': rel_str,
                        'size': file_size,
                        'type': 'file',
                        'checksum': f"sha256:{file_hash}"
                    })

                else:  # 目录
                    children = build_tree(entry, rel_str)
                    tree.append({
                        'name': entry.name,
                        'path': rel_str + '/',
                        'type': 'directory',
                        'children': children
                    })

            return tree

        # 构建文件树
        file_tree = build_tree(base_path)

        return files, file_tree

    def _calculate_file_hash(self, file_path: Path, chunk_size: int = 8192) -> str:
        """计算文件哈希值"""
        sha256_hash = hashlib.sha256()

        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(chunk_size), b''):
                sha256_hash.update(chunk)

        return sha256_hash.hexdigest()

    def _get_start_file_index(self, files: List[Dict], progress_percent: float) -> Tuple[int, int]:
        """
        根据进度百分比计算起始文件和偏移量
        
        参数:
            files: 文件列表
            progress_percent: 进度百分比 (0-100)
            
        返回:
            (文件索引, 文件内偏移量)
        """
        if not files:
            return 0, 0

        # 进度为0%，从第一个文件开始
        if progress_percent <= 0:
            return 0, 0

        # 进度为100%，表示已完成
        if progress_percent >= 100:
            return len(files), 0

        # 计算每个文件的平均进度份额
        total_files = len(files)
        progress_per_file = 100.0 / total_files

        # 计算应该从哪个文件开始
        file_index = int(progress_percent / progress_per_file)

        # 确保索引不超出范围
        if file_index >= total_files:
            file_index = total_files - 1

        # 计算在该文件内的偏移量
        file_progress = progress_percent - (file_index * progress_per_file)
        file_progress_percent = file_progress / progress_per_file  # 0.0-1.0

        # 如果这个文件已经完成超过95%，则从下一个文件开始
        if file_progress_percent >= 0.95:
            file_index += 1
            file_offset = 0
        else:
            # 计算文件内的字节偏移量
            file_size = files[file_index]['size']
            file_offset = int(file_size * file_progress_percent)

        return file_index, file_offset

    def _setup_routes(self):
        """设置API路由"""

        @self.app.get("/", tags=["状态"])
        async def root():
            """服务器状态"""
            return {
                "status": "running",
                "name": "Game Download Server",
                "version": "4.0.0",
                "games_count": len(self.config.get('games', [])),
                "documentation": "/docs"
            }

        @self.app.get("/games", tags=["游戏"])
        async def list_games(api_key: Optional[str] = Header(None, alias="X-API-Key")):
            """获取游戏列表，包含configToClient"""
            if not self._verify_api_key(api_key):
                raise HTTPException(status_code=403, detail="无效的API密钥")

            games_list = []
            for game in self.config.get('games', []):
                game_info = {
                    'id': game.get('id'),
                    'name': game.get('name'),
                    'version': game.get('version'),
                    'description': game.get('description')
                }

                # 包含configToClient字段
                if 'configToClient' in game:
                    game_info['configToClient'] = game['configToClient']

                games_list.append(game_info)

            return {"games": games_list}

        @self.app.get("/games/{game_id}", response_model=GameFileList, tags=["游戏"])
        async def get_game_files(
                game_id: str,
                api_key: Optional[str] = Header(None, alias="X-API-Key")
        ):
            """获取游戏文件列表（树形结构），包含configToClient"""
            if not self._verify_api_key(api_key):
                raise HTTPException(status_code=403, detail="无效的API密钥")

            game_info = self._get_game_info(game_id)
            if not game_info:
                raise HTTPException(status_code=404, detail="游戏不存在")

            # 扫描文件
            files, file_tree = self._scan_game_files(game_info)
            total_size = sum(f['size'] for f in files)

            # 构建响应，包含configToClient
            response_data = {
                "game_id": game_id,
                "game_name": game_info.get('name'),
                "files": files,
                "total_files": len(files),
                "total_size": total_size,
                "file_tree": file_tree
            }

            # 如果游戏有configToClient，包含在响应中
            if 'configToClient' in game_info:
                response_data['configToClient'] = game_info['configToClient']

            return GameFileList(**response_data)

        @self.app.get("/games/{game_id}/start", response_model=DownloadStartInfo, tags=["下载"])
        async def get_download_start_info(
                game_id: str,
                progress: float = Query(0.0, ge=0.0, le=100.0, description="进度百分比(0-100)"),
                api_key: Optional[str] = Header(None, alias="X-API-Key")
        ):
            """
            根据进度百分比获取下载起始信息，包含configToClient
            """
            if not self._verify_api_key(api_key):
                raise HTTPException(status_code=403, detail="无效的API密钥")

            game_info = self._get_game_info(game_id)
            if not game_info:
                raise HTTPException(status_code=404, detail="游戏不存在")

            # 扫描文件
            files, _ = self._scan_game_files(game_info)

            if not files:
                response_data = {
                    "game_id": game_id,
                    "start_file_index": 0,
                    "start_file_path": "",
                    "start_file_offset": 0,
                    "files": [],
                    "message": "游戏目录为空"
                }

                # 包含configToClient
                if 'configToClient' in game_info:
                    response_data['configToClient'] = game_info['configToClient']

                return DownloadStartInfo(**response_data)

            # 计算起始文件索引和偏移量
            file_index, file_offset = self._get_start_file_index(files, progress)

            # 如果进度>=100%，表示已完成
            if progress >= 100 or file_index >= len(files):
                response_data = {
                    "game_id": game_id,
                    "start_file_index": len(files),
                    "start_file_path": "",
                    "start_file_offset": 0,
                    "files": files,
                    "message": "游戏已下载完成"
                }

                # 包含configToClient
                if 'configToClient' in game_info:
                    response_data['configToClient'] = game_info['configToClient']

                return DownloadStartInfo(**response_data)

            # 获取起始文件信息
            start_file = files[file_index]

            # 为每个文件添加进度信息
            total_files = len(files)
            for i, file in enumerate(files):
                file['progress_segment'] = {
                    'start_percent': i * (100.0 / total_files),
                    'end_percent': (i + 1) * (100.0 / total_files),
                    'file_index': i
                }

            message = f"进度{progress}%: 从第{file_index+1}个文件开始 ({start_file['path']})"
            if file_offset > 0:
                message += f", 从文件偏移{file_offset}字节处开始"

            response_data = {
                "game_id": game_id,
                "start_file_index": file_index,
                "start_file_path": start_file['path'],
                "start_file_offset": file_offset,
                "files": files,
                "message": message
            }

            # 包含configToClient
            if 'configToClient' in game_info:
                response_data['configToClient'] = game_info['configToClient']

            return DownloadStartInfo(**response_data)

        @self.app.get("/download/file/{game_id}/{file_path:path}", tags=["下载"])
        async def download_file(
                game_id: str,
                file_path: str,
                offset: int = Query(0, ge=0, description="文件内偏移量（字节）"),
                api_key: Optional[str] = Header(None, alias="X-API-Key")
        ):
            """下载游戏文件（支持从指定偏移量开始）"""
            if not self._verify_api_key(api_key):
                raise HTTPException(status_code=403, detail="无效的API密钥")

            game_info = self._get_game_info(game_id)
            if not game_info:
                raise HTTPException(status_code=404, detail="游戏不存在")

            # 构建完整文件路径
            game_dir = Path(game_info.get('directory'))
            full_path = game_dir / file_path

            # 安全检查：确保文件在游戏目录内
            try:
                full_path.relative_to(game_dir)
            except ValueError:
                raise HTTPException(status_code=403, detail="禁止访问此文件")

            if not full_path.exists() or not full_path.is_file():
                raise HTTPException(status_code=404, detail="文件不存在")

            # 获取文件信息
            file_size = full_path.stat().st_size

            # 如果偏移量超过文件大小，返回空
            if offset >= file_size:
                raise HTTPException(status_code=416, detail="偏移量超过文件大小")

            # 如果有偏移量，则从偏移量处开始下载
            if offset > 0:
                return await self._send_partial_file(full_path, offset, file_size)

            # 完整文件下载
            return FileResponse(
                path=full_path,
                filename=full_path.name,
                headers={
                    'Accept-Ranges': 'bytes',
                    'Content-Length': str(file_size),
                    'Content-Disposition': f'attachment; filename="{full_path.name}"'
                }
            )

        @self.app.get("/download/stream/{game_id}", tags=["下载"])
        async def stream_game_files(
                game_id: str,
                progress: float = Query(0.0, ge=0.0, le=100.0, description="进度百分比(0-100)"),
                chunk_size: int = Query(65536, ge=1024, le=1048576, description="块大小(字节)"),
                api_key: Optional[str] = Header(None, alias="X-API-Key")
        ):
            """
            流式下载游戏所有文件（从指定进度开始）
            返回一个连续的流，客户端不需要处理多个文件
            """
            if not self._verify_api_key(api_key):
                raise HTTPException(status_code=403, detail="无效的API密钥")

            game_info = self._get_game_info(game_id)
            if not game_info:
                raise HTTPException(status_code=404, detail="游戏不存在")

            # 扫描文件
            files, _ = self._scan_game_files(game_info)

            if not files:
                raise HTTPException(status_code=404, detail="游戏目录为空")

            # 计算起始文件索引和偏移量
            file_index, file_offset = self._get_start_file_index(files, progress)

            # 如果进度>=100%，返回空
            if progress >= 100 or file_index >= len(files):
                raise HTTPException(status_code=404, detail="游戏已下载完成")

            # 构建文件路径
            game_dir = Path(game_info.get('directory'))

            async def file_stream():
                """文件流生成器"""
                # 从起始文件开始
                for i in range(file_index, len(files)):
                    file_info = files[i]
                    file_path = game_dir / file_info['path']

                    if not file_path.exists():
                        continue

                    # 对于起始文件，从偏移量开始
                    start_offset = file_offset if i == file_index else 0

                    # 发送文件分隔标记
                    if i > file_index or start_offset > 0:
                        yield b'--FILE_BOUNDARY--\n'
                        yield f'Filename: {file_info["path"]}\n'.encode()
                        yield f'Size: {file_info["size"]}\n'.encode()
                        yield b'--FILE_CONTENT--\n'

                    # 读取并发送文件
                    async with aiofiles.open(file_path, 'rb') as f:
                        await f.seek(start_offset)

                        while True:
                            chunk = await f.read(chunk_size)
                            if not chunk:
                                break
                            yield chunk

                    # 重置偏移量，后续文件从0开始
                    file_offset = 0

            # 计算总大小
            total_size = sum(f['size'] for f in files[file_index:])
            if file_offset > 0 and file_index < len(files):
                total_size -= file_offset

            headers = {
                'Content-Type': 'application/octet-stream',
                'Content-Disposition': f'attachment; filename="{game_id}.stream"',
                'X-Game-Id': game_id,
                'X-Start-File-Index': str(file_index),
                'X-Start-File-Path': files[file_index]['path'] if file_index < len(files) else '',
                'X-Total-Files': str(len(files)),
                'X-Current-Progress': str(progress)
            }

            return StreamingResponse(
                file_stream(),
                headers=headers,
                media_type='application/octet-stream'
            )

    async def _send_partial_file(self, file_path: Path, offset: int, file_size: int):
        """发送文件的一部分（支持从偏移量开始）"""
        if offset >= file_size:
            raise HTTPException(status_code=416, detail="请求范围无效")

        async def file_iterator():
            """文件迭代器"""
            async with aiofiles.open(file_path, 'rb') as f:
                await f.seek(offset)
                remaining = file_size - offset
                chunk_size = 65536  # 64KB

                while remaining > 0:
                    read_size = min(chunk_size, remaining)
                    chunk = await f.read(read_size)
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk

        headers = {
            'Content-Range': f'bytes {offset}-{file_size-1}/{file_size}',
            'Accept-Ranges': 'bytes',
            'Content-Length': str(file_size - offset),
            'Content-Disposition': f'attachment; filename="{file_path.name}"'
        }

        return StreamingResponse(
            file_iterator(),
            status_code=206,  # Partial Content
            headers=headers,
            media_type='application/octet-stream'
        )

    def run(self):
        """运行服务器"""
        import uvicorn

        server_config = self.config.get('server', {})
        host = server_config.get('host', '0.0.0.0')
        port = server_config.get('port', 8000)

        logger.info(f"启动游戏下载服务器: http://{host}:{port}")
        logger.info(f"API文档地址: http://{host}:{port}/docs")
        logger.info(f"可用游戏数量: {len(self.config.get('games', []))}")
        logger.info(f"验证启用: {server_config.get('verify', True)}")

        uvicorn.run(
            self.app,
            host=host,
            port=port,
            log_level="info"
        )

def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='游戏资源下载服务器')
    parser.add_argument('--config', '-c', default='config.json', help='配置文件路径')
    parser.add_argument('--host', help='服务器主机地址')
    parser.add_argument('--port', '-p', type=int, help='服务器端口')

    args = parser.parse_args()

    try:
        # 创建服务器实例
        server = GameDownloadServer(args.config)

        # 覆盖配置
        if args.host:
            server.config['server']['host'] = args.host
        if args.port:
            server.config['server']['port'] = args.port

        # 运行服务器
        server.run()

    except KeyboardInterrupt:
        logger.info("服务器被用户中断")
    except Exception as e:
        logger.error(f"服务器运行出错: {e}")
        raise

if __name__ == "__main__":
    main()