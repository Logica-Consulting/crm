import { describe, it, expect } from 'vitest'
import { shouldInterceptReversal } from '@/utils/reversalInterception'

describe('shouldInterceptReversal', () => {
  // -- Positive: terminal → active --

  it('returns true when moving from a Lost-type status to an active stage', () => {
    expect(
      shouldInterceptReversal(
        'CRM Deal',
        'status',
        'Perdido',
        'Negotiation',
        'Lost',
        'Ongoing'
      )
    ).toBe(true)
  })

  it('returns true when moving from a Won-type status to an active stage', () => {
    expect(
      shouldInterceptReversal(
        'CRM Deal',
        'status',
        'Delivery',
        'Validation',
        'Won',
        'Ongoing'
      )
    ).toBe(true)
  })

  // -- Terminal-ness is type-driven, not name-driven --

  it('treats an arbitrary status name with Won type as terminal', () => {
    expect(
      shouldInterceptReversal(
        'CRM Deal',
        'status',
        'Some Custom Won Name',
        'Validation',
        'Won',
        'Ongoing'
      )
    ).toBe(true)
  })

  it('does not treat a status named Delivery with a non-terminal type as terminal', () => {
    expect(
      shouldInterceptReversal(
        'CRM Deal',
        'status',
        'Delivery',
        'Validation',
        'Ongoing',
        'Ongoing'
      )
    ).toBe(false)
  })

  // -- Negative: not CRM Deal --

  it('returns false when doctype is not CRM Deal', () => {
    expect(
      shouldInterceptReversal(
        'CRM Lead',
        'status',
        'Perdido',
        'Negotiation',
        'Lost',
        'Ongoing'
      )
    ).toBe(false)
  })

  // -- Negative: wrong column_field --

  it('returns false when column_field is not "status"', () => {
    expect(
      shouldInterceptReversal(
        'CRM Deal',
        'comercial_pipeline_stage',
        'Perdido',
        'Negotiation',
        'Lost',
        'Ongoing'
      )
    ).toBe(false)
  })

  // -- Negative: from active to active (no reversal) --

  it('returns false when moving between active stages', () => {
    expect(
      shouldInterceptReversal(
        'CRM Deal',
        'status',
        'Identification',
        'Validation',
        'Open',
        'Ongoing'
      )
    ).toBe(false)
  })

  // -- Negative: from active to terminal (not a reversal) --

  it('returns false when moving from active to a Lost-type status', () => {
    expect(
      shouldInterceptReversal(
        'CRM Deal',
        'status',
        'Negotiation',
        'Perdido',
        'Ongoing',
        'Lost'
      )
    ).toBe(false)
  })

  // -- Negative: terminal to terminal (both terminal → not a reversal) --

  it('returns false when moving between two terminal statuses', () => {
    expect(
      shouldInterceptReversal(
        'CRM Deal',
        'status',
        'Perdido',
        'Delivery',
        'Lost',
        'Won'
      )
    ).toBe(false)
  })

  // -- Negative: same status (no move) --

  it('returns false when from and to are the same status', () => {
    expect(
      shouldInterceptReversal(
        'CRM Deal',
        'status',
        'Perdido',
        'Perdido',
        'Lost',
        'Lost'
      )
    ).toBe(false)
  })

  // -- Edge: empty values --

  it('returns false when fromStatus is empty', () => {
    expect(
      shouldInterceptReversal('CRM Deal', 'status', '', 'Negotiation', 'Lost', 'Ongoing')
    ).toBe(false)
  })

  it('returns false when toStatus is empty', () => {
    expect(
      shouldInterceptReversal('CRM Deal', 'status', 'Perdido', '', 'Lost', 'Ongoing')
    ).toBe(false)
  })

  // -- Edge: missing type info (statuses not yet loaded) --

  it('returns false when fromType is undefined', () => {
    expect(
      shouldInterceptReversal(
        'CRM Deal',
        'status',
        'Perdido',
        'Negotiation',
        undefined,
        'Ongoing'
      )
    ).toBe(false)
  })

  it('intercepts when toType is undefined and fromType is terminal', () => {
    // Unknown target type is treated as non-terminal (conservative intercept).
    expect(
      shouldInterceptReversal(
        'CRM Deal',
        'status',
        'Perdido',
        'Negotiation',
        'Lost',
        undefined
      )
    ).toBe(true)
  })
})
