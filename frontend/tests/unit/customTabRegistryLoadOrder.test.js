import { describe, it, expect, beforeEach, vi } from 'vitest'

function resetGlobals() {
  delete window.__crmCustomTabRegistry
  delete window.__crmCustomTabPendingRegistrations
}

describe('customTabRegistry load-order safety', () => {
  beforeEach(() => {
    vi.resetModules()
    resetGlobals()
  })

  it('flushes registrations buffered before the module evaluates', async () => {
    window.__crmCustomTabPendingRegistrations = [
      { name: 'Documents', label: 'Documents', order: 10 },
      { name: 'Health', label: 'Health', order: 40 },
    ]

    const registry = await import('@/utils/customTabRegistry')

    expect(registry.getRegisteredDealTabs().map((t) => t.name)).toEqual([
      'Documents',
      'Health',
    ])
    expect(window.__crmCustomTabPendingRegistrations).toEqual([])
  })

  it('skips malformed buffered registrations without failing', async () => {
    window.__crmCustomTabPendingRegistrations = [
      { label: 'No Name', order: 10 },
      { name: 'Documents', label: 'Documents', order: 10 },
    ]

    const registry = await import('@/utils/customTabRegistry')

    expect(registry.getRegisteredDealTabs().map((t) => t.name)).toEqual([
      'Documents',
    ])
  })

  it('adopts a pre-existing global registry instead of clobbering it', async () => {
    const existing = {
      registerDealTab() {},
      unregisterDealTab() {},
      getRegisteredDealTabs() {
        return [{ name: 'PreExisting' }]
      },
      getDealTab() {},
      clearDealTabRegistry() {},
    }
    window.__crmCustomTabRegistry = existing

    const registry = await import('@/utils/customTabRegistry')

    expect(window.__crmCustomTabRegistry).toBe(existing)
    expect(registry.getRegisteredDealTabs()).toEqual([{ name: 'PreExisting' }])
  })

  it('creates and exposes a fresh registry on the normal path', async () => {
    const registry = await import('@/utils/customTabRegistry')

    registry.registerDealTab({ name: 'Documents', label: 'Documents', order: 10 })
    expect(registry.getRegisteredDealTabs().map((t) => t.name)).toEqual([
      'Documents',
    ])
    expect(window.__crmCustomTabRegistry).toBeDefined()
  })
})
