from __future__ import annotations

import base64
import json
import math
import struct
from pathlib import Path


MODELS = Path("models")
MODELS.mkdir(exist_ok=True)


class GltfBuilder:
    def __init__(self) -> None:
        self.positions: list[tuple[float, float, float]] = []
        self.indices: list[int] = []
        self.meshes: list[dict] = []
        self.nodes: list[dict] = []
        self.materials: list[dict] = []

    def material(self, name: str, color: tuple[float, float, float, float]) -> int:
        self.materials.append(
            {
                "name": name,
                "pbrMetallicRoughness": {
                    "baseColorFactor": list(color),
                    "metallicFactor": 0.05,
                    "roughnessFactor": 0.62,
                },
            }
        )
        return len(self.materials) - 1

    def mesh(self, name: str, vertices: list[tuple[float, float, float]], faces: list[tuple[int, int, int]], material: int) -> int:
        vertex_offset = len(self.positions)
        index_offset = len(self.indices)
        self.positions.extend(vertices)
        for face in faces:
            self.indices.extend(face)
        self.meshes.append(
            {
                "name": name,
                "primitive": {
                    "position_offset": vertex_offset,
                    "position_count": len(vertices),
                    "index_offset": index_offset,
                    "index_count": len(faces) * 3,
                    "material": material,
                },
            }
        )
        self.nodes.append({"name": name, "mesh": len(self.meshes) - 1})
        return len(self.meshes) - 1

    def box(self, name: str, center: tuple[float, float, float], size: tuple[float, float, float], material: int) -> None:
        cx, cy, cz = center
        sx, sy, sz = (value / 2 for value in size)
        vertices = [
            (cx - sx, cy - sy, cz - sz),
            (cx + sx, cy - sy, cz - sz),
            (cx + sx, cy + sy, cz - sz),
            (cx - sx, cy + sy, cz - sz),
            (cx - sx, cy - sy, cz + sz),
            (cx + sx, cy - sy, cz + sz),
            (cx + sx, cy + sy, cz + sz),
            (cx - sx, cy + sy, cz + sz),
        ]
        faces = [
            (0, 1, 2), (0, 2, 3),
            (4, 6, 5), (4, 7, 6),
            (0, 4, 5), (0, 5, 1),
            (1, 5, 6), (1, 6, 2),
            (2, 6, 7), (2, 7, 3),
            (3, 7, 4), (3, 4, 0),
        ]
        self.mesh(name, vertices, faces, material)

    def cylinder_y(self, name: str, center: tuple[float, float, float], radius: float, length: float, material: int, segments: int = 24) -> None:
        cx, cy, cz = center
        vertices: list[tuple[float, float, float]] = []
        for side in (-0.5, 0.5):
            for index in range(segments):
                angle = math.tau * index / segments
                vertices.append((cx + math.cos(angle) * radius, cy + side * length, cz + math.sin(angle) * radius))
        vertices.append((cx, cy - length / 2, cz))
        vertices.append((cx, cy + length / 2, cz))
        bottom_center = segments * 2
        top_center = segments * 2 + 1
        faces: list[tuple[int, int, int]] = []
        for index in range(segments):
            nxt = (index + 1) % segments
            faces.append((index, nxt, segments + nxt))
            faces.append((index, segments + nxt, segments + index))
            faces.append((bottom_center, nxt, index))
            faces.append((top_center, segments + index, segments + nxt))
        self.mesh(name, vertices, faces, material)

    def write(self, path: Path) -> None:
        binary = bytearray()
        position_view = 0
        for vertex in self.positions:
            binary.extend(struct.pack("<fff", *vertex))
        while len(binary) % 4:
            binary.append(0)
        index_view = len(binary)
        for index in self.indices:
            binary.extend(struct.pack("<H", index))
        while len(binary) % 4:
            binary.append(0)

        buffer_views = [
            {"buffer": 0, "byteOffset": 0, "byteLength": position_view + len(self.positions) * 12, "target": 34962},
            {"buffer": 0, "byteOffset": index_view, "byteLength": len(self.indices) * 2, "target": 34963},
        ]
        accessors = []
        primitives = []
        for mesh in self.meshes:
            primitive = mesh["primitive"]
            pos_slice = self.positions[primitive["position_offset"]: primitive["position_offset"] + primitive["position_count"]]
            pos_accessor = len(accessors)
            accessors.append(
                {
                    "bufferView": 0,
                    "byteOffset": primitive["position_offset"] * 12,
                    "componentType": 5126,
                    "count": primitive["position_count"],
                    "type": "VEC3",
                    "min": [min(point[i] for point in pos_slice) for i in range(3)],
                    "max": [max(point[i] for point in pos_slice) for i in range(3)],
                }
            )
            idx_accessor = len(accessors)
            accessors.append(
                {
                    "bufferView": 1,
                    "byteOffset": primitive["index_offset"] * 2,
                    "componentType": 5123,
                    "count": primitive["index_count"],
                    "type": "SCALAR",
                }
            )
            primitives.append(
                {
                    "attributes": {"POSITION": pos_accessor},
                    "indices": idx_accessor,
                    "material": primitive["material"],
                    "mode": 4,
                }
            )

        gltf = {
            "asset": {"version": "2.0", "generator": "Dora Rerun tutorial model generator"},
            "scene": 0,
            "scenes": [{"nodes": list(range(len(self.nodes)))}],
            "nodes": self.nodes,
            "meshes": [{"name": mesh["name"], "primitives": [primitive]} for mesh, primitive in zip(self.meshes, primitives)],
            "materials": self.materials,
            "buffers": [{"uri": "data:application/octet-stream;base64," + base64.b64encode(binary).decode("ascii"), "byteLength": len(binary)}],
            "bufferViews": buffer_views,
            "accessors": accessors,
        }
        path.write_text(json.dumps(gltf, indent=2), encoding="utf-8")


