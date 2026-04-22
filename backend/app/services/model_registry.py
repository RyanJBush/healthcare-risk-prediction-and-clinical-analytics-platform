from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RegisteredModel:
    name: str
    version: str
    target_type: str
    family: str
    description: str


class ModelRegistry:
    """Simple in-process model registry abstraction for online inference."""

    def __init__(self) -> None:
        self._models: dict[tuple[str, str], RegisteredModel] = {}

    def register(self, model: RegisteredModel) -> None:
        self._models[(model.target_type, model.version)] = model

    def resolve(self, target_type: str, version: str = "tiered-v1") -> RegisteredModel | None:
        return self._models.get((target_type, version))

    def list_all(self) -> list[RegisteredModel]:
        return sorted(self._models.values(), key=lambda item: (item.target_type, item.version))


def build_default_registry() -> ModelRegistry:
    registry = ModelRegistry()
    for target in ("readmission", "deterioration", "adverse_event"):
        registry.register(
            RegisteredModel(
                name="Tiered Clinical Risk Engine",
                version="tiered-v1",
                target_type=target,
                family="rule_calibrated_logit",
                description=f"Production default model for {target}.",
            )
        )
    return registry
