"""
SOCaaS SDK Test Script

Tests each SDK method against the live API.
Run with: python test_sdk.py
"""

import json
import sys
from SOCaaSClient import SOCaaSClient, SERVICE_REQUEST_TYPES


def print_result(name: str, data, max_items: int = 2):
    """Pretty print test results."""
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print('='*60)

    if data is None:
        print("Result: None")
        return

    if isinstance(data, list):
        print(f"Count: {len(data)}")
        for i, item in enumerate(data[:max_items]):
            print(f"\n[{i}] {json.dumps(item, indent=2, default=str)[:500]}...")
        if len(data) > max_items:
            print(f"\n... and {len(data) - max_items} more items")
    elif isinstance(data, dict):
        print(json.dumps(data, indent=2, default=str)[:1000])
    else:
        print(data)


def test_alerts(client: SOCaaSClient):
    """Test alert endpoints."""
    print("\n" + "#"*60)
    print("# ALERT TESTS")
    print("#"*60)

    # 1. List Alerts
    alerts = client.list_alerts()
    print_result("List Alerts", alerts)

    if not alerts:
        print("\nNo alerts found. Skipping alert detail tests.")
        return None

    # Get first alert UUID for subsequent tests
    alert_uuid = alerts[0].get("uuid")
    alert_id = alerts[0].get("id")
    print(f"\nUsing alert UUID: {alert_uuid} (ID: {alert_id})")

    # 2. List Alerts with date filter
    alerts_filtered = client.list_alerts(
        created_date_from="2024-01-01T00:00:00Z",
        created_date_to="2026-12-31T23:59:59Z"
    )
    print_result("List Alerts (date filtered)", alerts_filtered)

    # 3. Get Alert Details
    alert_details = client.get_alert(alert_uuid)
    print_result("Get Alert Details", alert_details)

    return alert_uuid


def test_comments(client: SOCaaSClient, alert_uuid: str = None, sr_uuid: str = None):
    """Test comment endpoints."""
    print("\n" + "#"*60)
    print("# COMMENT TESTS")
    print("#"*60)

    if alert_uuid:
        # 4. List Alert Comments
        comments = client.list_alert_comments(alert_uuid)
        print_result(f"List Alert Comments ({alert_uuid[:8]}...)", comments)

        # 5. Create Alert Comment (commented out to avoid creating test data)
        # comment = client.create_alert_comment(alert_uuid, "Test comment from SDK")
        # print_result("Create Alert Comment", comment)

    if sr_uuid:
        # List Service Request Comments
        comments = client.list_service_request_comments(sr_uuid)
        print_result(f"List SR Comments ({sr_uuid[:8]}...)", comments)


def test_service_requests(client: SOCaaSClient):
    """Test service request endpoints."""
    print("\n" + "#"*60)
    print("# SERVICE REQUEST TESTS")
    print("#"*60)

    # 8. List Service Requests
    service_requests = client.list_service_requests()
    print_result("List Service Requests", service_requests)

    if not service_requests:
        print("\nNo service requests found.")
        return None

    sr_uuid = service_requests[0].get("uuid")
    print(f"\nUsing SR UUID: {sr_uuid}")

    # 9. Get Service Request Details
    sr_details = client.get_service_request(sr_uuid)
    print_result("Get Service Request Details", sr_details)

    return sr_uuid


def test_reports(client: SOCaaSClient):
    """Test report endpoints."""
    print("\n" + "#"*60)
    print("# REPORT TESTS")
    print("#"*60)

    reports = client.list_reports()
    print_result("List Reports", reports)

    return reports


def test_clients(client: SOCaaSClient):
    """Test client endpoints (MSSP)."""
    print("\n" + "#"*60)
    print("# CLIENT TESTS (MSSP)")
    print("#"*60)

    clients = client.list_clients()
    print_result("List Clients", clients)

    if clients:
        client_uuid = clients[0].get("client_uuid")
        print(f"\nUsing Client UUID: {client_uuid}")

        # Get alerts by client
        client_alerts = client.get_alerts_by_client(client_uuid)
        print_result(f"Alerts for Client ({client_uuid[:8]}...)", client_alerts)

        # Get service requests by client
        client_srs = client.get_service_requests_by_client(client_uuid)
        print_result(f"SRs for Client ({client_uuid[:8]}...)", client_srs)

        # Get reports by client
        client_reports = client.get_reports_by_client(client_uuid)
        print_result(f"Reports for Client ({client_uuid[:8]}...)", client_reports)

        return client_uuid

    return None


def test_onboarding_info(client: SOCaaSClient):
    """Test MSSP onboarding info endpoint."""
    print("\n" + "#"*60)
    print("# MSSP ONBOARDING INFO")
    print("#"*60)

    try:
        info = client.get_onboarding_info()
        print_result("Get Onboarding Info", info)
    except Exception as e:
        print(f"Onboarding info error (may require MSSP account): {e}")


def main():
    """Run all SDK tests."""
    print("="*60)
    print("SOCaaS SDK Test Suite")
    print("="*60)

    # Initialize client
    client = SOCaaSClient(
        username="62A1AFE0-0119-46FB-8AC8-9D2D04315BEE",
        password="91298682ce2e55c2721666f835e547e0!1Aa",
    )
    client.debug = True

    try:
        # Test each endpoint category
        alert_uuid = test_alerts(client)
        sr_uuid = test_service_requests(client)
        test_comments(client, alert_uuid, sr_uuid)
        test_reports(client)
        client_uuid = test_clients(client)
        test_onboarding_info(client)

        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        print(f"Alert UUID found: {alert_uuid}")
        print(f"Service Request UUID found: {sr_uuid}")
        print(f"Client UUID found: {client_uuid}")
        print("\nAll read-only tests completed!")

    except Exception as e:
        print(f"\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
