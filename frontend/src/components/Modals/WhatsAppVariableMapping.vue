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
              v-model="fieldMapping[variable.name]"
              class="flex-1"
              :options="fieldOptions"
              :placeholder="__('Select a field')"
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
const docFields = ref([])
const docValues = ref({})

const getVariablesResource = createResource({
  url: 'crm.api.whatsapp.get_template_variables',
  onSuccess: (data) => {
    variables.value = data || []
    // Initialize field mapping
    variables.value.forEach((v) => {
      fieldMapping.value[v.name] = ''
    })
    loading.value = false
  },
  onError: () => {
    loading.value = false
  },
})

const getDocFieldsResource = createResource({
  url: 'frappe.client.get',
  onSuccess: (data) => {
    if (data && data.fields) {
      docFields.value = data.fields
        .filter(
          (f) =>
            f.fieldtype &&
            !['Section Break', 'Column Break', 'Tab Break'].includes(
              f.fieldtype,
            ) &&
            f.fieldname,
        )
        .map((f) => ({
          label: f.label || f.fieldname,
          value: f.fieldname,
        }))
    }
    // Get doc values for preview
    if (props.docname) {
      createResource({
        url: 'frappe.client.get',
        params: {
          doctype: props.doctype,
          name: props.docname,
        },
        auto: true,
        onSuccess: (docData) => {
          docValues.value = docData || {}
        },
      }).fetch()
    }
  },
})

watch(
  () => props.templateName,
  (newVal) => {
    if (newVal && show.value) {
      loadTemplateVariables()
    }
  },
  { immediate: true },
)

watch(show, (newVal) => {
  if (newVal && props.templateName) {
    loadTemplateVariables()
  }
})

function loadTemplateVariables() {
  loading.value = true
  variables.value = []
  fieldMapping.value = {}

  getVariablesResource.fetch({ template: props.templateName })

  // Load doc fields for mapping
  if (!docFields.value.length) {
    getDocFieldsResource.fetch({
      doctype: 'DocType',
      name: props.doctype,
    })
  }
}

const fieldOptions = computed(() => {
  return [{ label: __('-- Select field --'), value: '' }, ...docFields.value]
})

function getPreviewValue(varName) {
  const fieldName = fieldMapping.value[varName]
  if (!fieldName || !docValues.value) return ''
  return docValues.value[fieldName] || ''
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
  return variables.value.every((v) => fieldMapping.value[v.name])
})

function sendWithVariables() {
  const bodyParam = {}
  variables.value.forEach((v) => {
    const fieldName = fieldMapping.value[v.name]
    bodyParam[v.name] = docValues.value[fieldName] || ''
  })
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
