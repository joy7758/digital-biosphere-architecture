def deliver(task_id: str) -> str:
    """Deterministic deliverable produced by worker-alpha."""
    return f"delivered:{task_id}"
