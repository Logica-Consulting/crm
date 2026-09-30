import json
import math
from datetime import date, datetime, time
from decimal import Decimal

import frappe
from frappe import _
from frappe.permissions import add_permission, update_permission_property

from crm.api.doc import get_assigned_users
from crm.fcrm.doctype.crm_notification.crm_notification import notify_user
from crm.integrations.api import get_contact_lead_or_deal_from_number

ALLOWED_WHATSAPP_ROLES = ["System Manager", "Sales Manager", "Sales User"]

WHATSAPP_PREVIEW_DOCTYPES = {"CRM Lead", "CRM Deal"}
WHATSAPP_PREVIEW_FIELD_TYPES = {
	"Check",
	"Currency",
	"Data",
	"Date",
	"Datetime",
	"Float",
	"Int",
	"Link",
	"Long Text",
	"Percent",
	"Select",
	"Small Text",
	"Text",
	"Time",
}
WHATSAPP_PREVIEW_DENIED_MESSAGE = "Not permitted to preview fields for this record."
_UNSERIALIZABLE_WHATSAPP_PREVIEW_VALUE = object()


def validate_access(reference_doctype=None, reference_name=None, permtype="read"):
	if not any(role in ALLOWED_WHATSAPP_ROLES for role in frappe.get_roles()):
		frappe.throw(_("Only sales users can access WhatsApp features."), frappe.PermissionError)

	if reference_doctype and reference_name:
		if not frappe.db.exists(reference_doctype, reference_name):
			frappe.throw(
				_("Reference document {0} {1} does not exist.").format(reference_doctype, reference_name),
				frappe.DoesNotExistError,
			)
		reference_doc = frappe.get_doc(reference_doctype, reference_name)
		if not reference_doc.has_permission(permtype):
			frappe.throw(
				_("Not permitted to access reference document {0} {1}.").format(
					reference_doctype, reference_name
				),
				frappe.PermissionError,
			)
		return reference_doc

	return None


def validate(doc, method):
	phone_number = doc.get("from") if doc.type == "Incoming" else doc.get("to")
	if phone_number:
		try:
			name, doctype = get_contact_lead_or_deal_from_number(phone_number)
			if doctype and name is not None:
				doc.reference_doctype = doctype
				doc.reference_name = name
		except Exception:
			frappe.log_error(frappe.get_traceback(), "CRM WhatsApp: failed to resolve contact from number")


def on_update(doc, method):
	frappe.publish_realtime(
		event="whatsapp_message",
		message={
			"reference_doctype": doc.reference_doctype,
			"reference_name": doc.reference_name,
		},
		doctype=doc.reference_doctype,
		docname=doc.reference_name,
	)

	notify_agent(doc)


def notify_agent(doc):
	if doc.type == "Incoming":
		if not doc.reference_doctype or not doc.reference_name:
			return
		doctype = doc.reference_doctype
		if doctype and doctype.startswith("CRM "):
			doctype = doctype[4:].lower()
		safe_reference_name = frappe.utils.escape_html(doc.reference_name)
		notification_text = f"""
            <div class="mb-2 leading-5 text-ink-gray-5">
                <span class="font-medium text-ink-gray-9">{_("You")}</span>
                <span>{_("received a whatsapp message in {0}").format(doctype)}</span>
                <span class="font-medium text-ink-gray-9">{safe_reference_name}</span>
            </div>
        """
		assigned_users = get_assigned_users(doc.reference_doctype, doc.reference_name)
		for user in assigned_users:
			notify_user(
				{
					"owner": doc.owner,
					"assigned_to": user,
					"notification_type": "WhatsApp",
					"message": doc.message,
					"notification_text": notification_text,
					"reference_doctype": "WhatsApp Message",
					"reference_docname": doc.name,
					"redirect_to_doctype": doc.reference_doctype,
					"redirect_to_docname": doc.reference_name,
				}
			)


@frappe.whitelist()
def is_whatsapp_enabled():
	if not frappe.db.exists("DocType", "WhatsApp Settings"):
		return False
	default_outgoing = frappe.get_cached_value(
		"WhatsApp Settings", "WhatsApp Settings", "default_outgoing_account"
	)
	if not default_outgoing:
		return False
	status = frappe.get_cached_value("WhatsApp Account", default_outgoing, "status")
	return status == "Active"


@frappe.whitelist()
def is_whatsapp_installed():
	if not frappe.db.exists("DocType", "WhatsApp Settings"):
		return False
	return True


