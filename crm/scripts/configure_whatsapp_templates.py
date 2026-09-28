"""
Script de configuración de plantillas WhatsApp para soporte de variables nombradas.

Este script configura las plantillas existentes con:
- for_doctype: "CRM Lead" (para que aparezcan en el selector)
- sample_values: placeholders necesarios para que frappe_whatsapp resuelva variables

Ejecutar vía:
  bench --site <site> execute <app>.scripts.configure_whatsapp_templates.execute
  O copiar este código en Frappe Console
"""

import frappe

def execute():
    """Configura plantillas WhatsApp para soporte de variables nombradas."""
    
    # Plantillas que requieren configuración
    # sample_values debe tener el mismo número de placeholders que variables en el template
    templates_config = [
        {"name": "sipra_bienvenida_con_formulario_-es_MX", "sample_values": "a,a,a"},
        {"name": "sipra_reflejar_dolor-es_MX", "sample_values": "a,a"},
        {"name": "sipra_oferta_llamada-es_MX", "sample_values": "a,a"},
        {"name": "sipra_demo_sin_activar_trial-es_MX", "sample_values": "a"},
        {"name": "sipra_disculpa_tardanza-es_MX", "sample_values": "a"},
        {"name": "sipra_presentacion_general-es_MX", "sample_values": "a"},
        {"name": "sipra_prueba_social-es_MX", "sample_values": "a"},
        {"name": "sipra_recuperacion_dial4-es_MX", "sample_values": "a"},
        {"name": "sipra_seguimiento_sin_respuesta-es_MX", "sample_values": "a"},
        {"name": "sipra_trial_primer_recordatorio-es_MX", "sample_values": "a"},
    ]
    
    configured_count = 0
    skipped_count = 0
    error_count = 0
    
    print("=" * 60)
    print("Configuración de Plantillas WhatsApp")
    print("=" * 60)
    
    for t in templates_config:
        template_name = t["name"]
        sample_values = t["sample_values"]
        
        # Verificar que existe
        if not frappe.db.exists("WhatsApp Templates", template_name):
            print(f"⚠️  Template no encontrado: {template_name}")
            skipped_count += 1
            continue
        
        try:
            # Actualizar sin disparar validate() (que sincroniza con Meta)
            frappe.db.set_value(
                "WhatsApp Templates",
                template_name,
                {
                    "for_doctype": "CRM Lead",
                    "sample_values": sample_values
                },
                update_modified=False
            )
            print(f"✅ Configurado: {template_name}")
            configured_count += 1
        except Exception as e:
            print(f"❌ Error al configurar {template_name}: {str(e)}")
            error_count += 1
    
    # Commit de cambios
    frappe.db.commit()
    
    print("=" * 60)
    print(f"Resumen:")
    print(f"  ✅ Configurados: {configured_count}")
    print(f"  ⚠️  Omitidos: {skipped_count}")
    print(f"  ❌ Errores: {error_count}")
    print("=" * 60)
    
    if configured_count > 0:
        print("\n✅ Configuración completada exitosamente")
        print("Las plantillas ahora aparecerán en el selector de WhatsApp del CRM")
    
    return {
        "configured": configured_count,
        "skipped": skipped_count,
        "errors": error_count
    }
