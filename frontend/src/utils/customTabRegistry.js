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
 */

import { reactive } from 'vue'

const registry = reactive(new Map())

/**
 * Register a custom Deal tab.
 * @param {Object} tabDef - Tab definition
 * @param {string} tabDef.name - Unique tab identifier
 * @param {string} tabDef.label - Display label
 * @param {number} [tabDef.order=99] - Sort order (lower = earlier)
 * @param {Function|Object} tabDef.render - Vue component or render function
 * @param {Object} [tabDef.icon] - Icon component
 * @param {Function} [tabDef.condition] - Visibility condition
 */
export function registerDealTab(tabDef) {
  if (!tabDef || !tabDef.name) {
    throw new Error('registerDealTab: tabDef.name is required')
  }
  registry.set(tabDef.name, {
    order: 99,
    ...tabDef,
  })
}

/**
 * Unregister a custom Deal tab by name.
 * @param {string} name - Tab name to remove
 */
export function unregisterDealTab(name) {
  registry.delete(name)
}

/**
 * Get all registered tabs, sorted by order.
 * @returns {Array} Array of tab definitions
 */
export function getRegisteredDealTabs() {
  return Array.from(registry.values()).sort(
    (a, b) => (a.order ?? 99) - (b.order ?? 99)
  )
}

/**
 * Get a specific registered tab by name.
 * @param {string} name - Tab name
 * @returns {Object|undefined} Tab definition or undefined
 */
export function getDealTab(name) {
  return registry.get(name)
}

/**
 * Clear all registered tabs (useful for testing).
 */
export function clearDealTabRegistry() {
  registry.clear()
}

// Expose registry globally for external IIFE builds (e.g. comercial app)
if (typeof window !== 'undefined') {
  window.__crmCustomTabRegistry = {
    registerDealTab,
    unregisterDealTab,
    getRegisteredDealTabs,
    getDealTab,
    clearDealTabRegistry,
  }
}
