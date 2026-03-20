import unittest

from kaanoon_test.system_adapters.clarification_engine import ClarificationSession


class ClarificationRoutingRegressions(unittest.TestCase):
    def setUp(self):
        self.session = ClarificationSession.__new__(ClarificationSession)

    def test_dense_case_matrix_is_not_treated_as_academic_direct(self):
        query = (
            "A technology company launches a mobile payment application that allows users to store money, "
            "make payments, and access instant micro-loans. During registration users must accept mandatory "
            "data sharing, broad consent clauses, algorithmic credit scoring without explanation, and an "
            "arbitration clause. Two years later a data breach exposes financial data, users receive phishing "
            "attempts, a researcher finds data sharing with third-party marketing firms, consumer complaints are "
            "filed, and a PIL is filed before the High Court."
        )
        self.assertFalse(self.session._is_academic_legal_analysis(query))

    def test_explicit_one_shot_instruction_can_bypass_case_matrix_clarification(self):
        query = (
            "Provide a one-shot answer without asking follow-up questions. Analyze separately the "
            "constitutional, statutory, and contractual issues. "
            "A technology company launches a mobile payment application that allows users to store money, "
            "make payments, and access instant micro-loans. During registration users must accept mandatory "
            "data sharing, broad consent clauses, algorithmic credit scoring without explanation, and an "
            "arbitration clause. Two years later a data breach exposes financial data and users file complaints."
        )
        self.assertTrue(self.session._is_academic_legal_analysis(query))

    def test_fintech_privacy_case_matrix_is_not_simple_direct(self):
        query = (
            "A Bengaluru-based digital payments company provides instant small-ticket consumer credit through a "
            "mobile app. The company profiles users using transaction metadata, location patterns, and device "
            "identifiers, then auto-rejects several applicants without explanation. Separately, a database leak "
            "exposed names, Aadhaar-linked KYC details, and transaction histories of nearly 50,000 users. The "
            "terms of service contain a broad arbitration clause and a waiver of class or representative "
            "proceedings. A public interest group now wants to challenge the platform practice and seek "
            "compensation, injunctive relief, and disclosure of the scoring logic. Analyze the possible causes "
            "of action and defenses under Indian law, including privacy, data protection, consumer protection, "
            "platform liability, arbitration, and maintainability of a PIL."
        )
        self.assertTrue(self.session._looks_like_complex_case_matrix(query))
        self.assertFalse(self.session._is_simple_query(query))


if __name__ == "__main__":
    unittest.main()