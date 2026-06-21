import unittest
from unittest.mock import patch, MagicMock
import time
import sys
import os

# Adjust path to import src modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.client import ConcurClient, ConcurAuthError, ConcurAPIError


class TestConcurClient(unittest.TestCase):

    def setUp(self):
        self.client_id = "test_client_id"
        self.client_secret = "test_client_secret"
        self.user_login_id = "user@example.com"
        self.client = ConcurClient(
            client_id=self.client_id,
            client_secret=self.client_secret
        )

    @patch("requests.post")
    def test_get_token_success(self, mock_post):
        # Configure mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "mock_access_token_123",
            "expires_in": 3600
        }
        mock_post.return_value = mock_response

        # Execute
        token = self.client.get_token()

        # Verify
        self.assertEqual(token, "mock_access_token_123")
        mock_post.assert_called_once_with(
            "https://us.api.concursolutions.com/oauth2/v0/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15
        )

    @patch("requests.post")
    def test_get_token_caching(self, mock_post):
        # Setup mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "mock_access_token_123",
            "expires_in": 3600
        }
        mock_post.return_value = mock_response

        # Call twice
        token1 = self.client.get_token()
        token2 = self.client.get_token()

        # Verify post was called only once (cached)
        self.assertEqual(token1, "mock_access_token_123")
        self.assertEqual(token2, "mock_access_token_123")
        mock_post.assert_called_once()

    @patch("requests.post")
    def test_get_token_failure(self, mock_post):
        # Setup mock with auth failure
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized client credentials"
        mock_post.return_value = mock_response

        with self.assertRaises(ConcurAuthError):
            self.client.get_token()

    @patch("requests.get")
    @patch("requests.post")
    def test_list_reports_success(self, mock_post, mock_get):
        # Mock authentication token call
        mock_auth_response = MagicMock()
        mock_auth_response.status_code = 200
        mock_auth_response.json.return_value = {
            "access_token": "mock_access_token_123",
            "expires_in": 3600
        }
        mock_post.return_value = mock_auth_response

        # Mock list reports GET call
        mock_list_response = MagicMock()
        mock_list_response.status_code = 200
        mock_list_response.json.return_value = {
            "Items": [
                {
                    "ReportID": "REP1",
                    "Name": "Trip to NY",
                    "Total": 150.00,
                    "CurrencyCode": "USD"
                }
            ]
        }
        mock_get.return_value = mock_list_response

        # Execute
        reports = self.client.list_reports(self.user_login_id)

        # Verify
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0]["ReportID"], "REP1")
        self.assertEqual(reports[0]["Name"], "Trip to NY")
        
        mock_get.assert_called_once_with(
            "https://us.api.concursolutions.com/api/v3.0/expense/reports",
            headers={
                "Authorization": "Bearer mock_access_token_123",
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            params={
                "user": self.user_login_id,
                "limit": 10
            },
            timeout=15
        )

    @patch("requests.post")
    def test_list_reports_forbidden(self, mock_post):
        # Bypass get_token mock with direct assignment to avoid patching requests.post multiple times
        self.client._access_token = "cached_token"
        self.client._token_expires_at = time.time() + 1000

        with patch("requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 403
            mock_response.text = "Forbidden - Invalid Scopes"
            mock_get.return_value = mock_response

            with self.assertRaises(ConcurAPIError) as ctx:
                self.client.list_reports(self.user_login_id)
            
            self.assertEqual(ctx.exception.status_code, 403)
            self.assertIn("Forbidden", ctx.exception.response_text)

    @patch("requests.post")
    def test_create_draft_report_success(self, mock_post):
        # Bypass get_token mock with direct assignment
        self.client._access_token = "cached_token"
        self.client._token_expires_at = time.time() + 1000

        # Mock creating report POST call
        mock_create_response = MagicMock()
        mock_create_response.status_code = 201
        mock_create_response.json.return_value = {
            "ReportID": "NEW_REPORT_ID",
            "Name": "Draft Report 1",
            "ReportStatus": "Not Submitted"
        }
        mock_post.return_value = mock_create_response

        # Execute
        report = self.client.create_draft_report(
            user_login_id=self.user_login_id,
            name="Draft Report 1",
            purpose="Testing",
            comment="API test"
        )

        # Verify
        self.assertEqual(report["ReportID"], "NEW_REPORT_ID")
        self.assertEqual(report["Name"], "Draft Report 1")
        
        mock_post.assert_called_once_with(
            "https://us.api.concursolutions.com/api/v3.0/expense/reports",
            headers={
                "Authorization": "Bearer cached_token",
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            params={
                "user": self.user_login_id
            },
            json={
                "Name": "Draft Report 1",
                "Purpose": "Testing",
                "Comment": "API test"
            },
            timeout=15
        )


if __name__ == "__main__":
    unittest.main()
