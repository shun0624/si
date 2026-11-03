import { atom, read, update } from 'claude-code'
import type { Register, EngineInterface, SessionRateLimit, SessionContextUsage } from 'claude-code'

import type { View } from '../types'

const PANE = 'shinchoku'
const view = atom({ plugin: 'shinchoku-bar', key: 'view' } as const, { progress: '', usage: '' } as View)

type Task = { subject: string; status: 'pending' | 'in_progress' | 'completed' }

const RULE =
  '3つ以上の手順がある作業では、始める前に TaskCreate で手順ごとにタスクを作り、' +
  '着手時に in_progress、終わったら completed に TaskUpdate すること（ユーザーの画面の進捗バーがこれで動く）。' +
  'タスク名は日本語の短い言葉にする。'

const LIMIT_NAMES: Record<string, string> = { five_hour: '5時間枠', seven_day: '週', spend_limit: '利用上限' }
const WARN_AT = 80

// 作業リスト（id → 内容）。新しい依頼で全部終わっていたらリセット
let tasks = new Map<string, Task>()
let todo: Task[] | null = null // 古い形式（TodoWrite）のリスト
let usageText = ''
const warned = new Set<string>()

function bar(done: number, total: number): string {
  const n = Math.round((done / total) * 10)
  return '■'.repeat(n) + '□'.repeat(10 - n)
}

function progressText(): string {
  const list = todo ?? [...tasks.values()]
  if (list.length === 0) return ''
  const done = list.filter(t => t.status === 'completed').length
  const now = list.find(t => t.status === 'in_progress')
  const label = done === list.length ? '完了' : now ? `「${now.subject}」` : ''
  return `進捗 ${bar(done, list.length)} ${done}/${list.length}${label ? ' ' + label : ''}`
}

function contextPercent(c: SessionContextUsage): number | undefined {
  if (c.percent !== undefined) return c.percent
  if (c.tokens !== undefined && c.window > 0) return Math.round((c.tokens / c.window) * 100)
  return undefined
}

async function show($: EngineInterface) {
  const progress = progressText()
  const usage = usageText || '使用量：計測待ち'
  $.ui.status([progress, usage].filter(s => s !== '').join('｜'))
  await update($, view, () => ({ progress, usage }))
}

function allDone(): boolean {
  const list = todo ?? [...tasks.values()]
  return list.length > 0 && list.every(t => t.status === 'completed')
}

export const register: Register = on => {
  // 「手順が多い作業ではやることリストを作る」ルールを Claude に伝える
  on('prompt.compose', async ($, e, next) => {
    const r = await next(e)
    return { sections: [...r.sections, { id: 'shinchoku-bar:rule', text: RULE, scope: 'session' as const }] }
  })

  on('prompt.submit', async ($, e, next) => {
    if (allDone()) {
      tasks = new Map()
      todo = null
      await show($)
    }
    return next(e)
  })

  on('tool.call', { tool: 'TaskCreate' }, async ($, e, next) => {
    const ran = await next(e)
    if (ran.deny === undefined && !ran.isError && ran.result?.task) {
      if (allDone()) tasks = new Map()
      todo = null
      tasks.set(ran.result.task.id, { subject: e.subject, status: 'pending' })
      await show($)
    }
    return ran
  })

  on('tool.call', { tool: 'TaskUpdate' }, async ($, e, next) => {
    const ran = await next(e)
    const t = tasks.get(e.taskId)
    if (ran.deny === undefined && !ran.isError && t) {
      const wasDone = allDone()
      if (e.status === 'deleted') tasks.delete(e.taskId)
      else tasks.set(e.taskId, { subject: e.subject ?? t.subject, status: e.status ?? t.status })
      await show($)
      if (!wasDone && allDone()) $.ui.toast('作業がすべて完了しました')
    }
    return ran
  })

  on('tool.call', { tool: 'TodoWrite' }, async ($, e, next) => {
    const ran = await next(e)
    if (ran.deny === undefined && !ran.isError) {
      const wasDone = allDone()
      todo = e.todos.map(t => ({ subject: t.content, status: t.status }))
      await show($)
      if (!wasDone && allDone()) $.ui.toast('作業がすべて完了しました')
    }
    return ran
  })

  // トークン使用量：作業がひと区切りするたびに届く
  on('session.measure', async ($, e, next) => {
    const parts: string[] = []
    const cp = contextPercent(e.context)
    if (cp !== undefined) parts.push(`容量 ${cp}%`)
    for (const l of e.rateLimits as readonly SessionRateLimit[]) {
      const name = LIMIT_NAMES[l.kind] ?? l.kind
      parts.push(`${name} ${Math.round(l.percentUsed)}%`)
      if (l.percentUsed >= WARN_AT && !warned.has(l.kind)) {
        warned.add(l.kind)
        $.ui.toast(`${name}の利用が${Math.round(l.percentUsed)}%になりました`)
      } else if (l.percentUsed < WARN_AT) warned.delete(l.kind)
    }
    if ((cp ?? 0) >= WARN_AT && !warned.has('context')) {
      warned.add('context')
      $.ui.toast(`会話の容量が${cp}%です。近いうちに古い話が要約されます`)
    } else if ((cp ?? 0) < WARN_AT) warned.delete('context')
    usageText = parts.join('｜')
    await show($)
    return next(e)
  })

  on('command.run', { command: 'shinchoku' }, async $ => {
    const opened = await $.ui.open({ id: PANE, title: '進捗と使用量', focus: true })
    let raw = ''
    try {
      const u = await $.session.usage()
      raw = `容量の生データ: ${JSON.stringify(u.context)} / 利用枠: ${JSON.stringify(u.rateLimits)}`
    } catch (err) {
      raw = `使用量を取得できませんでした: ${String(err)}`
    }
    const v = await read($, view)
    return {
      text:
        `いまの表示：${[v.progress, v.usage].filter(s => s).join('｜') || '（なし）'}\n` +
        `横の画面：${opened.isPlaced ? '表示しました' : '表示できませんでした（' + (opened.reason ?? '理由不明') + '）'}\n` +
        raw,
    }
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text } = $.ui.resolve(e)
    const v = await read($, view)
    return (
      <Box flexDirection="column">
        <Text>{v.progress || '進捗：作業リストはまだありません'}</Text>
        <Text dimColor>{v.usage || '使用量：計測待ち'}</Text>
      </Box>
    )
  })

  // アプリ側に表示場所がないときの代わり：返事の最後に1行だけ出す
  on('turn.complete', async ($, e, next) => {
    const done = await next(e)
    if (e.agentId !== undefined) return done
    if ((await $.session.surfaces()).length === 0) {
      const v = await read($, view)
      const line = [v.progress, v.usage].filter(s => s !== '').join('｜')
      if (line !== '') $.ui.log(`📊 ${line}`)
    }
    return done
  })

  on('session.start', async ($, e, next) => {
    try {
      const u = await $.session.usage()
      const cp = contextPercent(u.context)
      const parts = cp !== undefined ? [`容量 ${cp}%`] : []
      for (const l of u.rateLimits) parts.push(`${LIMIT_NAMES[l.kind] ?? l.kind} ${Math.round(l.percentUsed)}%`)
      usageText = parts.join('｜')
    } catch {
      // 数字が取れなくても表示しないだけ
    }
    await show($)
    await $.command.register({ name: 'shinchoku', description: '【進捗】進捗バーと使用量を横の画面に出す（表示の確認つき）' })
    void $.ui.open({ id: PANE, title: '進捗と使用量' })
    return next(e)
  })
}
