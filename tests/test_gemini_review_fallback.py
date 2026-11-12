import unittest
from unittest.mock import patch

from app.schemas.review import CodeReviewResponse
from app.services import gemini_service


class OfflineReviewTests(unittest.TestCase):
    def test_detects_literal_division_by_zero_without_scoring(self):
        code = "def divide(value):\n    return value / 0\n"

        result = gemini_service.offline_review_code(code, "Python")
        response = CodeReviewResponse(**result)

        self.assertIsNone(result["overall_score"])
        self.assertIsNone(response.overall_score)
        self.assertEqual(result["source"], "Offline Static Analyzer")
        self.assertEqual(result["improved_code"], code)
        self.assertEqual(result["bugs"][0]["severity"], "High")
        self.assertIn("ZeroDivisionError", result["bugs"][0]["description"])

    def test_review_falls_back_when_gemini_fails(self):
        with patch.object(
            gemini_service,
            "generate_json",
            side_effect=RuntimeError("quota exhausted")
        ):
            result = gemini_service.review_code("value = 1", "Python")

        self.assertEqual(result["source"], "Offline Static Analyzer")
        self.assertIsNone(result["overall_score"])
        self.assertIn("not a full code review", result["summary"])

    def test_unsupported_language_is_reported_as_unanalyzed(self):
        result = gemini_service.offline_review_code("class Example {}", "Java")

        self.assertIsNone(result["overall_score"])
        self.assertIn("Python only", result["summary"])
        self.assertEqual(result["bugs"], [])


if __name__ == "__main__":
    unittest.main()