def write_robot() -> None:
    gltf = GltfBuilder()
    blue = gltf.material("robot_blue", (0.20, 0.42, 0.78, 1.0))
    light = gltf.material("robot_light", (0.45, 0.66, 0.95, 1.0))
    dark = gltf.material("robot_dark", (0.12, 0.18, 0.28, 1.0))
    gltf.box("torso", (0.0, 0.0, 0.95), (0.42, 0.28, 0.82), blue)
    gltf.box("head", (0.0, 0.0, 1.55), (0.34, 0.30, 0.30), light)
    gltf.box("left_leg", (-0.13, 0.0, 0.35), (0.12, 0.16, 0.70), dark)
    gltf.box("right_leg", (0.13, 0.0, 0.35), (0.12, 0.16, 0.70), dark)
    gltf.box("left_arm", (0.0, -0.25, 0.92), (0.14, 0.12, 0.62), dark)
    gltf.box("right_arm", (0.0, 0.25, 0.92), (0.14, 0.12, 0.62), dark)
    gltf.write(MODELS / "humanoid_robot.gltf")


def write_car() -> None:
    gltf = GltfBuilder()
    yellow = gltf.material("car_yellow", (0.90, 0.68, 0.20, 1.0))
    cabin = gltf.material("car_cabin", (0.96, 0.78, 0.30, 1.0))
    tire = gltf.material("tire_dark", (0.04, 0.045, 0.05, 1.0))
    gltf.box("body", (0.0, 0.0, 0.32), (0.88, 0.46, 0.30), yellow)
    gltf.box("cabin", (-0.08, 0.0, 0.58), (0.42, 0.34, 0.28), cabin)
    for x in (-0.28, 0.28):
        for y in (-0.29, 0.29):
            gltf.cylinder_y(f"wheel_{x}_{y}", (x, y, 0.18), radius=0.13, length=0.10, material=tire)
    gltf.write(MODELS / "small_car.gltf")


def main() -> None:
    write_robot()
    write_car()
    print("Generated reusable glTF models in models/")


if __name__ == "__main__":
    main()
