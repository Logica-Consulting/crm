import { describe, it, expect, beforeEach } from 'vitest'
import {
  registerDealTab,
  unregisterDealTab,
  getRegisteredDealTabs,
  getDealTab,
  clearDealTabRegistry,
} from '@/utils/customTabRegistry'

describe('customTabRegistry', () => {
  beforeEach(() => {
    clearDealTabRegistry()
  })

  it('starts empty', () => {
    expect(getRegisteredDealTabs()).toEqual([])
  })

  it('registers a tab and retrieves it by name', () => {
    registerDealTab({ name: 'Documents', label: 'Documents', order: 10 })
    const tab = getDealTab('Documents')
    expect(tab).toBeDefined()
    expect(tab.name).toBe('Documents')
    expect(tab.label).toBe('Documents')
  })

  it('returns registered tabs sorted by order', () => {
    registerDealTab({ name: 'Health', label: 'Health', order: 40 })
    registerDealTab({ name: 'Documents', label: 'Documents', order: 10 })
    registerDealTab({ name: 'Compliance', label: 'Compliance', order: 30 })
    registerDealTab({ name: 'Solutions', label: 'Solutions', order: 20 })

    const tabs = getRegisteredDealTabs()
    expect(tabs.map((t) => t.name)).toEqual([
      'Documents',
      'Solutions',
      'Compliance',
      'Health',
    ])
  })

  it('unregisters a tab by name', () => {
    registerDealTab({ name: 'Documents', label: 'Documents', order: 10 })
    expect(getDealTab('Documents')).toBeDefined()

    unregisterDealTab('Documents')
    expect(getDealTab('Documents')).toBeUndefined()
    expect(getRegisteredDealTabs()).toEqual([])
  })

  it('overwrites a tab when registering with the same name', () => {
    registerDealTab({ name: 'Documents', label: 'Documents v1', order: 10 })
    registerDealTab({ name: 'Documents', label: 'Documents v2', order: 10 })

    const tab = getDealTab('Documents')
    expect(tab.label).toBe('Documents v2')
    expect(getRegisteredDealTabs()).toHaveLength(1)
  })

  it('returns undefined for unknown tab name', () => {
    expect(getDealTab('NonExistent')).toBeUndefined()
  })

  it('clears all registered tabs', () => {
    registerDealTab({ name: 'Documents', label: 'Documents', order: 10 })
    registerDealTab({ name: 'Solutions', label: 'Solutions', order: 20 })
    expect(getRegisteredDealTabs()).toHaveLength(2)

    clearDealTabRegistry()
    expect(getRegisteredDealTabs()).toEqual([])
  })

  it('uses default order of 99 when order is not specified', () => {
    registerDealTab({ name: 'NoOrder', label: 'NoOrder' })
    registerDealTab({ name: 'WithOrder', label: 'WithOrder', order: 5 })

    const tabs = getRegisteredDealTabs()
    expect(tabs[0].name).toBe('WithOrder')
    expect(tabs[1].name).toBe('NoOrder')
  })
})
