import unittest

from src.email_content import get_greeting_name


class GreetingNameTests(unittest.TestCase):
    def test_greeting_name_spain_direct_generic_talento(self) -> None:
        value = get_greeting_name("Talento y Personas", country="spain", contact_type="direct_recruiter")
        self.assertEqual(value, "equipo de Talento")

    def test_greeting_name_spain_direct_generic_rrhh(self) -> None:
        value = get_greeting_name("Recursos Humanos", country="spain", contact_type="direct_recruiter")
        self.assertEqual(value, "equipo de Talento")

    def test_greeting_name_uk_direct_people_team(self) -> None:
        value = get_greeting_name("People Team", country="uk", contact_type="direct_recruiter")
        self.assertEqual(value, "Talent team")

    def test_greeting_name_uk_real_person(self) -> None:
        value = get_greeting_name("Alexander Biro", country="uk", contact_type="general")
        self.assertEqual(value, "Alexander")

    def test_greeting_name_spain_real_person(self) -> None:
        value = get_greeting_name("María López", country="spain", contact_type="direct_recruiter")
        self.assertEqual(value, "María")

    def test_talent_email_spain_forces_talent_team(self) -> None:
        value = get_greeting_name(
            "Beluga",
            country="spain",
            contact_type="direct_recruiter",
            company_name="Beluga Linguistics",
            email="talent@belugalinguistics.com",
        )
        self.assertEqual(value, "equipo de Talento")

    def test_hr_email_spain_forces_talent_team(self) -> None:
        value = get_greeting_name(
            "HR Team",
            country="spain",
            contact_type="direct_recruiter",
            company_name="Company",
            email="hr@company.com",
        )
        self.assertEqual(value, "equipo de Talento")

    def test_rrhh_email_spain_forces_talent_team(self) -> None:
        value = get_greeting_name(
            "RRHH",
            country="spain",
            contact_type="direct_recruiter",
            company_name="Company",
            email="rrhh@company.es",
        )
        self.assertEqual(value, "equipo de Talento")

    def test_careers_email_uk_forces_talent_team(self) -> None:
        value = get_greeting_name(
            "Careers",
            country="uk",
            contact_type="direct_recruiter",
            company_name="Company",
            email="careers@company.co.uk",
        )
        self.assertEqual(value, "Talent team")

    def test_info_email_spain_generic_team(self) -> None:
        value = get_greeting_name(
            "Info",
            country="spain",
            contact_type="general",
            company_name="Company",
            email="info@company.es",
        )
        self.assertEqual(value, "equipo")

    def test_real_person_with_email_spain(self) -> None:
        value = get_greeting_name(
            "María García",
            country="spain",
            contact_type="direct_recruiter",
            company_name="Company",
            email="maria.garcia@company.es",
        )
        self.assertEqual(value, "María")

    def test_real_person_with_email_uk(self) -> None:
        value = get_greeting_name(
            "Alexander Smith",
            country="uk",
            contact_type="general",
            company_name="Company",
            email="alexander@company.com",
        )
        self.assertEqual(value, "Alexander")


if __name__ == "__main__":
    unittest.main()