def _get_orphan_messages_by_number(mobile_no: str) -> list:
	"""
	Fetch WhatsApp Messages whose from/to matches mobile_no but reference is
	empty or 'Contact' (orphans from number-matching gaps).

	This is a defensive query that heals existing orphaned messages without
	requiring a data migration.
	"""
	from crm.utils import _normalize_phone_digits

	mobile_digits = _normalize_phone_digits(mobile_no)
	if len(mobile_digits) < 10:
		return []

	# Get all WhatsApp Messages with empty or Contact reference
	all_orphans = frappe.get_all(
		"WhatsApp Message",
		filters=[
			["reference_doctype", "in", ["", "Contact", None]],
		],
		fields=[
			"name",
			"type",
			"to",
			"from",
			"content_type",
			"message_type",
			"attach",
			"template",
			"use_template",
			"message_id",
			"is_reply",
			"reply_to_message_id",
			"creation",
			"message",
			"status",
			"reference_doctype",
			"reference_name",
			"template_parameters",
			"template_header_parameters",
		],
	)

	# Filter by number match (last 10 digits)
	matched = []
	for msg in all_orphans:
		from_digits = _normalize_phone_digits(msg.get("from"))
		to_digits = _normalize_phone_digits(msg.get("to"))
		if (from_digits and len(from_digits) >= 10 and from_digits[-10:] == mobile_digits[-10:]) or (
			to_digits and len(to_digits) >= 10 and to_digits[-10:] == mobile_digits[-10:]
		):
			matched.append(msg)

	return matched


@frappe.whitelist()
def get_whatsapp_messages(reference_doctype: str, reference_name: str):
	reference_doc = validate_access(reference_doctype, reference_name)
	# twilio integration app is not compatible with crm app
	# crm has its own twilio integration in built
	if "twilio_integration" in frappe.get_installed_apps():
		return []
	if not frappe.db.exists("DocType", "WhatsApp Message"):
		return []
	messages = []

	if reference_doctype == "CRM Deal":
		lead = reference_doc.get("lead")
		if lead:
			validate_access("CRM Lead", lead)
			messages = frappe.get_all(
				"WhatsApp Message",
				filters={
					"reference_doctype": "CRM Lead",
					"reference_name": lead,
				},
				fields=[
					"name",
					"type",
					"to",
					"from",
					"content_type",
					"message_type",
					"attach",
					"template",
					"use_template",
					"message_id",
					"is_reply",
					"reply_to_message_id",
					"creation",
					"message",
					"status",
					"reference_doctype",
					"reference_name",
					"template_parameters",
					"template_header_parameters",
				],
			)

	messages += frappe.get_all(
		"WhatsApp Message",
		filters={
			"reference_doctype": reference_doctype,
			"reference_name": reference_name,
		},
		fields=[
			"name",
			"type",
			"to",
			"from",
			"content_type",
			"message_type",
			"attach",
			"template",
			"use_template",
			"message_id",
			"is_reply",
			"reply_to_message_id",
			"creation",
			"message",
			"status",
			"reference_doctype",
			"reference_name",
			"template_parameters",
			"template_header_parameters",
		],
	)

	# Defensive: include orphan messages whose from/to matches the lead's mobile_no
	# even if reference_doctype is empty or "Contact" (heals number-matching gaps)
	if reference_doctype == "CRM Lead":
		mobile_no = reference_doc.get("mobile_no")
		if mobile_no:
			orphan_messages = _get_orphan_messages_by_number(mobile_no)
			messages += orphan_messages

	# Filter messages to get only Template messages
	template_messages = [message for message in messages if message["message_type"] == "Template"]

	# Iterate through template messages
	for template_message in template_messages:
		# Find the template that this message is using
		if not frappe.db.exists("WhatsApp Templates", template_message["template"]):
			continue
		template = frappe.get_doc("WhatsApp Templates", template_message["template"])

		if template:
			template_message["template_name"] = template.template_name
			if template_message["template_parameters"]:
				parameters = json.loads(template_message["template_parameters"])
				template.template = parse_template_parameters(template.template, parameters)

			template_message["template"] = template.template
			if template_message["template_header_parameters"]:
				header_parameters = json.loads(template_message["template_header_parameters"])
				template.header = parse_template_parameters(template.header, header_parameters)
			template_message["header"] = template.header
			template_message["footer"] = template.footer

	# Filter messages to get only reaction messages
	reaction_messages = [message for message in messages if message["content_type"] == "reaction"]
	reaction_messages.reverse()

	# Iterate through reaction messages
	for reaction_message in reaction_messages:
		# Find the message that this reaction is reacting to
		reacted_message = next(
			(m for m in messages if m["message_id"] == reaction_message["reply_to_message_id"]),
			None,
		)

		# If the reacted message is found, add the reaction to it
		if reacted_message:
			reacted_message["reaction"] = reaction_message["message"]

	for message in messages:
		from_name = get_from_name(message) if message["from"] else _("You")
		message["from_name"] = from_name
	# Filter messages to get only replies
	reply_messages = [message for message in messages if message["is_reply"]]

	# Iterate through reply messages
	for reply_message in reply_messages:
		# Find the message that this message is replying to
		replied_message = next(
			(m for m in messages if m["message_id"] == reply_message["reply_to_message_id"]),
			None,
		)

		# If the replied message is found, add the reply details to the reply message
		if replied_message:
			from_name = get_from_name(reply_message) if replied_message["from"] else _("You")
			message = replied_message["message"]
			if replied_message["message_type"] == "Template":
				message = replied_message["template"]
			reply_message["reply_message"] = message
			reply_message["header"] = replied_message.get("header") or ""
			reply_message["footer"] = replied_message.get("footer") or ""
			reply_message["reply_to"] = replied_message["name"]
			reply_message["reply_to_type"] = replied_message["type"]
			reply_message["reply_to_from"] = from_name

	return [message for message in messages if message["content_type"] != "reaction"]


