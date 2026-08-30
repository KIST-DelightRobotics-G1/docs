"""VLM 노드 — 카메라 프레임으로 sub-task 성공 여부를 판정한다.

데모용 스텁. 실제 구현은 kist-drl-g1-cortex 레포에 있다.

@relation(SYS-REQ-44, scope=file)
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage

from cortex_msgs.msg import Subtask, Verdict


class VlmNode(Node):
    """클라우드 VLM 판정기 (ICD-65 구독 → ICD-66 발행, ICD-71 로 추론 요청)."""

    def __init__(self) -> None:
        super().__init__("vlm_node")

        self._active: Subtask | None = None
        self._latest_frame: CompressedImage | None = None

        self.create_subscription(Subtask, "/cortex/active_subtask", self._on_subtask, 10)
        self.create_subscription(
            CompressedImage, "/bridge/sensors/color/compressed", self._on_frame, 1
        )
        self._pub = self.create_publisher(Verdict, "/cortex/critic/verdict", 10)

        self.create_timer(1.0, self._evaluate)

    def _on_subtask(self, msg: Subtask) -> None:
        self._active = msg

    def _on_frame(self, msg: CompressedImage) -> None:
        self._latest_frame = msg

    # @relation(SYS-REQ-44, scope=function)
    def _evaluate(self) -> None:
        """활성 sub-task의 success_check 기준으로 최신 프레임을 판정한다."""
        if self._active is None or self._latest_frame is None:
            return

        passed = self._query_vlm(self._latest_frame, self._active.success_check)
        self._pub.publish(Verdict(subtask_id=self._active.id, passed=passed))


def main() -> None:
    rclpy.init()
    rclpy.spin(VlmNode())
    rclpy.shutdown()
