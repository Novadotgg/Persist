import asyncio
import structlog
from app.services.rules import match_triage_rules
from app.api.v1.endpoints.events import EventIngestRequest

# Initialize test logger
logger = structlog.get_logger()

def test_rule_matching():
    """
    Test deterministic triage rule engine logic.
    """
    logger.info("Starting rule matching tests...")

    # Test case 1: Priority Sender
    payload_1 = {
        "sender": "boss@company.com",
        "subject": "Status report",
        "body": "Hello team, send updates."
    }
    p1 = match_triage_rules(payload_1)
    assert p1 == 5, f"Expected priority 5, got {p1}"
    logger.info("Test 1 passed (Priority Sender -> 5)")

    # Test case 2: Urgent Keyword
    payload_2 = {
        "sender": "external@gmail.com",
        "subject": "Database outage alert!",
        "body": "The staging server seems to be down."
    }
    p2 = match_triage_rules(payload_2)
    assert p2 == 4, f"Expected priority 4, got {p2}"
    logger.info("Test 2 passed (Outage Keyword -> 4)")

    # Test case 3: Low priority newsletter
    payload_3 = {
        "sender": "newsletter@techcrunch.com",
        "subject": "Weekly Tech Digest",
        "body": "Here are the top stories of this week..."
    }
    p3 = match_triage_rules(payload_3)
    assert p3 == 1, f"Expected priority 1, got {p3}"
    logger.info("Test 3 passed (Newsletter Sender -> 1)")

    # Test case 4: Neutral event
    payload_4 = {
        "sender": "friend@gmail.com",
        "subject": "Coffee tomorrow?",
        "body": "Let's meet at 10 AM."
    }
    p4 = match_triage_rules(payload_4)
    assert p4 is None, f"Expected None (fallback to AI), got {p4}"
    logger.info("Test 4 passed (Neutral message -> None/fallback)")

    logger.info("All rule engine tests passed successfully!")


def test_schema_validation():
    """
    Test input payload schemas validate correctly.
    """
    logger.info("Starting schema validation tests...")
    
    req_data = {
        "source": "gmail",
        "type": "email_received",
        "payload": {
            "sender": "alice@example.com",
            "subject": "Hello",
            "body": "Body contents"
        }
    }
    
    # This should parse successfully without Pydantic validation errors
    obj = EventIngestRequest(**req_data)
    assert obj.source == "gmail"
    assert obj.type == "email_received"
    assert obj.payload["sender"] == "alice@example.com"
    
    logger.info("Schema validation tests passed successfully!")


if __name__ == "__main__":
    print("==================================================")
    print("      Personal AI Assistant OS Verification      ")
    print("==================================================")
    
    test_rule_matching()
    print("--------------------------------------------------")
    test_schema_validation()
    print("==================================================")
    print("             Verification Successful!             ")
    print("==================================================")
