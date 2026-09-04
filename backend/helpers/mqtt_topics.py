def robot_id_from_topic(topic: str) -> str:
    parts = topic.split("/")
    if len(parts) >= 2:
        return parts[1]
    return ""


def is_state_topic(topic: str) -> bool:
    return topic.endswith("/state")


def is_status_topic(topic: str) -> bool:
    return topic.endswith("/status")
