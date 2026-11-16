// cloud_rate_monitor: measures the real publication rate of a PointCloud2 topic.
//
// Why not `ros2 topic hz`? It is a Python subscriber, and for ~1 MB clouds it can be slower
// than the publisher. With a RELIABLE publisher that back-pressures the driver, so the
// number it prints depends on the subscriber, not on the LiDAR. This node is a light C++
// subscriber with configurable QoS and reports, once per window:
//   - arrival rate (Hz) and min/max period
//   - gaps: periods longer than gap_factor x the expected period (= missed or late scans)
//   - points per cloud (width x height)
//   - latency: arrival time minus header.stamp (meaningful only if the stamp is system time)
//
// Usage:
//   ros2 run caddy_ai2_ros2_sensors_rs_helios_5515 cloud_rate_monitor \
//     --ros-args -p topic:=/caddy_ai2/rs_helios_5515/points -p reliability:=best_effort

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <limits>
#include <memory>
#include <string>

#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/msg/point_cloud2.hpp"

using sensor_msgs::msg::PointCloud2;
using Clock = std::chrono::steady_clock;

class CloudRateMonitor : public rclcpp::Node
{
public:
  CloudRateMonitor()
  : Node("cloud_rate_monitor")
  {
    topic_ = declare_parameter<std::string>("topic", "/rs_helios_5515/points");
    const auto reliability = declare_parameter<std::string>("reliability", "best_effort");
    depth_ = declare_parameter<int>("depth", 5);
    window_s_ = declare_parameter<double>("window_s", 5.0);
    expected_hz_ = declare_parameter<double>("expected_hz", 10.0);
    gap_factor_ = declare_parameter<double>("gap_factor", 1.5);

    rclcpp::QoS qos(rclcpp::KeepLast(static_cast<size_t>(std::max<int64_t>(1, depth_))));
    if (reliability == "reliable") {
      qos.reliable();
    } else if (reliability == "best_effort") {
      qos.best_effort();
    } else {
      RCLCPP_WARN(get_logger(), "reliability '%s' unknown, using best_effort", reliability.c_str());
      qos.best_effort();
    }

    sub_ = create_subscription<PointCloud2>(
      topic_, qos, [this](PointCloud2::ConstSharedPtr msg) {on_cloud(*msg);});

    timer_ = create_wall_timer(
      std::chrono::duration<double>(window_s_), [this]() {report();});

    RCLCPP_INFO(
      get_logger(), "Listening to %s (%s, depth %ld). Expected %.1f Hz, window %.1f s.",
      topic_.c_str(), reliability.c_str(), static_cast<long>(depth_), expected_hz_, window_s_);
    reset_window();
    window_start_ = Clock::now();
  }

private:
  void on_cloud(const PointCloud2 & msg)
  {
    const auto now = Clock::now();
    if (have_last_) {
      const double dt = std::chrono::duration<double>(now - last_arrival_).count();
      period_min_ = std::min(period_min_, dt);
      period_max_ = std::max(period_max_, dt);
      if (dt > gap_factor_ / expected_hz_) {
        ++gaps_;
        // Scans that did not arrive in this gap (period / nominal - 1).
        missed_ += static_cast<uint64_t>(std::max(0.0, dt * expected_hz_ - 0.5)) ;
      }
    }
    last_arrival_ = now;
    have_last_ = true;

    ++count_;
    ++total_;
    points_ = static_cast<uint64_t>(msg.width) * msg.height;

    const double latency =
      (this->get_clock()->now() - rclcpp::Time(msg.header.stamp, get_clock()->get_clock_type()))
      .seconds();
    latency_sum_ += latency;
    latency_max_ = std::max(latency_max_, latency);
    frame_id_ = msg.header.frame_id;
  }

  void report()
  {
    const auto now = Clock::now();
    const double elapsed = std::chrono::duration<double>(now - window_start_).count();
    if (count_ == 0) {
      RCLCPP_WARN(get_logger(), "No clouds on %s in the last %.1f s", topic_.c_str(), elapsed);
    } else {
      const double hz = static_cast<double>(count_) / elapsed;
      const bool has_period = period_max_ > 0.0;
      RCLCPP_INFO(
        get_logger(),
        "%.2f Hz (%.0f%% of %.1f) | period min %.3f max %.3f s | gaps %lu (~%lu scans missed) | "
        "%lu pts | latency avg %.3f max %.3f s | frame %s | total %lu",
        hz, 100.0 * hz / expected_hz_, expected_hz_,
        has_period ? period_min_ : 0.0, has_period ? period_max_ : 0.0,
        static_cast<unsigned long>(gaps_), static_cast<unsigned long>(missed_),
        static_cast<unsigned long>(points_),
        latency_sum_ / static_cast<double>(count_), latency_max_,
        frame_id_.c_str(), static_cast<unsigned long>(total_));
    }
    reset_window();
    window_start_ = now;
  }

  void reset_window()
  {
    count_ = 0;
    gaps_ = 0;
    missed_ = 0;
    period_min_ = std::numeric_limits<double>::max();
    period_max_ = 0.0;
    latency_sum_ = 0.0;
    latency_max_ = 0.0;
  }

  std::string topic_;
  int64_t depth_{5};
  double window_s_{5.0};
  double expected_hz_{10.0};
  double gap_factor_{1.5};

  rclcpp::Subscription<PointCloud2>::SharedPtr sub_;
  rclcpp::TimerBase::SharedPtr timer_;

  Clock::time_point window_start_;
  Clock::time_point last_arrival_;
  bool have_last_{false};

  uint64_t count_{0}, total_{0}, gaps_{0}, missed_{0}, points_{0};
  double period_min_{0.0}, period_max_{0.0}, latency_sum_{0.0}, latency_max_{0.0};
  std::string frame_id_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<CloudRateMonitor>());
  rclcpp::shutdown();
  return 0;
}
