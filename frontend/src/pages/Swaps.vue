<template>
  <div>
    <h1 class="brand">对调</h1>
    <p class="muted">先生成周表,再填写两格对调(day + task_id);双方各自签名后才会改表</p>
    <div class="week-card" style="margin-bottom:12px">
      <label>A day <input type="number" v-model.number="form.a_day" /></label>
      <label>A task_id <input type="number" v-model.number="form.a_task" /></label>
      <label>B day <input type="number" v-model.number="form.b_day" /></label>
      <label>B task_id <input type="number" v-model.number="form.b_task" /></label>
      <button @click="request">申请对调</button>
    </div>
    <p v-if="err" class="err">{{ err }}</p>
    <ul class="list">
      <li v-for="s in rows" :key="s.id">
        #{{ s.id }} D{{ s.a_day }}/T{{ s.a_task }} ↔ D{{ s.b_day }}/T{{ s.b_task }}
        <span class="chip" :class="{ coral: s.status!=='confirmed' }">{{ statusText(s.status) }}</span>
        <span class="chip" :class="signClass(s.sign_a)">{{ nameOf(s.a_member) }}:{{ signText(s.sign_a) }}</span>
        <span class="chip" :class="signClass(s.sign_b)">{{ nameOf(s.b_member) }}:{{ signText(s.sign_b) }}</span>
        <template v-if="s.status==='pending'">
          <button class="ghost sm" @click="sign(s.id, s.a_member, 'sign')">{{ nameOf(s.a_member) }}签</button>
          <button class="ghost sm" @click="sign(s.id, s.b_member, 'sign')">{{ nameOf(s.b_member) }}签</button>
          <button class="ghost sm" @click="sign(s.id, s.a_member, 'reject')">拒签</button>
          <button class="sm" :disabled="!s.dual_signed" @click="confirm(s.id)">确认改表</button>
        </template>
      </li>
    </ul>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api'
const rows = ref([])
const members = ref({})
const err = ref('')
const form = ref({ a_day: 0, a_task: 1, b_day: 1, b_task: 1 })
function nameOf(id) { return members.value[id] || ('成员' + id) }
function signText(st) { return { signed: '已签', rejected: '已拒', pending: '待签' }[st] || st }
function signClass(st) { return st === 'signed' ? '' : (st === 'rejected' ? 'coral' : 'dim') }
function statusText(st) { return { pending: '待双签', confirmed: '已确认', rejected: '已拒签' }[st] || st }
async function load() {
  rows.value = await api('/swaps')
  const ms = await api('/members')
  members.value = Object.fromEntries(ms.map(m => [m.id, m.name]))
}
async function request() {
  err.value = ''
  try {
    await api('/weeks/1/swaps', { method: 'POST', body: JSON.stringify(form.value) })
    await load()
  } catch (e) { err.value = e.message }
}
async function sign(id, memberId, decision) {
  err.value = ''
  try {
    await api('/swaps/' + id + '/sign', { method: 'POST', body: JSON.stringify({ member_id: memberId, decision }) })
    await load()
  } catch (e) { err.value = e.message }
}
async function confirm(id) {
  err.value = ''
  try { await api('/swaps/' + id + '/confirm', { method: 'POST', body: '{}' }); await load() }
  catch (e) { err.value = e.message }
}
onMounted(load)
</script>
