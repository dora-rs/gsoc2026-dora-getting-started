FROM cyberbotics/webots:R2025a-ubuntu22.04

ARG ROS_DISTRO=humble
ENV ROS_DISTRO=${ROS_DISTRO}
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        gnupg \
        libxcb-cursor0 \
        locales \
        python3-opencv \
        python3-pil \
        python3-pip \
        software-properties-common \
        x11-apps \
    && locale-gen en_US.UTF-8 \
    && add-apt-repository universe \
    && curl -fsSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
        -o /usr/share/keyrings/ros-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" \
        > /etc/apt/sources.list.d/ros2.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        ros-${ROS_DISTRO}-cv-bridge \
        ros-${ROS_DISTRO}-ros-base \
    && python3 -m pip install --no-cache-dir \
        "dora-rs==0.5.0" \
        "fastapi==0.140.13" \
        "httpx==0.28.1" \
        "pydantic==2.13.4" \
        "pyarrow>=14,<20" \
        "pytest>=7,<9" \
        "PyYAML>=6,<7" \
        "requests>=2.31,<3" \
        "uvicorn==0.51.0" \
    && rm -rf /var/lib/apt/lists/*

COPY ros-entrypoint.sh /ros-entrypoint.sh
RUN chmod +x /ros-entrypoint.sh

ENTRYPOINT ["/ros-entrypoint.sh"]
CMD ["bash"]
