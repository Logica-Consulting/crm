<template>
  <LayoutHeader>
    <template #left-header>
      <div
        class="flex items-center gap-2 text-lg font-semibold text-ink-gray-9"
      >
        <WhatsAppIcon class="size-5" />
        <span>{{ __('Whatsapp') }}</span>
      </div>
    </template>
    <template #right-header>
      <FormControl
        v-model="search"
        type="text"
        :placeholder="__('Filter chats')"
        class="w-64"
      />
      <Button :loading="loading" :label="__('Refresh')" @click="reload" />
    </template>
  </LayoutHeader>

  <div class="flex h-full flex-col overflow-hidden">
    <ListView
      v-if="rows.length"
      :columns="columns"
      :rows="rows"
      :options="{
        getRowRoute: (row) => row.route,
        selectable: false,
        showTooltip: false,
        resizeColumn: true,
      }"
      row-key="name"
      class="flex-1 overflow-hidden"
    >
      <ListHeader class="mx-3 sm:mx-5">
        <ListHeaderItem
          v-for="column in columns"
          :key="column.key"
          :item="column"
        >
          <button
            class="flex w-full items-center gap-1 truncate text-left"
            @click="toggleSort(column.key)"
          >
            <span class="truncate">{{ column.label }}</span>
            <span v-if="sortField === column.key" class="text-ink-gray-5">
              {{ sortDirection === 'asc' ? '↑' : '↓' }}
            </span>
          </button>
        </ListHeaderItem>
      </ListHeader>
      <ListRows v-slot="{ column, item }" :rows="rows" doctype="WhatsApp Chat">
        <ListRowItem :item="item" :align="column.align" class="overflow-hidden">
          <template #default>
            <Tooltip
              v-if="column.key === 'last_message_on'"
              :text="formatExactDate(item)"
            >
              <div class="truncate text-base">
                {{ formatLastMessageTime(item) }}
              </div>
            </Tooltip>
            <div v-else class="truncate text-base">
              {{ item }}
            </div>
          </template>
        </ListRowItem>
      </ListRows>
    </ListView>

    <div
      v-else-if="!loading"
      class="flex flex-1 flex-col items-center justify-center gap-3 text-ink-gray-5"
    >
      <WhatsAppIcon class="size-10" />
      <div>{{ __('No WhatsApp chats found') }}</div>
    </div>

    <div v-else class="flex flex-1 items-center justify-center text-ink-gray-5">
      {{ __('Loading...') }}
    </div>

    <div
      v-if="
        chats.page_length_count && chats.page_length_count < chats.total_count
      "
      class="border-t px-3 py-2 sm:px-5"
    >
      <Button :loading="loading" :label="__('Load more')" @click="loadMore" />
    </div>
  </div>
</template>

<script setup>
import WhatsAppIcon from '@/components/Icons/WhatsAppIcon.vue'
import LayoutHeader from '@/components/LayoutHeader.vue'
import ListRows from '@/components/ListViews/ListRows.vue'
import { formatDate } from '@/utils'
import {
  Button,
  FormControl,
  ListView,
  ListHeader,
  ListHeaderItem,
  ListRowItem,
  Tooltip,
  call,
  dayjsLocal,
} from 'frappe-ui'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const pageLength = 20
const search = ref('')
const sortField = ref('last_message_on')
const sortDirection = ref('desc')
const loading = ref(false)
const chats = ref({
  data: [],
  row_count: 0,
  total_count: 0,
  page_length_count: 0,
})

const columns = [
  {
    label: __('Lead/Deal'),
    key: 'title',
    width: '18rem',
  },
  {
    label: __('Last message'),
    key: 'preview',
    width: '1fr',
  },
  {
    label: __('Last message at'),
    key: 'last_message_on',
    width: '12rem',
    align: 'right',
  },
]

const rows = computed(() => chats.value.data || [])

let searchTimeout

watch(search, () => {
  window.clearTimeout(searchTimeout)
  searchTimeout = window.setTimeout(() => reload(), 300)
})

onMounted(() => reload())

onBeforeUnmount(() => {
  window.clearTimeout(searchTimeout)
})

function orderBy() {
  return `${sortField.value} ${sortDirection.value}`
}

async function fetchChats(start = 0) {
  loading.value = true
  try {
    let response = await call('crm.api.whatsapp.get_whatsapp_chats', {
      search: search.value,
      order_by: orderBy(),
      start,
      page_length: pageLength,
    })

    if (start) {
      chats.value = {
        ...response,
        data: [...(chats.value.data || []), ...(response.data || [])],
      }
    } else {
      chats.value = response
    }
  } finally {
    loading.value = false
  }
}

function reload() {
  return fetchChats(0)
}

function loadMore() {
  return fetchChats(chats.value.page_length_count || 0)
}

function toggleSort(fieldname) {
  if (!['title', 'last_message_on'].includes(fieldname)) return

  if (sortField.value === fieldname) {
    sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortField.value = fieldname
    sortDirection.value = fieldname === 'title' ? 'asc' : 'desc'
  }
  reload()
}

function formatLastMessageTime(value) {
  if (!value) return ''

  let messageDate = dayjsLocal(value)
  let today = dayjsLocal().startOf('day')
  let messageDay = messageDate.startOf('day')
  let dayDiff = today.diff(messageDay, 'day')

  if (dayDiff <= 0) return messageDate.format('HH:mm')
  if (dayDiff === 1) return __('Ayer')
  return __('Hace {0} días', [dayDiff])
}

function formatExactDate(value) {
  return formatDate(value, undefined, true, true)
}
</script>
