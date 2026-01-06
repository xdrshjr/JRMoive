"""Base Agent and supporting infrastructure classes"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Callable, List, Type
from datetime import datetime
from enum import Enum
from dataclasses import dataclass
import logging
import asyncio
import traceback


class AgentState(Enum):
    """Agent状态枚举"""
    IDLE = "idle"               # 空闲
    RUNNING = "running"         # 运行中
    WAITING = "waiting"         # 等待中
    COMPLETED = "completed"     # 已完成
    ERROR = "error"             # 错误状态


class WorkflowState(Enum):
    """工作流状态"""
    INITIALIZED = "initialized"           # 已初始化
    PARSING_SCRIPT = "parsing_script"     # 解析剧本中
    GENERATING_IMAGES = "generating_images"  # 生成图片中
    GENERATING_VIDEOS = "generating_videos"  # 生成视频中
    COMPOSING_VIDEO = "composing_video"   # 合成视频中
    POST_PROCESSING = "post_processing"   # 后期处理中
    COMPLETED = "completed"               # 已完成
    FAILED = "failed"                     # 失败


@dataclass
class AgentMessage:
    """Agent间通信的消息格式"""
    sender_id: str          # 发送者Agent ID
    receiver_id: str        # 接收者Agent ID
    message_type: str       # 消息类型（task/result/error/status）
    payload: Any            # 消息内容
    timestamp: datetime     # 时间戳
    correlation_id: str     # 关联ID（用于追踪请求链路）


class BaseAgent(ABC):
    """Agent基类，定义所有Agent的通用接口"""

    def __init__(self, agent_id: str, config: Dict[str, Any]):
        """
        初始化Agent

        Args:
            agent_id: Agent唯一标识符
            config: Agent配置参数
        """
        self.agent_id = agent_id
        self.config = config
        self.logger = logging.getLogger(f"Agent.{agent_id}")
        self.state = AgentState.IDLE
        self.created_at = datetime.now()

    @abstractmethod
    async def execute(self, input_data: Any) -> Any:
        """
        执行Agent的核心任务

        Args:
            input_data: 输入数据

        Returns:
            处理后的输出数据
        """
        pass

    @abstractmethod
    async def validate_input(self, input_data: Any) -> bool:
        """
        验证输入数据的有效性

        Args:
            input_data: 待验证的输入数据

        Returns:
            验证是否通过
        """
        pass

    async def on_error(self, error: Exception) -> None:
        """
        错误处理钩子

        Args:
            error: 发生的异常
        """
        self.logger.error(f"Agent {self.agent_id} encountered error: {str(error)}")
        self.state = AgentState.ERROR

    async def on_complete(self, result: Any) -> None:
        """
        任务完成钩子

        Args:
            result: 执行结果
        """
        self.logger.info(f"Agent {self.agent_id} completed successfully")
        self.state = AgentState.COMPLETED


class MessageBus:
    """消息总线，负责Agent间的消息传递"""

    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}
        self.message_queue = asyncio.Queue()
        self._running = False

    def subscribe(self, message_type: str, callback: Callable):
        """
        订阅特定类型的消息

        Args:
            message_type: 消息类型
            callback: 回调函数
        """
        if message_type not in self.subscribers:
            self.subscribers[message_type] = []
        self.subscribers[message_type].append(callback)

    async def publish(self, message: AgentMessage):
        """
        发布消息

        Args:
            message: 要发布的消息
        """
        await self.message_queue.put(message)

    async def start_processing(self):
        """启动消息处理循环"""
        self._running = True
        while self._running:
            try:
                message = await asyncio.wait_for(self.message_queue.get(), timeout=1.0)
                if message.message_type in self.subscribers:
                    for callback in self.subscribers[message.message_type]:
                        await callback(message)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logging.error(f"Error processing message: {e}")

    def stop_processing(self):
        """停止消息处理"""
        self._running = False


class WorkflowStateManager:
    """工作流状态管理器"""

    def __init__(self):
        self.current_state = WorkflowState.INITIALIZED
        self.state_history = [(WorkflowState.INITIALIZED, datetime.now())]
        self.checkpoint_data = {}

    def transition_to(self, new_state: WorkflowState,
                     checkpoint: Optional[Dict] = None):
        """
        状态转换

        Args:
            new_state: 新状态
            checkpoint: 检查点数据（用于断点续传）
        """
        if self._is_valid_transition(self.current_state, new_state):
            self.current_state = new_state
            self.state_history.append((new_state, datetime.now()))

            if checkpoint:
                self.checkpoint_data[new_state.value] = checkpoint
        else:
            raise ValueError(
                f"Invalid state transition: {self.current_state} -> {new_state}"
            )

    def _is_valid_transition(self, from_state: WorkflowState,
                            to_state: WorkflowState) -> bool:
        """验证状态转换是否合法"""
        valid_transitions = {
            WorkflowState.INITIALIZED: [WorkflowState.PARSING_SCRIPT],
            WorkflowState.PARSING_SCRIPT: [
                WorkflowState.GENERATING_IMAGES,
                WorkflowState.FAILED
            ],
            WorkflowState.GENERATING_IMAGES: [
                WorkflowState.GENERATING_VIDEOS,
                WorkflowState.FAILED
            ],
            WorkflowState.GENERATING_VIDEOS: [
                WorkflowState.COMPOSING_VIDEO,
                WorkflowState.FAILED
            ],
            WorkflowState.COMPOSING_VIDEO: [
                WorkflowState.POST_PROCESSING,
                WorkflowState.FAILED
            ],
            WorkflowState.POST_PROCESSING: [
                WorkflowState.COMPLETED,
                WorkflowState.FAILED
            ],
        }

        return to_state in valid_transitions.get(from_state, [])

    def get_checkpoint(self, state: WorkflowState) -> Optional[Dict]:
        """获取特定状态的检查点数据"""
        return self.checkpoint_data.get(state.value)


class ErrorHandler:
    """统一错误处理器"""

    def __init__(self):
        self.error_handlers: Dict[Type[Exception], Callable] = {}
        self.retry_config = {
            'max_retries': 3,
            'backoff_factor': 2,
            'retry_exceptions': [ConnectionError, TimeoutError]
        }

    def register_handler(self, exception_type: Type[Exception],
                        handler: Callable):
        """
        注册特定异常的处理器

        Args:
            exception_type: 异常类型
            handler: 处理函数
        """
        self.error_handlers[exception_type] = handler

    async def handle_error(self, error: Exception,
                          context: Optional[Dict] = None) -> Any:
        """
        处理错误

        Args:
            error: 发生的异常
            context: 错误上下文信息

        Returns:
            处理结果（如重试、降级方案等）
        """
        error_type = type(error)

        # 查找匹配的错误处理器
        if error_type in self.error_handlers:
            return await self.error_handlers[error_type](error, context)

        # 默认错误处理：记录日志并抛出
        logging.error(f"Unhandled error: {error}")
        logging.error(f"Traceback: {traceback.format_exc()}")
        logging.error(f"Context: {context}")
        raise error
