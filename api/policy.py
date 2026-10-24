from dataclasses import dataclass

from pydantic import BaseModel, Field

# Only images from these registries may be deployed.
ALLOWED_REGISTRIES = ("ghcr.io/", "docker.io/library/")


class DeploymentSpec(BaseModel):
    """What a developer asks us to deploy."""

    service: str = Field(pattern=r"^[a-z][a-z0-9-]{1,40}[a-z0-9]$")
    image: str = Field(min_length=3, max_length=200)
    port: int = Field(ge=1, le=65535)
    cpu_limit: str | None = None
    memory_limit: str | None = None
    run_as_non_root: bool = False
    privileged: bool = False


@dataclass(frozen=True)
class Violation:
    rule: str
    message: str


def _has_pinned_tag(image: str) -> bool:
    """True if the image has a real version tag or a digest (not 'latest', not missing)."""
    if "@sha256:" in image:
        return True
    last_part = image.rsplit("/", 1)[-1]
    if ":" not in last_part:
        return False
    tag = last_part.split(":", 1)[1]
    return tag not in ("", "latest")


def evaluate(
    spec: DeploymentSpec,
    env_kind: str,
    requested_by: str,
    approved_by: str | None = None,
) -> list[Violation]:
    """Check a deployment request against every rule. Returns ALL violations found."""
    violations: list[Violation] = []

    if not _has_pinned_tag(spec.image):
        violations.append(
            Violation("image-tag-pinned", "Image must use a specific version tag or digest, not 'latest' or no tag.")
        )

    if not spec.image.lower().startswith(ALLOWED_REGISTRIES):
        violations.append(
            Violation("image-registry-allowed", f"Image must come from an allowed registry: {', '.join(ALLOWED_REGISTRIES)}")
        )

    if not spec.run_as_non_root:
        violations.append(Violation("run-as-non-root", "Container must run as a non-root user."))

    if spec.privileged:
        violations.append(Violation("no-privileged", "Privileged containers are not allowed."))

    if not spec.cpu_limit or not spec.memory_limit:
        violations.append(
            Violation("resource-limits-required", "Both a CPU limit and a memory limit are required.")
        )

    if spec.port < 1024:
        violations.append(Violation("unprivileged-port", "Ports below 1024 are not allowed."))

    if env_kind == "prod":
        if not approved_by:
            violations.append(Violation("prod-needs-approval", "Production deployments need an approver."))
        elif approved_by == requested_by:
            violations.append(
                Violation("prod-needs-approval", "The approver must be a different person than the requester.")
            )

    return violations