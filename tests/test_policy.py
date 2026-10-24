from api.policy import DeploymentSpec, evaluate

GOOD = dict(
    service="demo-api",
    image="ghcr.io/technathan971/demo-api:1.0.0",
    port=8080,
    cpu_limit="500m",
    memory_limit="256Mi",
    run_as_non_root=True,
)


def check(env_kind="dev", requested_by="alice", approved_by=None, **overrides):
    spec = DeploymentSpec(**{**GOOD, **overrides})
    return {v.rule for v in evaluate(spec, env_kind, requested_by, approved_by)}


def test_good_request_passes_in_dev():
    assert check() == set()


def test_latest_tag_is_blocked():
    assert check(image="ghcr.io/technathan971/demo-api:latest") == {"image-tag-pinned"}


def test_untagged_image_is_blocked():
    assert check(image="ghcr.io/technathan971/demo-api") == {"image-tag-pinned"}


def test_digest_pinned_image_is_allowed():
    digest_image = "ghcr.io/technathan971/demo-api@sha256:" + "a" * 64
    assert check(image=digest_image) == set()


def test_unknown_registry_is_blocked():
    assert check(image="evil.example.com/demo-api:1.0.0") == {"image-registry-allowed"}


def test_root_container_is_blocked():
    assert check(run_as_non_root=False) == {"run-as-non-root"}


def test_privileged_container_is_blocked():
    assert check(privileged=True) == {"no-privileged"}


def test_missing_limits_are_blocked():
    assert check(cpu_limit=None) == {"resource-limits-required"}
    assert check(memory_limit=None) == {"resource-limits-required"}


def test_low_port_is_blocked():
    assert check(port=80) == {"unprivileged-port"}


def test_prod_without_approver_is_blocked():
    assert check(env_kind="prod") == {"prod-needs-approval"}


def test_prod_self_approval_is_blocked():
    assert check(env_kind="prod", requested_by="alice", approved_by="alice") == {"prod-needs-approval"}


def test_prod_with_different_approver_passes():
    assert check(env_kind="prod", requested_by="alice", approved_by="bob") == set()


def test_all_violations_are_reported_together():
    rules = check(
        env_kind="prod",
        image="nginx",
        port=80,
        cpu_limit=None,
        run_as_non_root=False,
        privileged=True,
    )
    assert rules == {
        "image-tag-pinned",
        "image-registry-allowed",
        "run-as-non-root",
        "no-privileged",
        "resource-limits-required",
        "unprivileged-port",
        "prod-needs-approval",
    }