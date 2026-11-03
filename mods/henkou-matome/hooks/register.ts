import type { Register } from 'claude-code'

type Change = { path: string; detail: string }
type Entry = { at: string; summary: string }

const MAX_PER_FILE = 1500
const MAX_TOTAL = 9000

let request = ''
let changes: Change[] = []
const history: Entry[] = []

function cut(s: string, n: number): string {
  return s.length > n ? s.slice(0, n) + '…（省略）' : s
}

function shortPath(p: string): string {
  return p.replace(/^\/home\/user\//, '')
}

function timeJst(ms: number): string {
  const d = new Date(ms + 9 * 3600 * 1000)
  const hh = String(d.getUTCHours()).padStart(2, '0')
  const mm = String(d.getUTCMinutes()).padStart(2, '0')
  return `${d.getUTCMonth() + 1}/${d.getUTCDate()} ${hh}:${mm}`
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'henkou',
      description: '【変更まとめ】この会話でのファイル変更のまとめを一覧で見る',
    })
    return next(e)
  })

  on('command.run', { command: 'henkou' }, () => {
    if (history.length === 0) return { text: 'まだ変更のまとめはありません。' }
    return {
      text: history.map(h => `■ ${h.at}\n${h.summary}`).join('\n\n'),
    }
  })

  on('prompt.submit', ($, e, next) => {
    if (e.origin.kind !== 'plugin') {
      request = cut(e.text, 1000)
      changes = []
    }
    return next(e)
  })

  on('tool.call', { tool: 'Edit' }, async ($, e, next) => {
    const ran = await next(e)
    if (ran.deny === undefined && !ran.isError) {
      changes.push({
        path: shortPath(e.file_path),
        detail: `変更前:\n${cut(e.old_string, MAX_PER_FILE / 2)}\n変更後:\n${cut(e.new_string, MAX_PER_FILE / 2)}`,
      })
    }
    return ran
  })

  on('tool.call', { tool: 'Write' }, async ($, e, next) => {
    const ran = await next(e)
    if (ran.deny === undefined && !ran.isError) {
      changes.push({ path: shortPath(e.file_path), detail: `新しい内容:\n${cut(e.content, MAX_PER_FILE)}` })
    }
    return ran
  })

  on('turn.complete', async ($, e, next) => {
    const done = await next(e)
    if (e.agentId !== undefined || changes.length === 0 || e.reason !== 'answer') return done

    const list = changes
    changes = []
    let body = ''
    for (const c of list) {
      const part = `### ${c.path}\n${c.detail}\n\n`
      if (body.length + part.length > MAX_TOTAL) {
        body += `（ほか ${list.length - list.indexOf(c)} 件の変更は省略）\n`
        break
      }
      body += part
    }
    const files = [...new Set(list.map(c => c.path))]

    try {
      const r = await $.model.complete({
        model: 'haiku',
        maxTokens: 400,
        system:
          'あなたはプログラムを書かない人に、ファイルの変更内容を説明する係です。' +
          '専門用語を使わず、やさしい日本語で、次の3行だけを出力してください（前置きや締めは不要）。\n' +
          '何を：（何を変えたか）\n' +
          'なぜ：（なぜ変えたか。依頼内容から）\n' +
          '影響：（使う人から見て何が変わるか。注意点があれば）',
        prompt:
          `【ユーザーの依頼】\n${request}\n\n【作業後の返答（抜粋）】\n${cut(e.answer, 1500)}\n\n` +
          `【変更したファイルと内容】\n${body}`,
      })
      const at = timeJst(await $.clock.now())
      const summary =
        (r.isAnswered ? r.text.trim() : '（まとめを作れませんでした）') +
        `\n対象：${files.join('、')}`
      history.push({ at, summary })
      $.ui.log(`📝 変更のまとめ（${at}）\n${summary}`)
    } catch {
      $.ui.log(`📝 変更したファイル：${files.join('、')}（まとめは作れませんでした）`)
    }
    return done
  })
}
