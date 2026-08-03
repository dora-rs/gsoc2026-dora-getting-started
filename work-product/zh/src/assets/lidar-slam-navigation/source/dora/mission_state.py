from dataclasses import asdict, dataclass


@dataclass
class SensorSnapshot:
    scan_samples: int = 0
    odom_samples: int = 0
    map_width: int = 0
    map_height: int = 0
    known_cells: int = 0
    pose_available: bool = False


class MissionGate:
    def __init__(self):
        self.state = "WAITING_FOR_SENSORS"
        self.sensors = SensorSnapshot()
        self.goal_sent = False
        self.goal_accepted = False
        self.distance_remaining = None
        self.detail = "Waiting for LiDAR, odometry, map, and SLAM pose"

    def update_sensors(self, payload):
        self.sensors = SensorSnapshot(
            scan_samples=int(payload.get("scan_samples", 0)),
            odom_samples=int(payload.get("odom_samples", 0)),
            map_width=int(payload.get("map", {}).get("width", 0)),
            map_height=int(payload.get("map", {}).get("height", 0)),
            known_cells=int(payload.get("map", {}).get("known_cells", 0)),
            pose_available=payload.get("map_pose") is not None,
        )
        if not self.ready:
            self.state = "WAITING_FOR_SENSORS"
        elif not self.goal_sent:
            self.state = "READY"
            self.detail = "Required sensor and localization streams are ready"

    @property
    def ready(self):
        return (
            self.sensors.scan_samples > 0
            and self.sensors.odom_samples > 0
            and self.sensors.map_width > 0
            and self.sensors.map_height > 0
            and self.sensors.known_cells >= 500
            and self.sensors.pose_available
        )

    def mark_goal_sent(self):
        self.goal_sent = True
        self.state = "GOAL_SENT"
        self.detail = "NavigateToPose goal sent to Nav2"

    def mark_goal_accepted(self):
        self.goal_accepted = True
        self.state = "NAVIGATING"
        self.detail = "Nav2 accepted the navigation goal"

    def update_feedback(self, distance_remaining):
        self.distance_remaining = float(distance_remaining)
        self.state = "NAVIGATING"

    def complete(self, succeeded, detail):
        self.state = "SUCCEEDED" if succeeded else "FAILED"
        self.detail = detail

    def as_dict(self):
        return {
            "state": self.state,
            "detail": self.detail,
            "goal_sent": self.goal_sent,
            "goal_accepted": self.goal_accepted,
            "distance_remaining": self.distance_remaining,
            "sensors": asdict(self.sensors),
        }
