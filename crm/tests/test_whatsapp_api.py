"""
Tests unitarios para las APIs de WhatsApp con variables nombradas.

Ejecutar con:
  bench --site <site> run-tests --module crm.tests.test_whatsapp_api
"""

import json
from datetime import date, datetime, time
from decimal import Decimal
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase


class TestWhatsAppAPI(FrappeTestCase):
	"""Tests para APIs de WhatsApp con soporte de variables nombradas."""

	@classmethod
	def setUpClass(cls):
		"""Configuración inicial para todos los tests."""
		super().setUpClass()

	@classmethod
	def tearDownClass(cls):
		"""Limpieza después de todos los tests."""
		super().tearDownClass()

	@patch("crm.api.whatsapp.frappe.get_doc")
	def test_get_template_variables_extracts_named_variables(self, get_doc):
		"""Test que extrae correctamente variables nombradas del template."""
		from crm.api.whatsapp import get_template_variables

		get_doc.return_value = frappe._dict(
			template="Hola {{nombre}}, tu asesor es {{asesor}}. Disciplina: {{disciplina}}"
		)
		variables = get_template_variables("test_template_named")

		# Debe extraer 3 variables únicas
		self.assertEqual(len(variables), 3)

		# Verificar que las variables están ordenadas alfabéticamente
		variable_names = [v["name"] for v in variables]
		self.assertEqual(variable_names, ["asesor", "disciplina", "nombre"])

		# Verificar estructura de cada variable
		for var in variables:
			self.assertIn("name", var)
			self.assertIn("placeholder", var)
			self.assertTrue(var["placeholder"].startswith("{{"))
			self.assertTrue(var["placeholder"].endswith("}}"))

	@patch("crm.api.whatsapp.frappe.get_doc")
	def test_get_template_variables_empty_for_no_vars(self, get_doc):
		"""Test que retorna lista vacía para template sin variables."""
		from crm.api.whatsapp import get_template_variables

		get_doc.return_value = frappe._dict(template="Hola, este es un mensaje sin variables.")
		variables = get_template_variables("test_template_no_vars")

		self.assertEqual(len(variables), 0)
		self.assertEqual(variables, [])

	@patch("crm.api.whatsapp.frappe.get_doc")
	def test_get_template_variables_removes_duplicates(self, get_doc):
		"""Test que elimina variables duplicadas."""
		from crm.api.whatsapp import get_template_variables

		get_doc.return_value = frappe._dict(template="Hola {{nombre}}, {{nombre}}. Tu asesor es {{asesor}}.")
		variables = get_template_variables("test_template_duplicates")

		# Debe extraer solo 2 variables únicas (nombre aparece 2 veces en el template)
		self.assertEqual(len(variables), 2)

		variable_names = [v["name"] for v in variables]
		self.assertIn("nombre", variable_names)
		self.assertIn("asesor", variable_names)

	@patch("crm.api.whatsapp.frappe.get_doc")
	def test_get_template_variables_ignores_invalid_format(self, get_doc):
		"""Test que ignora variables con formato inválido (mayúsculas, números)."""
		from crm.api.whatsapp import get_template_variables

		get_doc.return_value = frappe._dict(
			template="Hola {{Nombre}}, tu ID es {{123id}}, contacto: {{teléfono}}"
		)
		variables = get_template_variables("test_template_invalid_vars")

		# No debe extraer ninguna variable válida (todas tienen formato inválido)
		self.assertEqual(len(variables), 0)

	@patch("crm.api.whatsapp.frappe.new_doc")
	@patch("crm.api.whatsapp.validate_access")
	def test_send_whatsapp_template_with_body_param(self, validate_access, new_doc):
		"""Test que envía template con variables nombradas usando body_param."""
		from crm.api.whatsapp import send_whatsapp_template

		validate_access.return_value = MagicMock()
		message = MagicMock()
		message.name = "WHATSAPP-MESSAGE-001"
		new_doc.return_value = message

		message_name = send_whatsapp_template(
			reference_doctype="CRM Lead",
			reference_name="LEAD-001",
			template="test_template_named",
			to="521234567890",
			body_param={"nombre": "Juan", "asesor": "María", "disciplina": "Karate"},
		)

		self.assertEqual(message_name, "WHATSAPP-MESSAGE-001")
		body_data = json.loads(message.update.call_args.args[0]["body_param"])
		self.assertEqual(body_data["nombre"], "Juan")
		self.assertEqual(body_data["asesor"], "María")
		self.assertEqual(body_data["disciplina"], "Karate")
		validate_access.assert_called_once_with("CRM Lead", "LEAD-001")
		message.insert.assert_called_once_with(ignore_permissions=True)

	@patch("crm.api.whatsapp._build_whatsapp_body_param_from_mapping", return_value=None)
	@patch("crm.api.whatsapp.frappe.new_doc")
	@patch("crm.api.whatsapp.validate_access")
	def test_send_whatsapp_template_without_body_param(self, validate_access, new_doc, build_body_param):
		"""Test que envía template sin variables (body_param=None)."""
		from crm.api.whatsapp import send_whatsapp_template

		reference_doc = MagicMock()
		validate_access.return_value = reference_doc
		message = MagicMock()
		message.name = "WHATSAPP-MESSAGE-001"
		new_doc.return_value = message

		message_name = send_whatsapp_template(
			reference_doctype="CRM Lead",
			reference_name="LEAD-001",
			template="test_template_no_vars",
			to="521234567890",
			body_param=None,
		)

		self.assertEqual(message_name, "WHATSAPP-MESSAGE-001")
		self.assertIsNone(message.update.call_args.args[0]["body_param"])
		validate_access.assert_called_once_with("CRM Lead", "LEAD-001")
		build_body_param.assert_called_once_with(reference_doc, "test_template_no_vars")
		message.insert.assert_called_once_with(ignore_permissions=True)

	def test_send_whatsapp_template_validates_access(self):
		"""Test que valida permisos de acceso al documento de referencia."""
		from crm.api.whatsapp import send_whatsapp_template

		# Intentar enviar a un Lead que no existe
		with self.assertRaises(frappe.DoesNotExistError):
			send_whatsapp_template(
				reference_doctype="CRM Lead",
				reference_name="NON_EXISTENT_LEAD",
				template="test_template_named",
				to="521234567890",
				body_param={"nombre": "Test"},
			)

	def test_mapping_fieldname_rejects_malformed_field_values(self):
		"""Test que ignora mappings con field no-string o vacío."""
		from crm.api.whatsapp import _get_mapping_fieldname

		self.assertIsNone(_get_mapping_fieldname({"source": "field", "field": ["first_name"]}))
		self.assertIsNone(_get_mapping_fieldname({"source": "field", "field": 123}))
		self.assertIsNone(_get_mapping_fieldname({"source": "field", "field": ""}))
		self.assertIsNone(_get_mapping_fieldname(""))
		self.assertEqual(_get_mapping_fieldname({"source": "field", "field": "first_name"}), "first_name")
		self.assertEqual(_get_mapping_fieldname("first_name"), "first_name")

	@patch("crm.api.whatsapp.frappe.new_doc")
	@patch("crm.api.whatsapp.frappe.get_doc")
	@patch("crm.api.whatsapp._get_whatsapp_visible_field_snapshots")
	@patch("crm.api.whatsapp.validate_access")
	def test_send_whatsapp_template_builds_body_param_from_saved_visible_field_mapping(
		self, validate_access, visible_fields, get_doc, new_doc
	):
		"""Test que el envío resuelve solo mappings guardados visibles."""
		from crm.api.whatsapp import send_whatsapp_template

		reference_doc = MagicMock()
		validate_access.return_value = reference_doc
		visible_fields.return_value = [
			{
				"fieldname": "__assigned_advisor_first_name",
				"label": "Assigned Advisor First Name",
				"value": "María",
			},
			{"fieldname": "first_name", "label": "First Name", "value": "Juan"},
		]

		template = MagicMock()
		template.named_field_mapping = json.dumps(
			{
				"asesor": {
					"source": "field",
					"field": "__assigned_advisor_first_name",
				},
				"nombre": "first_name",
				"private": "private_notes",
				"manual": {"source": "manual"},
			}
		)
		get_doc.return_value = template

		message = MagicMock()
		message.name = "WHATSAPP-MESSAGE-001"
		new_doc.return_value = message

		message_name = send_whatsapp_template(
			reference_doctype="CRM Lead",
			reference_name="LEAD-001",
			template="test_template_named",
			to="521234567890",
			body_param=None,
		)

		self.assertEqual(message_name, "WHATSAPP-MESSAGE-001")
		body_param = json.loads(message.update.call_args.args[0]["body_param"])
		self.assertEqual(body_param, {"asesor": "María", "nombre": "Juan"})
		validate_access.assert_called_once_with("CRM Lead", "LEAD-001")
		get_doc.assert_called_once_with("WhatsApp Templates", "test_template_named")
		visible_fields.assert_called_once_with(reference_doc)


