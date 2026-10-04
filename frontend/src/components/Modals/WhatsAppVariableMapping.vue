<template>
  <Dialog
    v-model:open="show"
    :title="__('Map Template Variables')"
    :size="'2xl'"
  >
    <template #default>
      <div v-if="loading" class="flex items-center justify-center py-8">
        <LoadingIndicator class="h-6 w-6" />
        <span class="ml-2 text-ink-gray-5">{{ __('Loading variables...') }}</span>
      </div>

      <div v-else-if="variables.length === 0" class="py-4">
        <div class="text-center text-ink-gray-5">
          {{ __('This template has no variables to map.') }}
        </div>
        <div class="mt-4 flex justify-end gap-2">
          <Button :label="__('Cancel')" @click="show = false" />
          <Button
            variant="solid"
            :label="__('Send Without Variables')"
            @click="sendWithoutVariables"
          />
        </div>
      </div>

      <div v-else>
        <div class="mb-4 rounded-lg bg-surface-gray-1 p-3">
          <div class="text-sm text-ink-gray-5">
            {{ __('Template') }}: <strong>{{ templateName }}</strong>
          </div>
          <div class="mt-1 text-sm text-ink-gray-5">
            {{ __('To') }}: <strong>{{ mobileNo }}</strong>
          </div>
        </div>

        <div v-if="hasExistingMapping" class="mb-3 rounded-lg border border-green-200 bg-green-50 p-2">
          <div class="flex items-center gap-2 text-sm text-green-700">
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
            </svg>
            {{ __('Using saved field mapping') }}
          </div>
        </div>

        <div class="space-y-3">
          <div
            v-for="variable in variables"
            :key="variable.name"
            class="flex items-center gap-3"
          >
            <div class="w-32 shrink-0">
              <code class="rounded bg-surface-gray-2 px-2 py-1 text-sm">
                {{ variable.placeholder }}
              </code>
            </div>
            <Select
              v-model="valueSource[variable.name]"
              class="w-36 shrink-0"
              :options="valueSourceOptions"
            />
            <Select
              v-if="valueSource[variable.name] !== 'manual'"
              v-model="fieldMapping[variable.name]"
              class="flex-1"
              :options="fieldOptions"
              :placeholder="__('Select a field')"
            />
            <input
              v-else
              v-model="manualValues[variable.name]"
              type="text"
              class="flex-1 rounded-md border border-outline-gray-2 bg-surface-white px-3 py-1.5 text-base text-ink-gray-8 placeholder:text-ink-gray-4 focus:border-outline-gray-4 focus:outline-none"
              :placeholder="__('Type a value')"
            />
            <div class="w-40 shrink-0 truncate text-sm text-ink-gray-5">
              {{ getPreviewValue(variable.name) }}
            </div>
          </div>
        </div>

        <div class="mt-4 rounded-lg border p-3">
          <div class="mb-1 text-xs font-medium text-ink-gray-5">
            {{ __('Preview') }}
          </div>
          <div class="text-sm text-ink-gray-8 whitespace-pre-wrap">
            {{ previewText }}
          </div>
        </div>

        <div class="mt-4 flex justify-end gap-2">
          <Button :label="__('Cancel')" @click="show = false" />
          <Button
            variant="solid"
            :label="__('Send Template')"
            :disabled="!isMappingComplete"
            @click="sendWithVariables"
          />
        </div>
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { createResource, Select } from 'frappe-ui'
import LoadingIndicator from '@/components/Icons/LoadingIndicator.vue'
import { ref, computed, watch } from 'vue'

const props = defineProps({
  templateName: { type: String, default: '' },
  templateBody: { type: String, default: '' },
  doctype: { type: String, default: '' },
  docname: { type: String, default: '' },
  mobileNo: { type: String, default: '' },
})

const show = defineModel({ type: Boolean })
const emit = defineEmits(['send'])

const loading = ref(false)
const variables = ref([])
const fieldMapping = ref({})
const valueSource = ref({})
const manualValues = ref({})
const docFields = ref([])
const docValues = ref({})
const existingMapping = ref({})

const getFieldsResource = createResource({
  url: 'crm.api.whatsapp.get_whatsapp_template_fields',
  onSuccess: (data) => {
    if (data?.fields) {
      docFields.value = data.fields.map((f) => ({
        label: f.label || f.fieldname,
        value: f.fieldname,
      }))
    }
    if (data?.existing_mapping) {
      existingMapping.value = data.existing_mapping
      // Pre-populate field mapping with existing values
      variables.value.forEach((v) => initVariableInput(v))
    }
    loading.value = false
  },
  onError: () => {
    loading.value = false
  },
})