@frappe.whitelist()
def create_whatsapp_message(
	reference_doctype: str,
	reference_name: str,
	message: str,
	to: str,
	attach: str,
	reply_to: str,
	content_type: str = "text",
):
	validate_access(reference_doctype, reference_name)
	doc = frappe.new_doc("WhatsApp Message")

	if reply_to:
		if not frappe.db.exists("WhatsApp Message", reply_to):
			frappe.throw(_("Referenced WhatsApp message does not exist."), frappe.DoesNotExistError)
		reply_doc = frappe.get_doc("WhatsApp Message", reply_to)
		if not reply_doc.has_permission("read"):
			frappe.throw(
				_("Not permitted to access the referenced WhatsApp message."), frappe.PermissionError
			)
		validate_access(reply_doc.reference_doctype, reply_doc.reference_name)
		doc.update(
			{
				"is_reply": True,
				"reply_to_message_id": reply_doc.message_id,
			}
		)

	doc.update(
		{
			"reference_doctype": reference_doctype,
			"reference_name": reference_name,
			"message": message or attach,
			"to": to,
			"attach": attach,
			"content_type": content_type,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name


@frappe.whitelist()
def get_template_variables(template: str) -> list[dict]:
	"""
	Extrae variables nombradas del body de una plantilla WhatsApp.
	
	Args:
		template: Nombre del documento WhatsApp Templates
		
	Returns:
		Lista de dicts con {name, placeholder} ordenados alfabéticamente
		
	Example:
		get_template_variables("sipra_bienvenida_con_formulario_-es_MX")
		→ [
			{"name": "asesor", "placeholder": "{{asesor}}"},
			{"name": "disciplina", "placeholder": "{{disciplina}}"},
			{"name": "nombre", "placeholder": "{{nombre}}"}
		  ]
	"""
	import re
	
	template_doc = frappe.get_doc("WhatsApp Templates", template)
	body = template_doc.template or ""
	
	# Regex para variables nombradas: solo minúsculas y guiones bajos
	# Ej: {{nombre}}, {{lead_owner}}, {{custom_field}}
	# NO match: {{Nombre}}, {{id123}}, {{teléfono}}
	pattern = r"\{\{([a-z][a-z0-9_]*)\}\}"
	matches = re.findall(pattern, body)
	
	# Eliminar duplicados y ordenar alfabéticamente
	unique_vars = sorted(set(matches))
	
	return [
		{"name": var, "placeholder": f"{{{{{var}}}}}"}
		for var in unique_vars
	]


def _deny_whatsapp_preview_access():
	frappe.throw(_(WHATSAPP_PREVIEW_DENIED_MESSAGE), frappe.PermissionError)


def _serialize_whatsapp_preview_value(value):
	"""Return only JSON-friendly scalar values for the preview contract."""
	if value is None:
		return value
	if type(value) in (str, int, bool):
		return value
	if type(value) is float:
		return value if math.isfinite(value) else _UNSERIALIZABLE_WHATSAPP_PREVIEW_VALUE
	if isinstance(value, (datetime, date, time)):
		return value.isoformat()
	if isinstance(value, Decimal):
		return format(value, "f")
	return _UNSERIALIZABLE_WHATSAPP_PREVIEW_VALUE


@frappe.whitelist()
def get_whatsapp_preview_fields(reference_doctype: str, reference_name: str) -> dict:
	"""Return a minimal, permission-scoped field/value snapshot for CRM preview."""
	if not any(role in ALLOWED_WHATSAPP_ROLES for role in frappe.get_roles()):
		_deny_whatsapp_preview_access()

	if (
		not isinstance(reference_doctype, str)
		or reference_doctype not in WHATSAPP_PREVIEW_DOCTYPES
		or not isinstance(reference_name, str)
		or not reference_name.strip()
	):
		_deny_whatsapp_preview_access()

	try:
		doc = frappe.get_doc(reference_doctype, reference_name)
	except frappe.DoesNotExistError:
		# Use the same response as a record permission denial to avoid leaking existence.
		_deny_whatsapp_preview_access()

	if not doc.has_permission("read"):
		_deny_whatsapp_preview_access()

	meta = frappe.get_meta(reference_doctype)
	get_permitted_fieldnames = getattr(meta, "get_permitted_fieldnames", None)
	if not callable(get_permitted_fieldnames):
		# Metadata alone is not a field-level authorization check.
		_deny_whatsapp_preview_access()

	try:
		permitted_fieldnames = set(
			get_permitted_fieldnames(
				user=frappe.session.user,
				permission_type="read",
				with_virtual_fields=False,
			)
		)
	except Exception:
		# Permission API failures fail closed; never fall back to get_meta alone.
		_deny_whatsapp_preview_access()

	fields = []
	for field in meta.fields:
		fieldname = getattr(field, "fieldname", None)
		if not fieldname or fieldname not in permitted_fieldnames:
			continue
		if getattr(field, "fieldtype", None) not in WHATSAPP_PREVIEW_FIELD_TYPES:
			continue
		if getattr(field, "hidden", 0) or getattr(field, "is_virtual", 0):
			continue
		if getattr(field, "mask", None):
			continue
		value = _serialize_whatsapp_preview_value(doc.get(fieldname))
		if value is _UNSERIALIZABLE_WHATSAPP_PREVIEW_VALUE:
			continue

		fields.append(
			{
				"fieldname": fieldname,
				"label": getattr(field, "label", None) or fieldname,
				"value": value,
			}
		)

	return {"fields": fields}


@frappe.whitelist()
def send_whatsapp_template(
	reference_doctype: str,
	reference_name: str,
	template: str,
	to: str,
	body_param: dict | None = None
):
	"""
	Envía plantilla WhatsApp con variables nombradas.
	
	Args:
		reference_doctype: DocType de referencia (ej: "CRM Lead")
		reference_name: Nombre del documento (ej: "LEAD-001")
		template: Nombre de WhatsApp Templates
		to: Número de teléfono destino
		body_param: Dict con variables nombradas y sus valores
					Ej: {"nombre": "Juan", "asesor": "María"}
	"""
	validate_access(reference_doctype, reference_name)
	doc = frappe.new_doc("WhatsApp Message")
	doc.update(
		{
			"reference_doctype": reference_doctype,
			"reference_name": reference_name,
			"message_type": "Template",
			"message": "Template message",
			"content_type": "text",
			"use_template": True,
			"template": template,
			"to": to,
			"body_param": json.dumps(body_param) if body_param else None,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name


@frappe.whitelist()
def react_on_whatsapp_message(emoji: str, reply_to_name: str):
	validate_access()
	if not frappe.db.exists("WhatsApp Message", reply_to_name):
		frappe.throw(_("Referenced WhatsApp message does not exist."), frappe.DoesNotExistError)
	reply_to_doc = frappe.get_doc("WhatsApp Message", reply_to_name)

	if not reply_to_doc.has_permission("read"):
		frappe.throw(_("Not permitted to access the referenced WhatsApp message."), frappe.PermissionError)

	validate_access(reply_to_doc.reference_doctype, reply_to_doc.reference_name)

	to = (reply_to_doc.type == "Incoming" and reply_to_doc.get("from")) or reply_to_doc.to
	doc = frappe.new_doc("WhatsApp Message")
	doc.update(
		{
			"reference_doctype": reply_to_doc.reference_doctype,
			"reference_name": reply_to_doc.reference_name,
			"message": emoji,
			"to": to,
			"reply_to_message_id": reply_to_doc.message_id,
			"content_type": "reaction",
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name


def parse_template_parameters(string, parameters):
	for i, parameter in enumerate(parameters, start=1):
		placeholder = "{{" + str(i) + "}}"
		string = string.replace(placeholder, str(parameter))

	return string


def get_from_name(message):
	if not message.get("reference_doctype") or not message.get("reference_name"):
		return message.get("from", "")
	doc = frappe.get_doc(message["reference_doctype"], message["reference_name"])
	from_name = ""
	if message["reference_doctype"] == "CRM Deal":
		if doc.get("contacts"):
			for c in doc.get("contacts"):
				if c.is_primary:
					from_name = c.full_name or c.mobile_no
					break
		else:
			from_name = doc.get("lead_name")
	else:
		from_name = " ".join(name for name in [doc.get("first_name"), doc.get("last_name")] if name)
	return from_name


def add_roles():
	if "frappe_whatsapp" not in frappe.get_installed_apps():
		return

	role_list = ["Sales Manager", "Sales User"]
	doctypes = ["WhatsApp Message", "WhatsApp Templates", "WhatsApp Settings"]
	for doctype in doctypes:
		for role in role_list:
			if frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": role}):
				continue
			add_permission(doctype, role, 0, "write")
			update_permission_property(doctype, role, 0, "create", 1)
			update_permission_property(doctype, role, 0, "delete", 1)
			update_permission_property(doctype, role, 0, "share", 1)
			update_permission_property(doctype, role, 0, "email", 1)
			update_permission_property(doctype, role, 0, "print", 1)


@frappe.whitelist()
def get_whatsapp_template_fields(doctype: str, template_name: str = None) -> dict:
	"""Return fields for a doctype including custom fields, plus existing mapping if template provided.
	
	Used by the WhatsApp variable mapping UI to pre-populate field selections.
	"""
	if not any(role in ALLOWED_WHATSAPP_ROLES for role in frappe.get_roles()):
		frappe.throw(_("Only sales users can access WhatsApp features."), frappe.PermissionError)

	if not isinstance(doctype, str) or not doctype:
		frappe.throw(_("Invalid doctype."))

	meta = frappe.get_meta(doctype)
	
	# Build field list including custom fields
	fields = []
	seen_fieldnames = set()
	
	for field in meta.fields:
		fieldname = getattr(field, "fieldname", None)
		if not fieldname or fieldname in seen_fieldnames:
			continue
		if getattr(field, "fieldtype", None) in ("Section Break", "Column Break", "Tab Break"):
			continue
		if getattr(field, "hidden", 0):
			continue
		
		seen_fieldnames.add(fieldname)
		fields.append({
			"fieldname": fieldname,
			"label": getattr(field, "label", None) or fieldname,
			"fieldtype": getattr(field, "fieldtype", None),
		})
	
	# Also include custom fields from Custom Field doctype
	custom_fields = frappe.get_all(
		"Custom Field",
		filters={"dt": doctype},
		fields=["fieldname", "label", "fieldtype"],
	)
	for cf in custom_fields:
		fieldname = cf.get("fieldname")
		if fieldname and fieldname not in seen_fieldnames:
			seen_fieldnames.add(fieldname)
			fields.append({
				"fieldname": fieldname,
				"label": cf.get("label") or fieldname,
				"fieldtype": cf.get("fieldtype"),
			})
	
	# Load existing mapping if template provided
	existing_mapping = {}
	if template_name:
		try:
			template = frappe.get_doc("WhatsApp Templates", template_name)
			if template.named_field_mapping:
				existing_mapping = json.loads(template.named_field_mapping)
		except Exception:
			pass
	
	return {"fields": fields, "existing_mapping": existing_mapping}


@frappe.whitelist()
def save_whatsapp_template_mapping(template_name: str, field_mapping: dict | str) -> dict:
	"""Save the field mapping for a WhatsApp template.
	
	field_mapping: JSON object mapping variable names to fieldnames, e.g. {"nombre": "lead_name"}
	"""
	if not any(role in ALLOWED_WHATSAPP_ROLES for role in frappe.get_roles()):
		frappe.throw(_("Only sales users can access WhatsApp features."), frappe.PermissionError)

	if not isinstance(template_name, str) or not template_name:
		frappe.throw(_("Invalid template name."))

	if isinstance(field_mapping, str):
		try:
			field_mapping = json.loads(field_mapping)
		except json.JSONDecodeError:
			frappe.throw(_("Invalid field mapping JSON."))

	if not isinstance(field_mapping, dict):
		frappe.throw(_("Field mapping must be a JSON object."))

	template = frappe.get_doc("WhatsApp Templates", template_name)
	template.named_field_mapping = json.dumps(field_mapping)
	template.save(ignore_permissions=True)
	
	return {"success": True, "mapping": field_mapping}
