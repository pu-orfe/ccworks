
import os
import sys
import json
import unittest
from http.server import HTTPServer
import threading

# Adjust path to import src and tests modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tests.mock_concur_server import MockConcurServer
from ccworks.browser_client import ConcurBrowserClient

DUMMY_SESSION = {
    "cookies": [
        {
            "name": "concur_mock_session",
            "value": "active_state",
            "domain": "127.0.0.1",
            "path": "/",
            "expires": -1,
            "httpOnly": True,
            "secure": False,
            "sameSite": "Lax"
        }
    ],
    "origins": []
}

class TestJustificationAndClassification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.session_file = "concur_session_test_just.json"
        with open(cls.session_file, "w") as f:
            json.dump(DUMMY_SESSION, f)
        
        cls.server = MockConcurServer(host="127.0.0.1", port=8090)
        cls.server.start()
        
        cls.client = ConcurBrowserClient(
            session_file=cls.session_file,
            base_url="http://127.0.0.1:8090"
        )

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()
        if os.path.exists(cls.session_file):
            os.remove(cls.session_file)

    def test_01_report_header_justification(self):
        """Test updating report header purpose and comment."""
        report_name = "Header Justification Test"
        purpose = "Test Purpose"
        comment = "Test Comment"
        
        # 1. Create a report
        self.client.create_draft_report(name=report_name, purpose="Initial", comment="Initial")
        
        # 2. Update the header
        res = self.client.update_report(
            old_name=report_name,
            new_name=report_name,
            new_purpose=purpose,
            new_comment=comment,
            headless=True
        )
        self.assertTrue(res["success"])
        
        # 3. Verify via details
        details = self.client.get_report_details(name=report_name, headless=True)
        self.assertEqual(details["purpose"], purpose)
        self.assertEqual(details["comment"], comment)

    def test_02_transaction_justification_and_classification(self):
        """Test updating transaction fields (type, purpose, comment)."""
        report_name = "Transaction Justification Test"
        
        # 1. Create a report (mock server automatically adds 2 transactions)
        self.client.create_draft_report(name=report_name)
        
        # 2. Update first transaction
        target_type = "Software"
        target_purpose = "Software justification"
        target_comment = "Software comment"
        
        res = self.client.update_report_transaction(
            report_name=report_name,
            transaction_indices=1,
            expense_type=target_type,
            business_purpose=target_purpose,
            comment=target_comment,
            headless=True
        )
        self.assertTrue(res["success"])
        
        # 3. Verify via details (deep scan)
        details = self.client.get_report_details(name=report_name, deep=True, headless=True)
        self.assertTrue(details["success"])
        self.assertGreaterEqual(len(details["expenses"]), 1)
        
        tx = details["expenses"][0]
        # In mock server, deep scan might return the values we set
        self.assertEqual(tx["expense_type"], target_type)
        self.assertEqual(tx["business_purpose"], target_purpose)
        self.assertEqual(tx["comment"], target_comment)

    def test_03_transaction_update_verification_failure(self):
        """Test that update fails correctly when field update fails to stick (e.g. invalid type)."""
        report_name = "Verification Failure Test"
        self.client.create_draft_report(name=report_name)
        
        # Update with an invalid type not in the select options
        res = self.client.update_report_transaction(
            report_name=report_name,
            transaction_indices=1,
            expense_type="Nonexistent Type",
            headless=True
        )
        
        # Since "Nonexistent Type" is not a valid option, selecting it will fail,
        # and success should be False.
        self.assertFalse(res["results"][0]["success"])
        self.assertFalse(res["success"])

    def test_04_bulk_apply_json_with_receipt(self):
        """Test applying JSON updates with a simulated receipt upload."""
        report_name = "Bulk Apply JSON Test"
        self.client.create_draft_report(name=report_name)
        
        # Create a dummy receipt file
        dummy_receipt = "temp_receipt.png"
        with open(dummy_receipt, "w") as f:
            f.write("dummy image data")
            
        try:
            updates = [
                {
                    "index": 0,
                    "expense_type": "Software",
                    "business_purpose": "Bulk purpose",
                    "comment": "Bulk comment",
                    "receipt_file_path": dummy_receipt
                }
            ]
            
            res = self.client.apply_json_updates(
                report_name=report_name,
                expenses=updates,
                headless=True
            )
            self.assertTrue(res["success"])
            self.assertTrue(res["results"][0]["success"])
        finally:
            if os.path.exists(dummy_receipt):
                os.remove(dummy_receipt)

if __name__ == "__main__":
    unittest.main()
