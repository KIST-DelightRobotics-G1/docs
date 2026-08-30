/**
 * 마이크 퍼블리셔 — ALSA 캡처를 DDS로 발행한다 (ICD-3).
 *
 * 데모용 스텁. 실제 구현은 kist-ext-sensor-io 레포에 있다.
 *
 * @relation(SYS-REQ-42, scope=file)
 */

#include <alsa/asoundlib.h>

#include <cstdint>
#include <vector>

namespace kist::ext_sensor_io {

constexpr uint32_t kSampleRate = 16000;
constexpr uint8_t kChannels = 1;
constexpr uint32_t kChunkMs = 100;

/// 100 ms 단위로 PCM을 캡처하여 rt/kist/mic/audio 로 발행한다.
/// @relation(SYS-REQ-42, scope=class)
class MicPublisher {
 public:
  MicPublisher();

  void Spin();

 private:
  // @relation(SYS-REQ-42, scope=function)
  void CaptureChunk(std::vector<int16_t>* out) {
    const snd_pcm_uframes_t frames = kSampleRate * kChunkMs / 1000;
    out->resize(frames * kChannels);
    snd_pcm_readi(pcm_, out->data(), frames);
  }

  void Publish(const std::vector<int16_t>& pcm);

  snd_pcm_t* pcm_ = nullptr;
  uint32_t seq_ = 0;
};

}  // namespace kist::ext_sensor_io
