/**
 * Pure guard: should a kanban drag from a terminal status to an active
 * stage be intercepted with a reversal-reason dialog?
 *
 * Reversal interception fires when ALL of:
 *   - doctype is "CRM Deal"
 *   - column_field is "status" (native single-axis)
 *   - fromStatus is a terminal status (Perdido or Won-type)
 *   - toStatus is NOT a terminal status (active stage)
 *   - fromStatus !== toStatus (actual move)
 *
 * Terminal statuses: "Perdido" (Lost) + any Won-type status.
 * For simplicity, we treat known Won-type names as terminal:
 *   Delivery, Commercial Closure (the two Won statuses seeded by comercial).
 *
 * @param {string} doctype     — the list's doctype
 * @param {string} columnField — the kanban's column_field
 * @param {string} fromStatus  — current status (drag source column)
 * @param {string} toStatus    — target status (drag destination column)
 * @returns {boolean}
 */

const WON_STATUSES = new Set(['Delivery', 'Commercial Closure'])
const LOST_STATUSES = new Set(['Perdido'])

function isTerminal(status) {
  return WON_STATUSES.has(status) || LOST_STATUSES.has(status)
}

export function shouldInterceptReversal(doctype, columnField, fromStatus, toStatus) {
  return !!(
    doctype === 'CRM Deal' &&
    columnField === 'status' &&
    fromStatus &&
    toStatus &&
    fromStatus !== toStatus &&
    isTerminal(fromStatus) &&
    !isTerminal(toStatus)
  )
}
