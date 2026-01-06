"""分镜优化器 - 自动优化镜头设计"""

from typing import List
from models.script_models import Scene, ShotType, CameraMovement


class StoryboardOptimizer:
    """分镜优化器 - 自动优化镜头设计"""

    @staticmethod
    def optimize_shot_sequence(scenes: List[Scene]) -> List[Scene]:
        """
        优化镜头序列，避免单调

        策略:
        1. 避免连续多个相同镜头类型
        2. 重要对话使用特写
        3. 场景转换时使用全景

        Args:
            scenes: 场景列表

        Returns:
            优化后的场景列表
        """
        if len(scenes) <= 1:
            return scenes

        optimized = scenes.copy()

        for i in range(1, len(optimized)):
            prev_scene = optimized[i - 1]
            curr_scene = optimized[i]

            # 避免连续相同镜头
            if prev_scene.shot_type == curr_scene.shot_type:
                curr_scene.shot_type = StoryboardOptimizer._get_alternate_shot(
                    curr_scene.shot_type
                )

            # 对话场景优化
            if curr_scene.dialogues:
                if len(curr_scene.dialogues) > 2:  # 多轮对话使用特写
                    curr_scene.shot_type = ShotType.CLOSE_UP

            # 场景转换使用全景
            if prev_scene.location != curr_scene.location:
                curr_scene.shot_type = ShotType.LONG_SHOT

        return optimized

    @staticmethod
    def _get_alternate_shot(current: ShotType) -> ShotType:
        """获取交替镜头类型"""
        alternates = {
            ShotType.CLOSE_UP: ShotType.MEDIUM_SHOT,
            ShotType.MEDIUM_SHOT: ShotType.CLOSE_UP,
            ShotType.LONG_SHOT: ShotType.MEDIUM_SHOT,
            ShotType.FULL_SHOT: ShotType.MEDIUM_SHOT,
            ShotType.EXTREME_CLOSE_UP: ShotType.MEDIUM_SHOT,
            ShotType.OVER_SHOULDER: ShotType.CLOSE_UP,
        }
        return alternates.get(current, ShotType.MEDIUM_SHOT)

    @staticmethod
    def adjust_scene_durations(scenes: List[Scene],
                              target_total: float) -> List[Scene]:
        """
        调整场景时长以匹配目标总时长

        Args:
            scenes: 场景列表
            target_total: 目标总时长（秒）

        Returns:
            调整后的场景列表
        """
        if not scenes:
            return scenes

        current_total = sum(s.duration for s in scenes)
        if current_total == 0:
            return scenes

        scale_factor = target_total / current_total

        for scene in scenes:
            # 确保时长在合法范围内 (1-10秒)
            scene.duration = max(1.0, min(10.0, scene.duration * scale_factor))

        return scenes

    @staticmethod
    def add_camera_dynamics(scenes: List[Scene]) -> List[Scene]:
        """
        为场景添加摄像机动态

        Args:
            scenes: 场景列表

        Returns:
            添加摄像机运动后的场景列表
        """
        for i, scene in enumerate(scenes):
            # 如果场景已有运镜设置，跳过
            if scene.camera_movement != CameraMovement.STATIC:
                continue

            # 根据场景特点添加运镜
            if scene.action and any(keyword in scene.action for keyword in ['走', '跑', '移动', '追']):
                scene.camera_movement = CameraMovement.TRACKING

            elif scene.shot_type == ShotType.LONG_SHOT:
                scene.camera_movement = CameraMovement.PAN

            elif len(scene.dialogues) > 0 and scene.shot_type == ShotType.CLOSE_UP:
                scene.camera_movement = CameraMovement.ZOOM

        return scenes

    @staticmethod
    def balance_shot_types(scenes: List[Scene]) -> List[Scene]:
        """
        平衡镜头类型分布，避免某种镜头类型过多

        Args:
            scenes: 场景列表

        Returns:
            平衡后的场景列表
        """
        if len(scenes) < 3:
            return scenes

        # 统计每种镜头类型的数量
        shot_counts = {}
        for scene in scenes:
            shot_type = scene.shot_type
            shot_counts[shot_type] = shot_counts.get(shot_type, 0) + 1

        # 如果某种镜头过多（超过50%），进行调整
        total_scenes = len(scenes)
        for shot_type, count in shot_counts.items():
            if count > total_scenes * 0.5:
                # 找到使用该镜头类型的场景，每隔一个调整一次
                adjusted = 0
                for i, scene in enumerate(scenes):
                    if scene.shot_type == shot_type and adjusted % 2 == 0:
                        scene.shot_type = StoryboardOptimizer._get_alternate_shot(shot_type)
                        adjusted += 1

        return scenes