const getVariablesResource = createResource({
  url: 'crm.api.whatsapp.get_template_variables',
  onSuccess: (data) => {
    variables.value = data || []
    // Initialize field mapping with existing values if available
    variables.value.forEach((v) => initVariableInput(v))
    loading.value = false
  },
  onError: () => {
    loading.value = false
  },
})

const getDocValuesResource = createResource({
  url: 'frappe.client.get',
  onSuccess: (data) => {
    docValues.value = data || {}
  },
})

const saveMappingResource = createResource({
  url: 'crm.api.whatsapp.save_whatsapp_template_mapping',
})

watch(
  () => props.templateName,
  (newVal) => {
    if (newVal && show.value) {
      loadData()
    }
  },
  { immediate: true },
)

watch(show, (newVal) => {
  if (newVal && props.templateName) {
    loadData()
  }
})

function loadData() {
  loading.value = true
  variables.value = []
  fieldMapping.value = {}
  valueSource.value = {}
  manualValues.value = {}
  existingMapping.value = {}

  // Load fields and existing mapping together
  getFieldsResource.fetch({
    doctype: props.doctype,
    template_name: props.templateName,
  })

  // Load template variables
  getVariablesResource.fetch({ template: props.templateName })

  // Load doc values for preview
  if (props.docname) {
    getDocValuesResource.fetch({
      doctype: props.doctype,
      name: props.docname,
    })
  }
}

const fieldOptions = computed(() => {
  return [{ label: __('-- Select field --'), value: '' }, ...docFields.value]
})

const valueSourceOptions = computed(() => [
  { label: __('Lead field'), value: 'field' },
  { label: __('Manual value'), value: 'manual' },
])

const hasExistingMapping = computed(() => {
  return Object.keys(existingMapping.value).length > 0 &&
    variables.value.some((v) => existingMapping.value[v.name])
})

function getSavedVariableConfig(varName) {
  const savedValue = existingMapping.value[varName]

  if (savedValue && typeof savedValue === 'object') {
    return {
      source: savedValue.source === 'manual' ? 'manual' : 'field',
      field: savedValue.field || '',
    }
  }

  return {
    source: 'field',
    field: savedValue || '',
  }
}

function initVariableInput(variable) {
  const savedConfig = getSavedVariableConfig(variable.name)

  if (!valueSource.value[variable.name]) {
    valueSource.value[variable.name] = savedConfig.source
  }

  if (valueSource.value[variable.name] !== 'manual') {
    fieldMapping.value[variable.name] =
      savedConfig.field || fieldMapping.value[variable.name] || ''
  }

  if (manualValues.value[variable.name] === undefined) {
    manualValues.value[variable.name] = ''
  }
}

function getVariableValue(varName) {
  if (valueSource.value[varName] === 'manual') {
    return manualValues.value[varName] || ''
  }

  const fieldName = fieldMapping.value[varName]
  if (!fieldName || !docValues.value) return ''
  return docValues.value[fieldName] || ''
}

function getPreviewValue(varName) {
  return getVariableValue(varName)
}

const previewText = computed(() => {
  if (!props.templateBody) return ''
  let text = props.templateBody
  variables.value.forEach((v) => {
    const value = getPreviewValue(v.name) || `[${v.name}]`
    text = text.replace(new RegExp(`\\{\\{${v.name}\\}\\}`, 'g'), value)
  })
  return text
})

const isMappingComplete = computed(() => {
  return variables.value.every((v) => {
    if (valueSource.value[v.name] === 'manual') {
      return manualValues.value[v.name]?.trim()
    }
    return fieldMapping.value[v.name]
  })
})

function sendWithVariables() {
  const bodyParam = {}
  const newMapping = {}
  Object.assign(newMapping, existingMapping.value)

  variables.value.forEach((v) => {
    if (valueSource.value[v.name] === 'manual') {
      bodyParam[v.name] = manualValues.value[v.name] || ''
      newMapping[v.name] = { source: 'manual' }
      return
    }

    const fieldName = fieldMapping.value[v.name]
    bodyParam[v.name] = docValues.value[fieldName] || ''
    newMapping[v.name] = { source: 'field', field: fieldName }
  })

  // Save mapping if it changed
  const mappingChanged = JSON.stringify(newMapping) !== JSON.stringify(existingMapping.value)
  if (mappingChanged) {
    saveMappingResource.fetch({
      template_name: props.templateName,
      field_mapping: newMapping,
    })
  }

  emit('send', {
    template: props.templateName,
    body_param: bodyParam,
  })
  show.value = false
}

function sendWithoutVariables() {
  emit('send', {
    template: props.templateName,
    body_param: null,
  })
  show.value = false
}
</script>
