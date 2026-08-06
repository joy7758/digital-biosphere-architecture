"""Deterministic controlled worker for the method-v2 experiment.

Execution results are determined ONLY by:

    task_requirements + selected_agent + capability_matrix + environment

This module never reads the experiment arm, any decision-change flag, any
protocol-enablement flag, any desired result, or any expected outcome. The
same inputs always produce the same result (pure function, no I/O, no clock).

Result status enum follows AHRP Experience Event v0.1:
SUCCESS / FAILURE / TIMEOUT / CANCELLED.
"""

from typing import Any, Dict, Tuple

# Ordered, documented decision rules. Priority is fixed and deterministic.
RULE_CAPABILITY_MISSING = "RULE_CAPABILITY_MISSING"
RULE_POLICY_RESTRICTION = "RULE_POLICY_RESTRICTION"
RULE_SERVICE_UNAVAILABLE = "RULE_SERVICE_UNAVAILABLE"
RULE_INPUT_OVER_AGENT_CAPACITY = "RULE_INPUT_OVER_AGENT_CAPACITY"
RULE_INPUT_OVER_ENVIRONMENT = "RULE_INPUT_OVER_ENVIRONMENT"
RULE_PASS = "RULE_PASS"


def agent_key(identity_ref: str, agent_version: str) -> str:
    return f"{identity_ref}@{agent_version}"


def execute_task(task: Dict[str, Any], identity_ref: str,
                 capability_matrix: Dict[str, Any]
                 ) -> Tuple[str, str, str]:
    """Execute one task deterministically.

    Returns ``(result_status, failure_category, rule)`` where
    ``failure_category`` is ``"NOT_APPLICABLE"`` for SUCCESS.
    """
    environment = capability_matrix["environment"]
    key = agent_key(identity_ref, "1.0.0")
    agent = capability_matrix["agents"].get(key)
    if agent is None:
        # Unknown agent is a capability failure, never a silent pass.
        return "FAILURE", "CAPABILITY_LIMIT", RULE_CAPABILITY_MISSING

    task_type = task["task_type"]
    requirements = task["requirements"]
    capability = agent["capabilities"].get(task_type)
    min_level = requirements["min_capability_level"]
    input_size_mb = requirements["input_size_mb"]

    # Rule 1: capability level must cover the task requirement.
    if capability is None or capability["level"] < min_level:
        return "FAILURE", "CAPABILITY_LIMIT", RULE_CAPABILITY_MISSING

    # Rule 2: policy-compliance certification is mandatory when required.
    if requirements.get("requires_policy_compliance") and \
            not agent.get("policy_compliance_certified", False):
        return "FAILURE", "POLICY_RESTRICTION", RULE_POLICY_RESTRICTION

    # Rule 3: required environment services must be available.
    for service in requirements.get("required_services", []):
        if service in environment.get("unavailable_services", []):
            return "CANCELLED", "DEPENDENCY_FAILURE", RULE_SERVICE_UNAVAILABLE

    # Rule 4: input size must fit the agent's declared capacity.
    if input_size_mb > capability["max_input_mb"]:
        return "TIMEOUT", "RESOURCE_UNAVAILABLE", RULE_INPUT_OVER_AGENT_CAPACITY

    # Rule 5: input size must fit the controlled environment.
    if input_size_mb > environment.get("max_single_input_mb", 0):
        return "TIMEOUT", "ENVIRONMENT_ERROR", RULE_INPUT_OVER_ENVIRONMENT

    return "SUCCESS", "NOT_APPLICABLE", RULE_PASS
