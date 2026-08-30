"""STT 노드 — 마이크 오디오를 텍스트로 변환한다.

데모용 스텁. 실제 구현은 kist-drl-g1-cortex 레포에 있다.

@relation(SYS-REQ-27, scope=file)
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from g1_onboard_msgs.msg import AudioPCM, SpeakerState


class SttNode(Node):
    """Google Cloud STT 스트리밍 인식기.

    ICD-3 (mic audio) 를 구독하고 ICD-64 (transcript) 를 발행한다.
    """

    def __init__(self) -> None:
        super().__init__("stt_node")

        self._muted = False

        self.create_subscription(
            AudioPCM, "/bridge/sensors/audio_pcm", self._on_audio, 10
        )
        self.create_subscription(
            SpeakerState, "/bridge/audio/speaker_state", self._on_speaker_state, 10
        )
        self._pub = self.create_publisher(String, "/cortex/stt/transcript", 10)

    # @relation(SYS-REQ-27, scope=function)
    def _on_audio(self, msg: AudioPCM) -> None:
        """마이크 청크를 인식기로 흘려보낸다. 뮤트 중이면 폐기한다."""
        if self._muted:
            return
        self._stream.write(msg.data)

    # 에코 캔슬: 스피커 재생 중에는 마이크 입력을 차단한다.
    # @relation(SYS-REQ-27, scope=range_start)
    def _on_speaker_state(self, msg: SpeakerState) -> None:
        if msg.playing and not self._muted:
            self.get_logger().info("speaker playing -> mic muted")
            self._muted = True
        elif not msg.playing and self._muted:
            self.get_logger().info("speaker idle -> mic unmuted")
            self._muted = False
    # @relation(SYS-REQ-27, scope=range_end)

    def _publish_transcript(self, text: str) -> None:
        """is_final 문장만 orchestrator로 전달한다 (ICD-64)."""
        self._pub.publish(String(data=text))


def main() -> None:
    rclpy.init()
    rclpy.spin(SttNode())
    rclpy.shutdown()
