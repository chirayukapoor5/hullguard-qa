"""Mass calculations for the documented disjoint box model."""

from math import fsum, prod

from .models import DENSITY, Component, Model


def volume_m3(part: Component) -> float:
    return prod(dimension / 1_000 for dimension in part.size_mm)


def mass_kg(part: Component) -> float:
    return volume_m3(part) * DENSITY[part.material]


def assembly_mass_kg(model: Model) -> float:
    return fsum(map(mass_kg, model.components))
