import unittest
from leavebot_copy.scripts.air_ticket_utils import next_air_ticket_eligibility

class TestAirTicketUtils(unittest.TestCase):
    def test_next_air_ticket_eligibility_multiple_formats(self):
        """Both date formats should parse correctly."""
        d1 = next_air_ticket_eligibility("10-Aug-2023")
        d2 = next_air_ticket_eligibility("2023-08-10")
        self.assertEqual(d1, "2025-08-09")
        self.assertEqual(d1, d2)

if __name__ == "__main__":
    unittest.main()
