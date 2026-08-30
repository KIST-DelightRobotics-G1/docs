"""TTS 노드 — 텍스트를 한국어 음성으로 합성한다.

데모용 스텁. 실제 구현은 kist-drl-g1-cortex 레포에 있다.

@relation(SYS-REQ-29, scope=file)
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool

from cortex_msgs.msg import ActionCmd
from g1_onboard_msgs.msg import AudioPCM

CLOVA_SAMPLE_RATE = 24000
TARGET_SAMPLE_RATE = 16000


class TtsNode(Node):
    """Naver CLOVA TTS 클라이언트.

    ICD-68 (say) / ICD-69 (stop) 을 구독하고 ICD-8 (audio out) 을 발행한다.
    """

    def __init__(self) -> None:
        super().__init__("tts_node")

        self._task = None

        self.create_subscription(ActionCmd, "/cortex/tts/say", self._on_say, 10)
        self.create_subscription(Bool, "/cortex/tts/stop", self._on_stop, 10)
        self._pub = self.create_publisher(AudioPCM, "/bridge/cmd/audio_out", 10)

    # @relation(SYS-REQ-29, scope=function)
    def _on_say(self, msg: ActionCmd) -> None:
        """CLOVA로 합성한 뒤 16 kHz로 resample하여 speaker_node에 발행한다."""
        pcm24 = self._clova_synthesize(msg.text)
        pcm16 = self._resample(pcm24, CLOVA_SAMPLE_RATE, TARGET_SAMPLE_RATE)
        self._pub.publish(AudioPCM(data=pcm16, sample_rate=TARGET_SAMPLE_RATE))

    # barge-in: 진행 중인 합성 태스크를 취소한다.
    # 이미 스피커로 나간 오디오는 회수할 수 없다 (fire-and-forget).
    # @relation(SYS-REQ-29, scope=function)
    def _on_stop(self, msg: Bool) -> None:
        if msg.data and self._task is not None:
            self._task.cancel()
            self._task = None


def main() -> None:
    rclpy.init()
    rclpy.spin(TtsNode())
    rclpy.shutdown()
