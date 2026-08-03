FROM cyberbotics/webots:R2025a-ubuntu22.04

ARG ROS_DISTRO=humble
ENV ROS_DISTRO=${ROS_DISTRO}
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        gnupg \
        locales \
        python3-pip \
        software-properties-common \
    && locale-gen en_US.UTF-8 \
    && add-apt-repository universe \
    && curl -fsSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
        -o /usr/share/keyrings/ros-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" \
        > /etc/apt/sources.list.d/ros2.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        ros-${ROS_DISTRO}-cartographer-ros \
        ros-${ROS_DISTRO}-navigation2 \
        ros-${ROS_DISTRO}-nav2-bringup \
        ros-${ROS_DISTRO}-robot-localization \
        ros-${ROS_DISTRO}-ros-base \
        ros-${ROS_DISTRO}-rviz2 \
        ros-${ROS_DISTRO}-slam-toolbox \
        ros-${ROS_DISTRO}-teleop-twist-keyboard \
        ros-${ROS_DISTRO}-webots-ros2-tiago \
        ros-${ROS_DISTRO}-webots-ros2-driver \
        ros-${ROS_DISTRO}-xacro \
        python3-colcon-common-extensions \
        python3-rosdep \
        python3-vcstool \
        x11-apps \
    && python3 -m pip install --no-cache-dir \
        "dora-rs==0.5.0" \
        "pyarrow>=14,<20" \
        "pytest>=7,<9" \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libxcb-cursor0 \
        python3-pil \
    && rm -rf /var/lib/apt/lists/*

COPY ros-entrypoint.sh /ros-entrypoint.sh
RUN chmod +x /ros-entrypoint.sh

ENTRYPOINT ["/ros-entrypoint.sh"]
CMD ["bash"]