class TestWhatsAppPreviewFields(FrappeTestCase):
	"""Tests for the permission-scoped WhatsApp preview field contract."""

	def make_field(
		self,
		fieldname,
		fieldtype="Data",
		label=None,
		hidden=0,
		is_virtual=0,
		mask=None,
		permlevel=0,
	):
		return frappe._dict(
			fieldname=fieldname,
			fieldtype=fieldtype,
			label=label,
			hidden=hidden,
			is_virtual=is_virtual,
			mask=mask,
			permlevel=permlevel,
		)

	def make_meta(self, fields, permitted_fieldnames):
		meta = frappe._dict(fields=fields)
		meta.get_permitted_fieldnames = MagicMock(return_value=permitted_fieldnames)
		fields_by_name = {field.fieldname: field for field in fields}
		meta.get_field = MagicMock(side_effect=fields_by_name.get)
		return meta

	@patch("crm.api.whatsapp.frappe.get_meta")
	@patch("crm.api.whatsapp.frappe.get_doc")
	@patch("crm.api.whatsapp.frappe.get_roles", return_value=["Sales User"])
	def test_returns_only_permitted_displayable_standard_and_custom_fields(
		self, _get_roles, get_doc, get_meta
	):
		from crm.api.whatsapp import get_whatsapp_preview_fields

		doc = MagicMock()
		doc.has_permission.return_value = True
		values = {
			"first_name": "Ada",
			"custom_region": "North",
			"custom_empty": None,
			"private_notes": "high-permission secret",
			"hidden_value": "hidden",
			"virtual_value": "computed",
			"masked_value": "masked",
			"html_value": "<b>unsafe</b>",
			"password_value": "secret",
			"code_value": "print('unsafe')",
			"json_value": '{"unsafe": true}',
			"table_value": [{"name": "secret"}],
			"table_multi_value": ["secret"],
			"attach_value": "/private/file.pdf",
			"attach_image_value": "/private/image.png",
			"unknown_value": "excluded",
		}
		doc.get.side_effect = values.get
		get_doc.return_value = doc
		get_meta.return_value = self.make_meta(
			[
				self.make_field("first_name", label="First Name"),
				self.make_field("custom_region", label="Region"),
				self.make_field("custom_empty", label="Empty custom field"),
				self.make_field("private_notes", label="Private Notes", permlevel=1),
				self.make_field("hidden_value", hidden=1),
				self.make_field("virtual_value", is_virtual=1),
				self.make_field("masked_value", mask="X"),
				self.make_field("html_value", fieldtype="HTML"),
				self.make_field("password_value", fieldtype="Password"),
				self.make_field("code_value", fieldtype="Code"),
				self.make_field("json_value", fieldtype="JSON"),
				self.make_field("table_value", fieldtype="Table"),
				self.make_field("table_multi_value", fieldtype="Table MultiSelect"),
				self.make_field("attach_value", fieldtype="Attach"),
				self.make_field("attach_image_value", fieldtype="Attach Image"),
				self.make_field("unknown_value", fieldtype="Unknown Type"),
			],
			[
				"first_name",
				"custom_region",
				"custom_empty",
				"hidden_value",
				"virtual_value",
				"masked_value",
				"html_value",
				"password_value",
				"code_value",
				"json_value",
				"table_value",
				"table_multi_value",
				"attach_value",
				"attach_image_value",
				"unknown_value",
			],
		)

		result = get_whatsapp_preview_fields("CRM Lead", "LEAD-001")

		self.assertEqual(
			result,
			{
				"fields": [
					{"fieldname": "first_name", "label": "First Name", "value": "Ada"},
					{"fieldname": "custom_region", "label": "Region", "value": "North"},
					{"fieldname": "custom_empty", "label": "Empty custom field", "value": None},
				]
			},
		)
		get_meta.return_value.get_permitted_fieldnames.assert_called_once_with(
			user=frappe.session.user,
			permission_type="read",
			with_virtual_fields=False,
		)
		self.assertEqual(
			[call.args[0] for call in doc.get.call_args_list],
			["first_name", "custom_region", "custom_empty"],
		)

	@patch("crm.api.whatsapp.frappe.get_doc")
	@patch("crm.api.whatsapp.frappe.get_roles", return_value=[])
	def test_role_denial_happens_before_record_access(self, _get_roles, get_doc):
		from crm.api.whatsapp import get_whatsapp_preview_fields

		with self.assertRaises(frappe.PermissionError) as raised:
			get_whatsapp_preview_fields("CRM Lead", "LEAD-001")

		self.assertEqual(str(raised.exception), "Not permitted to preview fields for this record.")
		get_doc.assert_not_called()

	@patch("crm.api.whatsapp.frappe.db.get_value")
	@patch("crm.api.whatsapp.frappe.get_meta")
	@patch("crm.api.whatsapp.frappe.get_doc")
	@patch("crm.api.whatsapp.frappe.get_roles", return_value=["Sales User"])
	def test_includes_derived_assigned_advisor_fields_when_owner_field_is_permitted(
		self, _get_roles, get_doc, get_meta, get_value
	):
		from crm.api.whatsapp import get_whatsapp_preview_fields

		doc = MagicMock()
		doc.doctype = "CRM Lead"
		doc.has_permission.return_value = True
		doc.get.side_effect = {"lead_owner": "maria@example.com"}.get
		get_doc.return_value = doc
		get_meta.return_value = self.make_meta(
			[self.make_field("lead_owner", fieldtype="Link", label="Lead Owner")],
			["lead_owner"],
		)
		get_value.return_value = frappe._dict(full_name="María López", first_name="María", last_name="López")

		result = get_whatsapp_preview_fields("CRM Lead", "LEAD-001")

		self.assertEqual(
			result,
			{
				"fields": [
					{"fieldname": "lead_owner", "label": "Lead Owner", "value": "maria@example.com"},
					{
						"fieldname": "__assigned_advisor_full_name",
						"label": "Assigned Advisor Full Name",
						"value": "María López",
					},
					{
						"fieldname": "__assigned_advisor_first_name",
						"label": "Assigned Advisor First Name",
						"value": "María",
					},
				]
			},
		)

	@patch("crm.api.whatsapp.frappe.db.get_value")
	@patch("crm.api.whatsapp.frappe.get_meta")
	@patch("crm.api.whatsapp.frappe.get_doc")
	@patch("crm.api.whatsapp.frappe.get_roles", return_value=["Sales User"])
	def test_omits_derived_assigned_advisor_fields_when_owner_field_is_masked(
		self, _get_roles, get_doc, get_meta, get_value
	):
		from crm.api.whatsapp import get_whatsapp_preview_fields

		doc = MagicMock()
		doc.doctype = "CRM Lead"
		doc.has_permission.return_value = True
		doc.get.side_effect = {"lead_owner": "maria@example.com"}.get
		get_doc.return_value = doc
		get_meta.return_value = self.make_meta(
			[self.make_field("lead_owner", fieldtype="Link", label="Lead Owner", mask="X")],
			["lead_owner"],
		)

		result = get_whatsapp_preview_fields("CRM Lead", "LEAD-001")

		self.assertEqual(result, {"fields": []})
		get_value.assert_not_called()

	@patch("crm.api.whatsapp.frappe.get_meta")
	@patch("crm.api.whatsapp.frappe.get_doc")
	@patch("crm.api.whatsapp.frappe.get_roles", return_value=["Sales User"])
	def test_record_denial_and_missing_record_use_same_generic_error(self, _get_roles, get_doc, get_meta):
		from crm.api.whatsapp import get_whatsapp_preview_fields

		denied_doc = MagicMock()
		denied_doc.has_permission.return_value = False
		get_doc.return_value = denied_doc
		with self.assertRaises(frappe.PermissionError) as denied:
			get_whatsapp_preview_fields("CRM Lead", "RESTRICTED-LEAD")

		get_doc.side_effect = frappe.DoesNotExistError
		with self.assertRaises(frappe.PermissionError) as missing:
			get_whatsapp_preview_fields("CRM Lead", "MISSING-LEAD")

		self.assertEqual(str(denied.exception), str(missing.exception))
		get_meta.assert_not_called()

	@patch("crm.api.whatsapp.frappe.get_doc")
	@patch("crm.api.whatsapp.frappe.get_roles", return_value=["Sales User"])
	def test_rejects_unsupported_doctype_and_empty_record_name(self, _get_roles, get_doc):
		from crm.api.whatsapp import get_whatsapp_preview_fields

		for doctype, name in [("User", "Administrator"), ("CRM Lead", " ")]:
			with self.subTest(doctype=doctype, name=name):
				with self.assertRaises(frappe.PermissionError):
					get_whatsapp_preview_fields(doctype, name)

		get_doc.assert_not_called()

	@patch("crm.api.whatsapp.frappe.get_meta")
	@patch("crm.api.whatsapp.frappe.get_doc")
	@patch("crm.api.whatsapp.frappe.get_roles", return_value=["Sales User"])
	def test_permission_helper_failure_fails_closed(self, _get_roles, get_doc, get_meta):
		from crm.api.whatsapp import get_whatsapp_preview_fields

		doc = MagicMock()
		doc.has_permission.return_value = True
		get_doc.return_value = doc
		meta = self.make_meta([self.make_field("first_name")], ["first_name"])
		meta.get_permitted_fieldnames.side_effect = RuntimeError("permission lookup failed")
		get_meta.return_value = meta

		with self.assertRaises(frappe.PermissionError) as raised:
			get_whatsapp_preview_fields("CRM Lead", "LEAD-001")

		self.assertEqual(str(raised.exception), "Not permitted to preview fields for this record.")
		doc.get.assert_not_called()

	@patch("crm.api.whatsapp.frappe.get_meta")
	@patch("crm.api.whatsapp.frappe.get_doc")
	@patch("crm.api.whatsapp.frappe.get_roles", return_value=["Sales User"])
	def test_serializes_known_scalar_types_and_omits_unexpected_objects(self, _get_roles, get_doc, get_meta):
		from crm.api.whatsapp import get_whatsapp_preview_fields

		doc = MagicMock()
		doc.has_permission.return_value = True
		doc.get.side_effect = {
			"date_value": date(2026, 9, 28),
			"datetime_value": datetime(2026, 9, 28, 12, 30),
			"time_value": time(9, 15),
			"decimal_value": Decimal("123.450"),
			"unexpected_value": object(),
		}.get
		get_doc.return_value = doc
		get_meta.return_value = self.make_meta(
			[
				self.make_field("date_value", fieldtype="Date"),
				self.make_field("datetime_value", fieldtype="Datetime"),
				self.make_field("time_value", fieldtype="Time"),
				self.make_field("decimal_value", fieldtype="Currency"),
				self.make_field("unexpected_value", fieldtype="Data"),
			],
			[
				"date_value",
				"datetime_value",
				"time_value",
				"decimal_value",
				"unexpected_value",
			],
		)

		result = get_whatsapp_preview_fields("CRM Lead", "LEAD-001")

		self.assertEqual(
			result,
			{
				"fields": [
					{"fieldname": "date_value", "label": "date_value", "value": "2026-09-28"},
					{
						"fieldname": "datetime_value",
						"label": "datetime_value",
						"value": "2026-09-28T12:30:00",
					},
					{"fieldname": "time_value", "label": "time_value", "value": "09:15:00"},
					{"fieldname": "decimal_value", "label": "decimal_value", "value": "123.450"},
				]
			},
		)

	@patch("crm.api.whatsapp.frappe.get_meta")
	@patch("crm.api.whatsapp.frappe.get_doc")
	@patch("crm.api.whatsapp.frappe.get_roles", return_value=["Sales User"])
	def test_missing_permission_helper_fails_closed(self, _get_roles, get_doc, get_meta):
		from crm.api.whatsapp import get_whatsapp_preview_fields

		doc = MagicMock()
		doc.has_permission.return_value = True
		get_doc.return_value = doc
		get_meta.return_value = frappe._dict(fields=[self.make_field("first_name")])

		with self.assertRaises(frappe.PermissionError):
			get_whatsapp_preview_fields("CRM Lead", "LEAD-001")

		doc.get.assert_not_called()
