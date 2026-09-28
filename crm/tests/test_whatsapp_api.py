"""
Tests unitarios para las APIs de WhatsApp con variables nombradas.

Ejecutar con:
  bench --site <site> run-tests --module crm.tests.test_whatsapp_api
"""

import frappe
from frappe.tests.utils import FrappeTestCase
import json


class TestWhatsAppAPI(FrappeTestCase):
    """Tests para APIs de WhatsApp con soporte de variables nombradas."""

    @classmethod
    def setUpClass(cls):
        """Configuración inicial para todos los tests."""
        super().setUpClass()
        
        # Crear template de prueba con variables nombradas
        if not frappe.db.exists("WhatsApp Templates", "test_template_named"):
            frappe.get_doc({
                "doctype": "WhatsApp Templates",
                "template_name": "test_template_named",
                "actual_name": "test_template_named",
                "template": "Hola {{nombre}}, tu asesor es {{asesor}}. Disciplina: {{disciplina}}",
                "for_doctype": "CRM Lead",
                "sample_values": "a,a,a",
                "status": "APPROVED",
                "language": "es",
                "language_code": "es_MX",
                "category": "MARKETING"
            }).insert(ignore_permissions=True)
        
        # Crear template de prueba sin variables
        if not frappe.db.exists("WhatsApp Templates", "test_template_no_vars"):
            frappe.get_doc({
                "doctype": "WhatsApp Templates",
                "template_name": "test_template_no_vars",
                "actual_name": "test_template_no_vars",
                "template": "Hola, este es un mensaje sin variables.",
                "for_doctype": "CRM Lead",
                "status": "APPROVED",
                "language": "es",
                "language_code": "es_MX",
                "category": "MARKETING"
            }).insert(ignore_permissions=True)
        
        # Crear template con variables duplicadas
        if not frappe.db.exists("WhatsApp Templates", "test_template_duplicates"):
            frappe.get_doc({
                "doctype": "WhatsApp Templates",
                "template_name": "test_template_duplicates",
                "actual_name": "test_template_duplicates",
                "template": "Hola {{nombre}}, {{nombre}}. Tu asesor es {{asesor}}.",
                "for_doctype": "CRM Lead",
                "sample_values": "a,a",
                "status": "APPROVED",
                "language": "es",
                "language_code": "es_MX",
                "category": "MARKETING"
            }).insert(ignore_permissions=True)

    @classmethod
    def tearDownClass(cls):
        """Limpieza después de todos los tests."""
        # Eliminar templates de prueba
        for template_name in ["test_template_named", "test_template_no_vars", "test_template_duplicates"]:
            if frappe.db.exists("WhatsApp Templates", template_name):
                frappe.delete_doc("WhatsApp Templates", template_name, force=True)
        
        super().tearDownClass()

    def test_get_template_variables_extracts_named_variables(self):
        """Test que extrae correctamente variables nombradas del template."""
        from crm.api.whatsapp import get_template_variables
        
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

    def test_get_template_variables_empty_for_no_vars(self):
        """Test que retorna lista vacía para template sin variables."""
        from crm.api.whatsapp import get_template_variables
        
        variables = get_template_variables("test_template_no_vars")
        
        self.assertEqual(len(variables), 0)
        self.assertEqual(variables, [])

    def test_get_template_variables_removes_duplicates(self):
        """Test que elimina variables duplicadas."""
        from crm.api.whatsapp import get_template_variables
        
        variables = get_template_variables("test_template_duplicates")
        
        # Debe extraer solo 2 variables únicas (nombre aparece 2 veces en el template)
        self.assertEqual(len(variables), 2)
        
        variable_names = [v["name"] for v in variables]
        self.assertIn("nombre", variable_names)
        self.assertIn("asesor", variable_names)

    def test_get_template_variables_ignores_invalid_format(self):
        """Test que ignora variables con formato inválido (mayúsculas, números)."""
        # Crear template temporal con variables inválidas
        template_name = "test_template_invalid_vars"
        if not frappe.db.exists("WhatsApp Templates", template_name):
            frappe.get_doc({
                "doctype": "WhatsApp Templates",
                "template_name": template_name,
                "actual_name": template_name,
                "template": "Hola {{Nombre}}, tu ID es {{id123}}, contacto: {{teléfono}}",
                "for_doctype": "CRM Lead",
                "sample_values": "a,a,a",
                "status": "APPROVED",
                "language": "es",
                "language_code": "es_MX",
                "category": "MARKETING"
            }).insert(ignore_permissions=True)
        
        try:
            from crm.api.whatsapp import get_template_variables
            
            variables = get_template_variables(template_name)
            
            # No debe extraer ninguna variable válida (todas tienen formato inválido)
            self.assertEqual(len(variables), 0)
        finally:
            # Limpiar
            if frappe.db.exists("WhatsApp Templates", template_name):
                frappe.delete_doc("WhatsApp Templates", template_name, force=True)

    def test_send_whatsapp_template_with_body_param(self):
        """Test que envía template con variables nombradas usando body_param."""
        from crm.api.whatsapp import send_whatsapp_template
        
        # Crear Lead de prueba
        lead_name = frappe.generate_hash(length=10)
        lead = frappe.get_doc({
            "doctype": "CRM Lead",
            "lead_name": lead_name,
            "first_name": "Juan",
            "mobile_no": "521234567890",
            "lead_owner": "maria@example.com"
        })
        lead.insert(ignore_permissions=True)
        
        try:
            # Enviar template con variables nombradas
            message_name = send_whatsapp_template(
                reference_doctype="CRM Lead",
                reference_name=lead.name,
                template="test_template_named",
                to="521234567890",
                body_param={
                    "nombre": "Juan",
                    "asesor": "María",
                    "disciplina": "Karate"
                }
            )
            
            # Verificar que se creó el mensaje
            self.assertIsNotNone(message_name)
            self.assertTrue(frappe.db.exists("WhatsApp Message", message_name))
            
            # Verificar que body_param se guardó correctamente
            message = frappe.get_doc("WhatsApp Message", message_name)
            self.assertIsNotNone(message.body_param)
            
            body_data = json.loads(message.body_param)
            self.assertEqual(body_data["nombre"], "Juan")
            self.assertEqual(body_data["asesor"], "María")
            self.assertEqual(body_data["disciplina"], "Karate")
            
            # Limpiar
            frappe.delete_doc("WhatsApp Message", message_name, force=True)
        finally:
            # Limpiar Lead
            frappe.delete_doc("CRM Lead", lead.name, force=True)

    def test_send_whatsapp_template_without_body_param(self):
        """Test que envía template sin variables (body_param=None)."""
        from crm.api.whatsapp import send_whatsapp_template
        
        # Crear Lead de prueba
        lead_name = frappe.generate_hash(length=10)
        lead = frappe.get_doc({
            "doctype": "CRM Lead",
            "lead_name": lead_name,
            "first_name": "Test",
            "mobile_no": "521234567890"
        })
        lead.insert(ignore_permissions=True)
        
        try:
            # Enviar template sin variables
            message_name = send_whatsapp_template(
                reference_doctype="CRM Lead",
                reference_name=lead.name,
                template="test_template_no_vars",
                to="521234567890",
                body_param=None
            )
            
            # Verificar que se creó el mensaje
            self.assertIsNotNone(message_name)
            self.assertTrue(frappe.db.exists("WhatsApp Message", message_name))
            
            # Verificar que body_param es None
            message = frappe.get_doc("WhatsApp Message", message_name)
            self.assertIsNone(message.body_param)
            
            # Limpiar
            frappe.delete_doc("WhatsApp Message", message_name, force=True)
        finally:
            # Limpiar Lead
            frappe.delete_doc("CRM Lead", lead.name, force=True)

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
                body_param={"nombre": "Test"}
            )
