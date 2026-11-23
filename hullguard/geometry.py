"""Write and read the HULLGUARD subset of Wavefront OBJ."""

from collections import Counter
from dataclasses import dataclass, field
from itertools import product
from math import isfinite
from typing import cast

from .models import Model, Vector

# Corner ordering follows Cartesian product X, Y, Z, each with low then high.
TRIANGLES = (
    (0, 1, 3),
    (0, 3, 2),
    (4, 6, 7),
    (4, 7, 5),
    (0, 4, 5),
    (0, 5, 1),
    (2, 3, 7),
    (2, 7, 6),
    (0, 2, 6),
    (0, 6, 4),
    (1, 5, 7),
    (1, 7, 3),
)


def write_obj(model: Model) -> str:
    lines = [f"# hullguard revision {model.revision}", "# hullguard units mm"]
    for index, part in enumerate(model.components):
        lines.append(f"o {part.id}")
        axes = zip(part.origin_mm, part.maximum_mm, strict=True)
        lines.extend(
            "v " + " ".join(f"{coordinate:.3f}" for coordinate in v) for v in product(*axes)
        )
        start = 8 * index + 1
        lines.extend(f"f {start + a} {start + b} {start + c}" for a, b, c in TRIANGLES)
    return "\n".join(lines) + "\n"


@dataclass
class Mesh:
    vertices: list[Vector] = field(default_factory=list)
    faces: list[tuple[int, int, int]] = field(default_factory=list)

    @property
    def bounds(self) -> tuple[Vector, Vector]:
        axes = list(zip(*self.vertices, strict=True))
        return cast(Vector, tuple(map(min, axes))), cast(Vector, tuple(map(max, axes)))

    def is_closed_outward_box(self) -> bool:
        if len(self.vertices) != 8 or len(self.faces) != 12:
            return False
        low, high = self.bounds
        if set(self.vertices) != set(product(*zip(low, high, strict=True))):
            return False
        planes: Counter = Counter()
        directed_edges: Counter = Counter()
        for triangle in self.faces:
            a, b, c = (self.vertices[index] for index in triangle)
            plane = [axis for axis in range(3) if a[axis] == b[axis] == c[axis]]
            if len(set(triangle)) != 3 or len(plane) != 1:
                return False
            axis = plane[0]
            j, k = (axis + 1) % 3, (axis + 2) % 3
            normal = (b[j] - a[j]) * (c[k] - a[k]) - (b[k] - a[k]) * (c[j] - a[j])
            direction = 1 if a[axis] == high[axis] else -1
            if normal * direction <= 0:
                return False
            planes[axis, direction] += 1
            for start, end in zip(triangle, (*triangle[1:], triangle[0]), strict=True):
                directed_edges[start, end] += 1
        return (
            len(planes) == 6
            and all(count == 2 for count in planes.values())
            and all(
                count == 1 and directed_edges[end, start] == 1
                for (start, end), count in directed_edges.items()
            )
        )


def read_obj(content: str) -> tuple[dict[str, str], dict[str, Mesh]]:
    headers: dict[str, str] = {}
    meshes: dict[str, Mesh] = {}
    mesh = None
    total_vertices = 0
    offset = 0
    for line_no, line in enumerate(content.splitlines(), 1):
        values = line.split()
        if not values:
            continue
        try:
            match values:
                case ["#", "hullguard", key, value]:
                    if key in headers:
                        raise ValueError(f"duplicate header {key}")
                    headers[key] = value
                case ["#", *_]:
                    continue
                case ["o", name]:
                    if name in meshes:
                        raise ValueError(f"duplicate object {name}")
                    mesh = meshes[name] = Mesh()
                    offset = total_vertices
                case ["v", x, y, z] if mesh is not None:
                    vertex = (float(x), float(y), float(z))
                    if any(not isfinite(value) or abs(value) > 2_000_000 for value in vertex):
                        raise ValueError("vertex must be finite and within ±2,000,000 mm")
                    mesh.vertices.append(vertex)
                    total_vertices += 1
                case ["f", a, b, c] if mesh is not None:
                    indices = (int(a) - offset - 1, int(b) - offset - 1, int(c) - offset - 1)
                    if min(indices) < 0 or max(indices) >= len(mesh.vertices):
                        raise ValueError("face references a vertex outside the current object")
                    mesh.faces.append(indices)
                case _:
                    raise ValueError("expected a named object, vertex, triangle, or comment")
        except ValueError as error:
            raise ValueError(f"OBJ line {line_no}: {error}") from error
    return headers, meshes
