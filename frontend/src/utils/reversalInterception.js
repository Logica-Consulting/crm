/**
 * Pure guard: should a kanban drag from a terminal status to an active
 * stage be intercepted with a reversal-reason dialog?
 *
 * Reversal interception fires when ALL of:
 *   - doctype is "CRM Deal"
 *   - column_field is "status" (native single-axis)
 *   - fromStatus is a terminal status (Won or Lost type)
 *   - toStatus is NOT a terminal status (active stage)
 *   - fromStatus !== toStatus (actual move)
 *
 * Terminal-ness is derived from the status `type` field (Won/Lost), matching
 * the backend, rather than hardcoding status names.
 *
 * @param {string} doctype     — the list's doctype
 * @param {string} columnField — the kanban's column_field
 * @param {string} fromStatus  — current status (drag source column)
 * @param {string} toStatus    — target status (drag destination column)
 * @param {string} [fromType]  — type of the source status (Won/Lost/Ongoing/Open)
 * @param {string} [toType]    — type of the target status
 * @returns {boolean}
 */

const TERMINAL_TYPES = new Set(['Won', 'Lost'])

function isTerminalType(type) {
  return TERMINAL_TYPES.has(type)
}

export function shouldInterceptReversal(
  doctype,
  columnField,
  fromStatus,
  toStatus,
  fromType,
  toType
) {
  return !!(
    doctype === 'CRM Deal' &&
    columnField === 'status' &&
    fromStatus &&
    toStatus &&
    fromStatus !== toStatus &&
    isTerminalType(fromType) &&
    !isTerminalType(toType)
  )
}
