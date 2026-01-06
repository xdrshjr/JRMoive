"""
Checkpoint Manager - 断点续传管理器
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging


class CheckpointManager:
    """断点续传管理器"""

    def __init__(self, checkpoint_dir: Path = None):
        """
        初始化检查点管理器

        Args:
            checkpoint_dir: 检查点存储目录
        """
        self.checkpoint_dir = checkpoint_dir or Path("./checkpoints")
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)

    def save_checkpoint(
        self,
        task_id: str,
        stage: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Path:
        """
        保存检查点

        Args:
            task_id: 任务ID
            stage: 当前阶段（如：parsing, image_generation, video_generation, composition）
            data: 要保存的数据
            metadata: 附加元数据

        Returns:
            检查点文件路径
        """
        checkpoint = {
            'task_id': task_id,
            'stage': stage,
            'timestamp': datetime.now().isoformat(),
            'data': data,
            'metadata': metadata or {}
        }

        checkpoint_file = self._get_checkpoint_path(task_id, stage)

        try:
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Checkpoint saved: {checkpoint_file}")
            return checkpoint_file

        except Exception as e:
            self.logger.error(f"Failed to save checkpoint: {e}")
            raise

    def load_checkpoint(
        self,
        task_id: str,
        stage: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        加载检查点

        Args:
            task_id: 任务ID
            stage: 阶段（None则加载最新）

        Returns:
            检查点数据，如果不存在则返回None
        """
        try:
            if stage:
                checkpoint_file = self._get_checkpoint_path(task_id, stage)
            else:
                # 查找最新的检查点
                checkpoint_file = self._find_latest_checkpoint(task_id)

            if not checkpoint_file or not checkpoint_file.exists():
                self.logger.info(f"No checkpoint found for task {task_id}")
                return None

            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                checkpoint = json.load(f)

            self.logger.info(f"Checkpoint loaded: {checkpoint_file}")
            return checkpoint

        except Exception as e:
            self.logger.error(f"Failed to load checkpoint: {e}")
            return None

    def list_checkpoints(self, task_id: str) -> List[Dict[str, Any]]:
        """
        列出任务的所有检查点

        Args:
            task_id: 任务ID

        Returns:
            检查点信息列表
        """
        checkpoints = []

        try:
            for checkpoint_file in self.checkpoint_dir.glob(f"{task_id}_*.json"):
                with open(checkpoint_file, 'r', encoding='utf-8') as f:
                    checkpoint = json.load(f)
                    checkpoints.append({
                        'file': str(checkpoint_file),
                        'stage': checkpoint['stage'],
                        'timestamp': checkpoint['timestamp']
                    })

            # 按时间排序
            checkpoints.sort(key=lambda x: x['timestamp'])

            return checkpoints

        except Exception as e:
            self.logger.error(f"Failed to list checkpoints: {e}")
            return []

    def checkpoint_exists(self, task_id: str, stage: Optional[str] = None) -> bool:
        """
        检查检查点是否存在

        Args:
            task_id: 任务ID
            stage: 阶段（None则检查是否有任何检查点）

        Returns:
            是否存在
        """
        if stage:
            checkpoint_file = self._get_checkpoint_path(task_id, stage)
            return checkpoint_file.exists()
        else:
            # 检查是否有任何检查点
            return len(list(self.checkpoint_dir.glob(f"{task_id}_*.json"))) > 0

    def clear_checkpoints(self, task_id: str, stage: Optional[str] = None):
        """
        清除检查点

        Args:
            task_id: 任务ID
            stage: 阶段（None则清除所有检查点）
        """
        try:
            if stage:
                # 清除特定阶段的检查点
                checkpoint_file = self._get_checkpoint_path(task_id, stage)
                if checkpoint_file.exists():
                    checkpoint_file.unlink()
                    self.logger.info(f"Checkpoint removed: {checkpoint_file}")
            else:
                # 清除所有检查点
                count = 0
                for checkpoint_file in self.checkpoint_dir.glob(f"{task_id}_*.json"):
                    checkpoint_file.unlink()
                    count += 1

                self.logger.info(f"Cleared {count} checkpoints for task {task_id}")

        except Exception as e:
            self.logger.error(f"Failed to clear checkpoints: {e}")

    def get_resume_stage(self, task_id: str) -> Optional[str]:
        """
        获取可恢复的阶段

        Args:
            task_id: 任务ID

        Returns:
            下一个需要执行的阶段，如果没有检查点则返回None
        """
        checkpoints = self.list_checkpoints(task_id)

        if not checkpoints:
            return None

        # 获取最后完成的阶段
        latest_checkpoint = checkpoints[-1]
        latest_stage = latest_checkpoint['stage']

        # 定义阶段顺序
        stages = ['parsing', 'image_generation', 'video_generation', 'composition']

        try:
            current_index = stages.index(latest_stage)
            # 返回下一个阶段
            if current_index + 1 < len(stages):
                return stages[current_index + 1]
            else:
                # 已完成所有阶段
                return 'completed'
        except ValueError:
            # 未知阶段
            return None

    def _get_checkpoint_path(self, task_id: str, stage: str) -> Path:
        """
        获取检查点文件路径

        Args:
            task_id: 任务ID
            stage: 阶段

        Returns:
            检查点文件路径
        """
        return self.checkpoint_dir / f"{task_id}_{stage}.json"

    def _find_latest_checkpoint(self, task_id: str) -> Optional[Path]:
        """
        查找最新的检查点文件

        Args:
            task_id: 任务ID

        Returns:
            最新的检查点文件路径，如果不存在则返回None
        """
        checkpoints = list(self.checkpoint_dir.glob(f"{task_id}_*.json"))

        if not checkpoints:
            return None

        # 按修改时间排序，返回最新的
        return max(checkpoints, key=lambda p: p.stat().st_mtime)

    def archive_checkpoint(self, task_id: str, archive_dir: Optional[Path] = None):
        """
        归档检查点（移动到归档目录）

        Args:
            task_id: 任务ID
            archive_dir: 归档目录
        """
        if archive_dir is None:
            archive_dir = self.checkpoint_dir / "archive"

        archive_dir.mkdir(parents=True, exist_ok=True)

        try:
            count = 0
            for checkpoint_file in self.checkpoint_dir.glob(f"{task_id}_*.json"):
                archive_path = archive_dir / checkpoint_file.name
                checkpoint_file.rename(archive_path)
                count += 1

            self.logger.info(f"Archived {count} checkpoints for task {task_id}")

        except Exception as e:
            self.logger.error(f"Failed to archive checkpoints: {e}")

    def restore_from_archive(self, task_id: str, archive_dir: Optional[Path] = None):
        """
        从归档恢复检查点

        Args:
            task_id: 任务ID
            archive_dir: 归档目录
        """
        if archive_dir is None:
            archive_dir = self.checkpoint_dir / "archive"

        if not archive_dir.exists():
            self.logger.warning(f"Archive directory does not exist: {archive_dir}")
            return

        try:
            count = 0
            for checkpoint_file in archive_dir.glob(f"{task_id}_*.json"):
                restore_path = self.checkpoint_dir / checkpoint_file.name
                checkpoint_file.rename(restore_path)
                count += 1

            self.logger.info(f"Restored {count} checkpoints for task {task_id}")

        except Exception as e:
            self.logger.error(f"Failed to restore checkpoints: {e}")

    def get_checkpoint_size(self, task_id: str) -> int:
        """
        获取检查点占用的磁盘空间

        Args:
            task_id: 任务ID

        Returns:
            字节数
        """
        total_size = 0

        for checkpoint_file in self.checkpoint_dir.glob(f"{task_id}_*.json"):
            total_size += checkpoint_file.stat().st_size

        return total_size

    def cleanup_old_checkpoints(self, days: int = 7):
        """
        清理旧检查点

        Args:
            days: 保留天数，超过此天数的检查点将被删除
        """
        import time

        cutoff_time = time.time() - (days * 24 * 60 * 60)
        count = 0

        try:
            for checkpoint_file in self.checkpoint_dir.glob("*.json"):
                if checkpoint_file.stat().st_mtime < cutoff_time:
                    checkpoint_file.unlink()
                    count += 1

            self.logger.info(f"Cleaned up {count} old checkpoints (>{days} days)")

        except Exception as e:
            self.logger.error(f"Failed to cleanup old checkpoints: {e}")
