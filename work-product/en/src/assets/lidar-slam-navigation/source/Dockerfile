FROM cyberbotics/webots:R2025a-ubuntu22.04

ARG ROS_DISTRO=humble
ARG DORA_CLI_VERSION=1.0.0-rc.4
ARG DORA_PYTHON_VERSION=1.0.0rc4
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
        "pyarrow>=14,<20" \
        "pytest>=7,<9" \
        "uv==0.11.17" \
    && rm -rf /var/lib/apt/lists/*

RUN uv python install 3.11.14 \
    && uv venv --python 3.11.14 /opt/dora-venv \
    && uv pip install --python /opt/dora-venv/bin/python \
        "dora-rs==${DORA_PYTHON_VERSION}" \
        "pyarrow==24.0.0" \
        "PyYAML==6.0.3" \
    && mkdir -p /opt/uv/bin \
    && mv /usr/local/bin/uv /opt/uv/bin/uv \
    && if [ -e /usr/local/bin/uvx ]; then mv /usr/local/bin/uvx /opt/uv/bin/uvx; fi

RUN curl -fsSL \
        "https://github.com/dora-rs/dora/releases/download/v${DORA_CLI_VERSION}/dora-cli-x86_64-unknown-linux-gnu.tar.gz" \
        -o /tmp/dora-cli.tar.gz \
    && echo "251cb47b6e306049082c9d5fc30aa6e73c7be1ad27acfbcfff2f23be3202dd5a  /tmp/dora-cli.tar.gz" | sha256sum --check --status \
    && tar -xzf /tmp/dora-cli.tar.gz -C /tmp \
    && install -m 0755 /tmp/dora-cli-x86_64-unknown-linux-gnu/dora /usr/local/bin/dora \
    && rm -rf /tmp/dora-cli.tar.gz /tmp/dora-cli-x86_64-unknown-linux-gnu

ENV PATH="/opt/dora-venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libxcb-cursor0 \
        python3-pil \
    && rm -rf /var/lib/apt/lists/*

COPY ros-entrypoint.sh /ros-entrypoint.sh
RUN chmod +x /ros-entrypoint.sh

ENTRYPOINT ["/ros-entrypoint.sh"]
CMD ["bash"]
