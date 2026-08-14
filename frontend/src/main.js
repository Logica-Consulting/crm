import './index.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createDialog } from './utils/dialogs'
import { initSocket } from './socket'
import router from './router'
import translationPlugin from './translation'
import App from './App.vue'

import {
  FrappeUI,
  Button,
  Input,
  TextInput,
  FormControl,
  ErrorMessage,
  Dialog,
  Alert,
  Badge,
  setConfig,
  frappeRequest,
  call,
  FeatherIcon,
} from 'frappe-ui'

import { telemetryPlugin } from 'frappe-ui/frappe'
// injects the lucide SVG sprite into the DOM so the IconPicker and lucide Icons
// (used for view icons) can render from it
import { spritePlugin } from 'frappe-ui/icons'

let globalComponents = {
  Button,
  TextInput,
  Input,
  FormControl,
  ErrorMessage,
  Dialog,
  Alert,
  Badge,
  FeatherIcon,
}

// create a pinia instance
let pinia = createPinia()

let app = createApp(App)

setConfig('resourceFetcher', frappeRequest)
app.use(FrappeUI)
app.use(spritePlugin)
app.use(pinia)
app.use(router)
app.use(translationPlugin)
for (let key in globalComponents) {
  app.component(key, globalComponents[key])
}
app.use(telemetryPlugin, { app_name: 'crm' })

app.config.globalProperties.$dialog = createDialog

// frappe.call shim — Comercial stores use the global frappe.call({ method, args })
// and expect a `{ message }` response. The CRM SPA only provides frappe-ui's `call()`
// (which returns the unwrapped message), so bridge it before any Comercial component mounts.
window.frappe = window.frappe || {}
if (!window.frappe.call) {
  window.frappe.call = async ({ method, args = {} } = {}) => {
    try {
      const message = await call(method, args)
      return { message }
    } catch (err) {
      const parts = []
      if (err.exc_type) parts.push(err.exc_type)
      if (err.messages && err.messages.length) {
        parts.push(err.messages.join(' | '))
      }
      if (err.exc && typeof err.exc === 'string') {
        parts.push(err.exc.slice(0, 800))
      }
      const detail = parts.join(' — ') || err.message || 'Unknown error'
      const e = new Error(detail)
      e.messages = err.messages
      e.exc_type = err.exc_type
      e.exc = err.exc
      e.status = err.status
      throw e
    }
  }
}

let socket
if (import.meta.env.DEV) {
  frappeRequest({ url: '/api/method/crm.www.crm.get_context_for_dev' }).then(
    (values) => {
      for (let key in values) {
        window[key] = values[key]
      }
      socket = initSocket()
      app.config.globalProperties.$socket = socket
      app.mount('#app')
    },
  )
} else {
  socket = initSocket()
  app.config.globalProperties.$socket = socket
  app.mount('#app')
}

if (import.meta.env.DEV) {
  window.$dialog = createDialog
}
