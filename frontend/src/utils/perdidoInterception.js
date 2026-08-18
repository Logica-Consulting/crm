/**
 * Pure guard: should a kanban drag to "Perdido" be intercepted
 * with a lost_reason dialog instead of a plain set_value?
 *
 * Interception fires ONLY when ALL of:
 *   - doctype is "CRM Deal"
 *   - column_field is "comercial_pipeline_stage"
 *   - target column (data.to) is "Perdido"
 *
 * @param {string} doctype    — the list's doctype (from props)
 * @param {string} columnField — the kanban's column_field (from view)
 * @param {string} toValue    — the target column name (from drag data.to)
 * @returns {boolean}
 */
export function shouldInterceptPerdido(doctype, columnField, toValue) {
  return (
    doctype === 'CRM Deal' &&
    columnField === 'comercial_pipeline_stage' &&
    toValue === 'Perdido'
  )
}
