import { describe, it, expect } from 'vitest'
import { shouldInterceptPerdido } from '@/utils/perdidoInterception'

describe('shouldInterceptPerdido', () => {
  // ── Positive: all three conditions met ──

  it('returns true when doctype=CRM Deal, column_field=comercial_pipeline_stage, to=Perdido', () => {
    expect(
      shouldInterceptPerdido('CRM Deal', 'comercial_pipeline_stage', 'Perdido')
    ).toBe(true)
  })

  // ── Negative: wrong doctype ──

  it('returns false when doctype is not CRM Deal (e.g. CRM Lead)', () => {
    expect(
      shouldInterceptPerdido('CRM Lead', 'comercial_pipeline_stage', 'Perdido')
    ).toBe(false)
  })

  it('returns false when doctype is empty', () => {
    expect(shouldInterceptPerdido('', 'comercial_pipeline_stage', 'Perdido')).toBe(
      false
    )
  })

  // ── Negative: wrong column_field ──

  it('returns false when column_field is "status" instead of comercial_pipeline_stage', () => {
    expect(shouldInterceptPerdido('CRM Deal', 'status', 'Perdido')).toBe(false)
  })

  it('returns false when column_field is empty', () => {
    expect(shouldInterceptPerdido('CRM Deal', '', 'Perdido')).toBe(false)
  })

  it('returns false when column_field is undefined', () => {
    expect(shouldInterceptPerdido('CRM Deal', undefined, 'Perdido')).toBe(false)
  })

  // ── Negative: wrong target column ──

  it('returns false when target is not Perdido (e.g. Delivery)', () => {
    expect(
      shouldInterceptPerdido('CRM Deal', 'comercial_pipeline_stage', 'Delivery')
    ).toBe(false)
  })

  it('returns false when target is a non-terminal stage (e.g. Identification)', () => {
    expect(
      shouldInterceptPerdido('CRM Deal', 'comercial_pipeline_stage', 'Identification')
    ).toBe(false)
  })

  it('returns false when target is empty', () => {
    expect(
      shouldInterceptPerdido('CRM Deal', 'comercial_pipeline_stage', '')
    ).toBe(false)
  })

  // ── Negative: all wrong ──

  it('returns false when all three conditions are wrong', () => {
    expect(shouldInterceptPerdido('CRM Lead', 'status', 'Open')).toBe(false)
  })

  // ── Edge: case sensitivity ──

  it('is case-sensitive on doctype ("crm deal" does not match)', () => {
    expect(
      shouldInterceptPerdido('crm deal', 'comercial_pipeline_stage', 'Perdido')
    ).toBe(false)
  })

  it('is case-sensitive on target ("perdido" does not match)', () => {
    expect(
      shouldInterceptPerdido('CRM Deal', 'comercial_pipeline_stage', 'perdido')
    ).toBe(false)
  })
})
