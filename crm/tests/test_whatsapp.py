# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import MagicMock, patch

import frappe

from crm.api.whatsapp import notify_agent, on_update, validate
from crm.tests import CRMTestCase as FrappeTestCase
from crm.utils import phones_match


class TestWhatsAppHooks(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	# --- validate() ---

	def test_validate_sets_reference_when_contact_found(self):
		"""validate() links the doc when a matching Contact/Lead is found"""
		doc = MagicMock()
		doc.type = "Incoming"
		doc.get.return_value = "+15551234567"

		with patch(
			"crm.api.whatsapp.get_contact_lead_or_deal_from_number",
			return_value=("LEAD-0001", "CRM Lead"),
		):
			validate(doc, None)

		self.assertEqual(doc.reference_doctype, "CRM Lead")
		self.assertEqual(doc.reference_name, "LEAD-0001")

	def test_validate_skips_reference_when_no_contact_found(self):
		"""validate() leaves reference fields untouched when number is unknown"""
		doc = MagicMock()
		doc.type = "Incoming"
		doc.get.return_value = "+15559999999"
		doc.reference_doctype = None
		doc.reference_name = None

		with patch(
			"crm.api.whatsapp.get_contact_lead_or_deal_from_number",
			return_value=(None, None),
		):
			validate(doc, None)

		self.assertIsNone(doc.reference_doctype)
		self.assertIsNone(doc.reference_name)

	def test_validate_logs_error_on_exception(self):
		"""validate() catches lookup exceptions and logs them instead of raising"""
		doc = MagicMock()
		doc.type = "Incoming"
		doc.get.return_value = "invalid-number"

		with (
			patch(
				"crm.api.whatsapp.get_contact_lead_or_deal_from_number",
				side_effect=Exception("parse error"),
			),
			patch("frappe.log_error") as mock_log,
		):
			validate(doc, None)  # must not raise

		mock_log.assert_called_once()

	# --- notify_agent() ---

	def test_notify_agent_returns_early_when_no_reference(self):
		"""notify_agent() skips notification when reference_doctype and reference_name are absent"""
		doc = MagicMock()
		doc.type = "Incoming"
		doc.reference_doctype = None
		doc.reference_name = None

		with patch("crm.api.whatsapp.get_assigned_users") as mock_users:
			notify_agent(doc)  # must not raise

		mock_users.assert_not_called()

	def test_notify_agent_returns_early_when_reference_doctype_missing(self):
		"""notify_agent() skips notification when only reference_doctype is absent"""
		doc = MagicMock()
		doc.type = "Incoming"
		doc.reference_doctype = ""
		doc.reference_name = "LEAD-0001"

		with patch("crm.api.whatsapp.get_assigned_users") as mock_users:
			notify_agent(doc)

		mock_users.assert_not_called()


class TestPhonesMatch(FrappeTestCase):
	"""Tests for phones_match() robust phone number comparison."""

	def test_exact_match(self):
		"""Identical numbers match"""
		self.assertTrue(phones_match("5216691252211", "5216691252211"))

	def test_plus_prefix(self):
		"""Numbers with and without '+' prefix match"""
		self.assertTrue(phones_match("+5216691252211", "5216691252211"))

	def test_mx_trunk_prefix(self):
		"""Mexican mobile: with trunk '1' matches without trunk '1'"""
		# Meta webhook sends: +52 1 669 125 2211 (E.164 with mobile trunk)
		# Stored as: 526691252211 (without the '1')
		self.assertTrue(phones_match("5216691252211", "526691252211"))

	def test_ar_trunk_prefix(self):
		"""Argentine mobile: with trunk '9' matches without trunk '9'"""
		# Meta webhook sends: +54 9 11 5555 1234 (E.164 with mobile trunk)
		# Stored as: 541155551234 (without the '9')
		self.assertTrue(phones_match("5491155551234", "541155551234"))

	def test_different_numbers_no_match(self):
		"""Different numbers don't match"""
		self.assertFalse(phones_match("5216691252211", "5216699999999"))

	def test_empty_numbers_no_match(self):
		"""Empty numbers don't match"""
		self.assertFalse(phones_match("", "5216691252211"))
		self.assertFalse(phones_match("5216691252211", ""))
		self.assertFalse(phones_match("", ""))

	def test_short_numbers_no_match(self):
		"""Numbers shorter than 10 digits don't match via fallback"""
		self.assertFalse(phones_match("12345", "123456"))


class TestOnUpdateRealtime(FrappeTestCase):
	"""Tests for on_update() realtime publishing."""

	def test_on_update_publishes_to_doc_room(self):
		"""on_update() publishes to the reference doc's room, not Guest's room"""
		doc = MagicMock()
		doc.reference_doctype = "CRM Lead"
		doc.reference_name = "CRM-LEAD-001"

		with patch("crm.api.whatsapp.frappe.publish_realtime") as mock_publish:
			on_update(doc, None)

			mock_publish.assert_called_once_with(
				event="whatsapp_message",
				message={
					"reference_doctype": "CRM Lead",
					"reference_name": "CRM-LEAD-001",
				},
				doctype="CRM Lead",
				docname="CRM-LEAD-001",
			)
