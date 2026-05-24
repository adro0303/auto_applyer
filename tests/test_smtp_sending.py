import smtplib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.db.repository import Repository
from src.db.schema import init_db
from src.sending import NON_SENDABLE_MESSAGE_STATUSES, process_approved_batch
from src.smtp_errors import classify_smtp_exception, extract_smtp_code, is_temporary_smtp_code


class TestSmtpClassification(unittest.TestCase):
    def test_extract_451(self):
        exc = smtplib.SMTPDataError(451, b"4.3.0 Mail server temporarily rejected message")
        self.assertEqual(extract_smtp_code(exc), 451)
        self.assertTrue(is_temporary_smtp_code(451))

    def test_classify_451_as_uncertain(self):
        exc = smtplib.SMTPDataError(451, b"4.3.0 Mail server temporarily rejected message")
        self.assertEqual(classify_smtp_exception(exc)["kind"], "uncertain")

    def test_classify_550_as_failed(self):
        exc = smtplib.SMTPDataError(550, b"5.1.1 User unknown")
        self.assertEqual(classify_smtp_exception(exc)["kind"], "failed")

    def test_classify_auth_as_failed(self):
        exc = smtplib.SMTPAuthenticationError(535, b"Authentication failed")
        self.assertEqual(classify_smtp_exception(exc)["kind"], "failed")


class TestProcessApprovedBatch(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "test.sqlite"
        init_db(self.db_path)
        self.repo = Repository(self.db_path)
        self.message_id = self._seed_approved_message()

    def tearDown(self):
        self.tmp.cleanup()

    def _seed_approved_message(self) -> int:
        with self.repo.connect() as conn:
            conn.execute("INSERT INTO companies (name, country) VALUES ('Test Co', 'uk')")
            company_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.execute(
                """
                INSERT INTO contacts (company_id, email, name, status, lead_score)
                VALUES (?, 'test@example.com', 'Test User', 'drafted', 90)
                """,
                (company_id,),
            )
            contact_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.execute(
                """
                INSERT INTO messages (
                    contact_id, subject, body, template_type, campaign_country, status
                ) VALUES (?, 'Subj', 'Body', 'initial', 'uk', 'approved')
                """,
                (contact_id,),
            )
            return int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])

    @patch("src.sending.check_send_allowed")
    @patch("src.sending.send_email_live")
    def test_smtp_451_marks_send_unknown(self, mock_send, _mock_check):
        mock_send.side_effect = smtplib.SMTPDataError(
            451, b"4.3.0 Mail server temporarily rejected message"
        )
        messages = self.repo.get_approved_messages(country="uk")
        results = process_approved_batch(messages, dry_run=False, repo=self.repo)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["result"], "uncertain")
        self.assertTrue(results[0]["manual_check_required"])

        row = self.repo.get_message_by_id(self.message_id)
        self.assertEqual(row["status"], "send_unknown")

    @patch("src.sending.send_email_live")
    def test_send_unknown_not_selected_again(self, mock_send):
        with self.repo.connect() as conn:
            conn.execute(
                "UPDATE messages SET status = 'send_unknown' WHERE id = ?",
                (self.message_id,),
            )
        messages = self.repo.get_approved_messages(country="uk")
        self.assertEqual(len(messages), 0)
        mock_send.assert_not_called()

    def test_non_sendable_statuses_include_send_unknown(self):
        self.assertIn("send_unknown", NON_SENDABLE_MESSAGE_STATUSES)


if __name__ == "__main__":
    unittest.main()
