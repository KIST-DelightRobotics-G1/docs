"""GUI 브리지 노드 — 상태와 카메라 프레임을 WebSocket으로 재발행한다.

데모용 스텁. 실제 구현은 kist-drl-g1-cortex 레포에 있다.

@relation(SYS-REQ-41, scope=file)
"""

import asyncio

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage

from cortex_msgs.msg import TaskStatus

WS_PORT = 8081
TARGET_FPS = 15


class GuiBridgeNode(Node):
    """ICD-67 + ICD-62 를 구독하여 ICD-55 (WebSocket) 로 재발행한다."""

    def __init__(self) -> None:
        super().__init__("gui_bridge_node")

        self._status: TaskStatus | None = None
        self._frame: bytes | None = None
        self._clients: set = set()

        self.create_subscription(TaskStatus, "/cortex/task_status", self._on_status, 10)
        self.create_subscription(
            CompressedImage, "/bridge/sensors/color/compressed", self._on_frame, 1
        )

    def _on_status(self, msg: TaskStatus) -> None:
        self._status = msg

    def _on_frame(self, msg: CompressedImage) -> None:
        # latest-value cell: 느린 client가 파이프라인을 막지 않도록 최신 프레임만 유지한다.
        self._frame = bytes(msg.data)

    # 매 tick 각 client에 text(JSON) 후 binary(JPEG) 순으로 전송한다.
    # 이전 broadcast가 끝나지 않았으면 프레임을 drop한다 (latest-wins 백프레셔).
    # @relation(SYS-REQ-41, scope=range_start)
    async def _broadcast(self) -> None:
        while True:
            await asyncio.sleep(1.0 / TARGET_FPS)
            if not self._clients:
                continue

            payload = self._status_json()
            for client in list(self._clients):
                try:
                    await client.send(payload)
                    if self._frame is not None:
                        await client.send(self._frame)
                except asyncio.TimeoutError:
                    self._clients.discard(client)
    # @relation(SYS-REQ-41, scope=range_end)

    def _status_json(self) -> str:
        if self._status is None:
            return '{"scenario": null, "subtask": null, "state": "idle"}'
        return (
            f'{{"scenario": "{self._status.task_name}", '
            f'"subtask": {{"name": "{self._status.current_subtask}", '
            f'"i": {self._status.subtask_index}, "n": {self._status.subtask_count}}}, '
            f'"state": "active"}}'
        )


def main() -> None:
    rclpy.init()
    rclpy.spin(GuiBridgeNode())
    rclpy.shutdown()
