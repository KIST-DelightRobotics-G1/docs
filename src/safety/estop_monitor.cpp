/**
 * E-STOP 모니터 — 관절 명령 이상을 감지하여 긴급정지를 발효한다.
 *
 * 데모용 스텁. 기능 제어 레이어(gearsonic WBC)와 독립된 프로세스로 동작해야 한다.
 *
 * @relation(SYS-REQ-35, scope=file)
 */

#include <array>
#include <cstdint>

namespace kist::safety {

constexpr size_t kJointCount = 29;
constexpr double kMaxDeltaQPerTick = 0.05;  // rad
constexpr uint32_t kEstopDeadlineMs = 100;

struct JointLimits {
  double q_min;
  double q_max;
};

/// 관절 한계 초과 및 급격한 명령 변화를 감시한다.
/// @relation(SYS-REQ-35, scope=class)
class EstopMonitor {
 public:
  /// rt/lowcmd 발행 직전에 호출된다. false 반환 시 명령을 차단한다.
  /// @relation(SYS-REQ-35, scope=function)
  bool Validate(const std::array<double, kJointCount>& q_target) {
    for (size_t i = 0; i < kJointCount; ++i) {
      if (q_target[i] < limits_[i].q_min || q_target[i] > limits_[i].q_max) {
        TriggerEstop("joint limit exceeded");
        return false;
      }
      if (std::abs(q_target[i] - q_prev_[i]) > kMaxDeltaQPerTick) {
        TriggerEstop("command discontinuity");
        return false;
      }
    }
    q_prev_ = q_target;
    return true;
  }

 private:
  // 기능 제어 레이어를 거치지 않고 모터 드라이버에 직접 정지를 지시한다.
  // @relation(SYS-REQ-35, scope=range_start)
  void TriggerEstop(const char* reason);
  // @relation(SYS-REQ-35, scope=range_end)

  std::array<JointLimits, kJointCount> limits_{};
  std::array<double, kJointCount> q_prev_{};
};

}  // namespace kist::safety
