import { describe, it, expect } from 'vitest'
import { shouldInterceptReversal } from '@/utils/reversalInterception'

describe('shouldInterceptReversal', () => {
  // -- Positive: terminal → active --

  it('returns true when moving from Perdido to an active stage', () => {
    expect(
      shouldInterceptReversal('CRM Deal', 'status', 'Perdido', 'Negotiation')
    ).toBe(true)
  })

  it('returns true when moving from a Won-type status to an active stage', () => {
    expect(
      shouldInterceptReversal('CRM Deal', 'status', 'Delivery', 'Validation')
    ).toBe(true)
  })

  // -- Negative: not CRM Deal --

  it('returns false when doctype is not CRM Deal', () => {
    expect(
      shouldInterceptReversal('CRM Lead', 'status', 'Perdido', 'Negotiation')
    ).toBe(false)
  })

  // -- Negative: wrong column_field --

  it('returns false when column_field is not "status"', () => {
    expect(
      shouldInterceptReversal(
        'CRM Deal',
        'comercial_pipeline_stage',
        'Perdido',
        'Negotiation'
      )
    ).toBe(false)
  })

  // -- Negative: from active to active (no reversal) --

  it('returns false when moving between active stages', () => {
    expect(
      shouldInterceptReversal('CRM Deal', 'status', 'Identification', 'Validation')
    ).toBe(false)
  })

  // -- Negative: from active to terminal (not a reversal) --

  it('returns false when moving from active to Perdido', () => {
    expect(
      shouldInterceptReversal('CRM Deal', 'status', 'Negotiation', 'Perdido')
    ).toBe(false)
  })

  // -- Negative: same status (no move) --

  it('returns false when from and to are the same terminal', () => {
    expect(
      shouldInterceptReversal('CRM Deal', 'status', 'Perdido', 'Perdido')
    ).toBe(false)
  })

  // -- Edge: empty values --

  it('returns false when fromStatus is empty', () => {
    expect(
      shouldInterceptReversal('CRM Deal', 'status', '', 'Negotiation')
    ).toBe(false)
  })

  it('returns false when toStatus is empty', () => {
    expect(
      shouldInterceptReversal('CRM Deal', 'status', 'Perdido', '')
    ).toBe(false)
  })
})
