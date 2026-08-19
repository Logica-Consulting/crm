/**
 * Reactive registry for custom Deal tabs.
 *
 * External apps (e.g. comercial via app_include_js) can register
 * tab definitions that will appear as native tabs in the Deal detail view.
 *
 * Each tab definition must have:
 *   - name: unique string identifier (used as tab key)
 *   - label: display label (translatable)
 *   - order: numeric sort order (lower = earlier)
 *   - render: Vue component or render function for the tab panel
 *
 * Optional:
 *   - icon: Vue component for the tab icon
 *   - condition: () => boolean — if false, tab is hidden
 *
 * The registry is exposed globally on `window` so that external IIFE builds
 * (loaded via app_include_js) can register tabs without importing ES modules.
 *
 * Load-order safety: external IIFEs may evaluate BEFORE this module (the SPA
 * bundle is a deferred module). Registrations made before this module runs are
 * buffered in `window.__crmCustomTabPendingRegistrations` and flushed into the
 * registry on initialization. The registry also adopts any pre-existing
 * `window.__crmCustomTabRegistry` instead of clobbering it.
 */

import { reactive } from 'vue'

/**
 * Create a fresh custom Deal tab registry.
 * @returns {Object} registry API
 */
function createRegistry() {
  const registry = reactive(new Map())

  function registerDealTab(tabDef) {
    if (!tabDef || !tabDef.name) {
      throw new Error('registerDealTab: tabDef.name is required')
    }
    registry.set(tabDef.name, {
      order: 99,
      ...tabDef,
    })
  }

  function unregisterDealTab(name) {
    registry.delete(name)
  }

  function getRegisteredDealTabs() {
    return Array.from(registry.values()).sort(
      (a, b) => (a.order ?? 99) - (b.order ?? 99)
    )
  }

  function getDealTab(name) {
    return registry.get(name)
  }

  function clearDealTabRegistry() {
    registry.clear()
  }

  return {
    registerDealTab,
    unregisterDealTab,
    getRegisteredDealTabs,
    getDealTab,
    clearDealTabRegistry,
  }
}

const PENDING_KEY = '__crmCustomTabPendingRegistrations'

/**
 * Flush registrations buffered before this module evaluated into the registry.
 */
function flushPendingRegistrations(target) {
  if (typeof window === 'undefined') return
  const pending = window[PENDING_KEY]
  if (!Array.isArray(pending) || pending.length === 0) return
  for (const tabDef of pending) {
    try {
      target.registerDealTab(tabDef)
    } catch {
      // Ignore malformed buffered definitions — never break registry init.
    }
  }
  window[PENDING_KEY] = []
}

// Lazy + defensive initialization: adopt any pre-existing registry (e.g. a
// bootstrap stub) rather than clobbering it, otherwise create a fresh one.
const registry =
  (typeof window !== 'undefined' && window.__crmCustomTabRegistry) ||
  createRegistry()

if (typeof window !== 'undefined') {
  window.__crmCustomTabRegistry = registry
  flushPendingRegistrations(registry)
}

export const registerDealTab = registry.registerDealTab
export const unregisterDealTab = registry.unregisterDealTab
export const getRegisteredDealTabs = registry.getRegisteredDealTabs
export const getDealTab = registry.getDealTab
export const clearDealTabRegistry = registry.clearDealTabRegistry
