"""
Unit tests for base_agent module
"""
import pytest
import asyncio
from agents.base_agent import (
    BaseAgent,
    AgentState,
    WorkflowState,
    WorkflowStateManager,
    MessageBus,
    AgentMessage,
    ErrorHandler
)
from datetime import datetime


class DummyAgent(BaseAgent):
    """测试用的虚拟Agent"""

    async def execute(self, input_data):
        """执行测试任务"""
        return f"Processed: {input_data}"

    async def validate_input(self, input_data):
        """验证输入"""
        return input_data is not None


@pytest.mark.asyncio
async def test_base_agent_creation():
    """测试Agent创建"""
    agent = DummyAgent("test_agent", {"key": "value"})
    assert agent.agent_id == "test_agent"
    assert agent.state == AgentState.IDLE
    assert agent.config["key"] == "value"


@pytest.mark.asyncio
async def test_agent_execute():
    """测试Agent执行"""
    agent = DummyAgent("test_agent", {})
    result = await agent.execute("test_data")
    assert result == "Processed: test_data"


@pytest.mark.asyncio
async def test_agent_validate_input():
    """测试输入验证"""
    agent = DummyAgent("test_agent", {})
    assert await agent.validate_input("valid") == True
    assert await agent.validate_input(None) == False


def test_workflow_state_manager():
    """测试工作流状态管理"""
    manager = WorkflowStateManager()

    # 初始状态
    assert manager.current_state == WorkflowState.INITIALIZED

    # 有效状态转换
    manager.transition_to(WorkflowState.PARSING_SCRIPT)
    assert manager.current_state == WorkflowState.PARSING_SCRIPT

    # 无效状态转换应该抛出异常
    with pytest.raises(ValueError):
        manager.transition_to(WorkflowState.COMPLETED)


def test_workflow_state_checkpoint():
    """测试检查点功能"""
    manager = WorkflowStateManager()

    checkpoint_data = {"scene_count": 5, "progress": 0.5}
    manager.transition_to(
        WorkflowState.PARSING_SCRIPT,
        checkpoint=checkpoint_data
    )

    retrieved = manager.get_checkpoint(WorkflowState.PARSING_SCRIPT)
    assert retrieved == checkpoint_data


@pytest.mark.asyncio
async def test_message_bus():
    """测试消息总线"""
    bus = MessageBus()
    received_messages = []

    async def callback(message: AgentMessage):
        received_messages.append(message)

    # 订阅消息
    bus.subscribe("test_type", callback)

    # 发布消息
    message = AgentMessage(
        sender_id="agent1",
        receiver_id="agent2",
        message_type="test_type",
        payload="test_data",
        timestamp=datetime.now(),
        correlation_id="test_correlation"
    )

    await bus.publish(message)

    # 手动处理一条消息
    msg = await bus.message_queue.get()
    for cb in bus.subscribers["test_type"]:
        await cb(msg)

    assert len(received_messages) == 1
    assert received_messages[0].payload == "test_data"


@pytest.mark.asyncio
async def test_error_handler():
    """测试错误处理器"""
    handler = ErrorHandler()

    # 注册错误处理函数
    async def handle_value_error(error, context):
        return "handled"

    handler.register_handler(ValueError, handle_value_error)

    # 测试已注册的错误
    result = await handler.handle_error(ValueError("test"), {})
    assert result == "handled"

    # 测试未注册的错误应该重新抛出
    with pytest.raises(TypeError):
        await handler.handle_error(TypeError("test"), {})
