"""Orchestrator 노드 — 시나리오의 sub-task를 순차 실행한다.

데모용 스텁. 실제 구현은 kist-drl-g1-cortex 레포에 있다.

@relation(SYS-REQ-44, scope=file)
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, String

from cortex_msgs.msg import ActionCmd, Subtask, TaskStatus, Verdict


class OrchestratorNode(Node):
    """open-loop 시나리오 상태머신 (IDLE ↔ RUNNING).

    ICD-64/66 을 구독하고 ICD-65/67/68/69 를 발행한다.
    """

    def __init__(self) -> None:
        super().__init__("orchestrator_node")

        self._scenario = None
        self._index = 0
        self._latest_verdict: Verdict | None = None

        self.create_subscription(String, "/cortex/stt/transcript", self._on_stt, 10)
        self.create_subscription(Verdict, "/cortex/critic/verdict", self._on_verdict, 10)

        self._subtask_pub = self.create_publisher(Subtask, "/cortex/active_subtask", 10)
        self._status_pub = self.create_publisher(TaskStatus, "/cortex/task_status", 10)
        self._say_pub = self.create_publisher(ActionCmd, "/cortex/tts/say", 10)
        self._stop_pub = self.create_publisher(Bool, "/cortex/tts/stop", 10)

        self.create_timer(0.1, self._tick)

    # @relation(SYS-REQ-44, scope=function)
    def _on_stt(self, msg: String) -> None:
        """트리거 키워드와 매칭되면 시나리오를 시작한다."""
        if self._scenario is None:
            return
        if self._scenario.trigger in msg.data:
            self._index = 0
            self._enter_subtask(self._index)

    def _on_verdict(self, msg: Verdict) -> None:
        """무거운 추론이 tick을 막지 않도록 최신 판정만 캐시한다."""
        self._latest_verdict = msg

    # sub-task 전이 판정 루프.
    # @relation(SYS-REQ-44, scope=range_start)
    def _tick(self) -> None:
        if self._scenario is None:
            return

        current = self._scenario.subtasks[self._index]
        verdict = self._latest_verdict

        if verdict is not None and verdict.subtask_id == current.id and verdict.passed:
            self._latest_verdict = None
            self._index += 1
            if self._index >= len(self._scenario.subtasks):
                self._publish_status("SUCCEEDED")
                self._scenario = None
            else:
                self._enter_subtask(self._index)
    # @relation(SYS-REQ-44, scope=range_end)

    def _enter_subtask(self, index: int) -> None:
        subtask = self._scenario.subtasks[index]
        self._subtask_pub.publish(
            Subtask(
                id=subtask.id,
                success_check=subtask.success_check,
                timeout_sec=subtask.timeout_sec,
            )
        )
        self._publish_status("RUNNING")

    # GUI로 진행 상황을 통지한다 (ICD-67).
    # @relation(SYS-REQ-41, scope=function)
    def _publish_status(self, state: str) -> None:
        self._status_pub.publish(
            TaskStatus(
                task_name=self._scenario.name,
                current_subtask=self._scenario.subtasks[self._index].id,
                subtask_index=self._index,
                subtask_count=len(self._scenario.subtasks),
                state=state,
            )
        )


def main() -> None:
    rclpy.init()
    rclpy.spin(OrchestratorNode())
    rclpy.shutdown()
