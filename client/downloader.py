# downloader.py
import os
import json
from pathlib import Path
from urllib.parse import quote
import requests

def download_game(
        server_url: str,
        api_key: str,
        game: dict,
        install_dir: Path,
        progress_callback=None,
        status_callback=None
):
    headers = {"X-API-Key": api_key}
    game_id = game["id"]
    install_dir = Path(install_dir)
    install_dir.mkdir(parents=True, exist_ok=True)

    # === 1. 获取完整游戏信息（含所有文件）===
    resp = requests.get(f"{server_url}/games/{game_id}", headers=headers, timeout=10)
    resp.raise_for_status()
    game_data = resp.json()
    files = game_data["files"]
    total_size = sum(f["size"] for f in files)

    if total_size == 0:
        raise ValueError("游戏总大小为0")

    # === 2. 加载已有下载进度 ===
    progress_file = install_dir / ".download_progress.json"
    if progress_file.exists():
        try:
            with open(progress_file, "r", encoding="utf-8") as f:
                file_status = json.load(f)
        except:
            file_status = {}
    else:
        file_status = {}

    # 初始化未记录的文件
    for f in files:
        path = f["path"]
        if path not in file_status:
            file_status[path] = {"size": f["size"], "downloaded": 0}

    # === 3. 辅助函数：获取已下载总量 ===
    def get_downloaded_total():
        return sum(info["downloaded"] for info in file_status.values())

    # 初始进度
    downloaded_so_far = get_downloaded_total()
    if progress_callback:
        progress_callback(downloaded_so_far, total_size)

    # === 4. 逐个下载文件 ===
    for file_info in files:
        remote_path = file_info["path"]
        local_path = install_dir / remote_path
        local_path.parent.mkdir(parents=True, exist_ok=True)

        already = file_status[remote_path]["downloaded"]
        if already >= file_info["size"]:
            continue  # 已完成

        if status_callback:
            status_callback(f"下载: {remote_path}")

        # 带偏移量请求
        url = f"{server_url}/download/file/{game_id}/{quote(remote_path)}?offset={already}"
        with requests.get(url, headers=headers, stream=True, timeout=30) as r:
            r.raise_for_status()
            with open(local_path, "ab") as f_out:
                for chunk in r.iter_content(chunk_size=64 * 1024):
                    if chunk:
                        f_out.write(chunk)
                        file_status[remote_path]["downloaded"] += len(chunk)
                        # 👇 上报整体进度
                        if progress_callback:
                            progress_callback(get_downloaded_total(), total_size)

        # 保存进度（即使单个文件完成也保存）
        with open(progress_file, "w", encoding="utf-8") as f:
            json.dump(file_status, f, indent=2, ensure_ascii=False)

    # === 5. 所有文件下载完成，删除进度文件 ===
    if progress_file.exists():
        try:
            progress_file.unlink()  # 安全删除 .download_progress.json
        except Exception as e:
            # 可选：打印警告但不中断流程
            if status_callback:
                status_callback(f"⚠️ 无法清理进度文件: {e}")

    if status_callback:
        status_callback("✅ 下载完成")