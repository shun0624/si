import type { Register } from 'claude-code'

const SCRIPT = ['tools/price_compare.py', 'si/tools/price_compare.py', '/home/user/si/tools/price_compare.py']
const PYTHONS = ['python3', 'python', 'py']

function todayJst(ms: number): string {
  const d = new Date(ms + 9 * 3600 * 1000)
  return `${d.getUTCFullYear()}年${d.getUTCMonth() + 1}月${d.getUTCDate()}日`
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'nedan',
      argumentHint: '品番 [--max 上限価格]',
      description: '【値段】楽天とYahoo!を安い順に比べる（例: /nedan BS2039009 --max 30000）',
    })
    return next(e)
  })

  on('command.run', { command: 'nedan' }, async ($, e) => {
    const args = e.args.trim()
    if (args === '') {
      return { text: '使い方: /nedan 品番（例: /nedan BS2039009、上限つき: /nedan BS2039009 --max 30000）' }
    }
    const words = args.split(/\s+/)
    const date = todayJst(await $.clock.now())
    $.ui.status(`値段を調べています: ${words[0]}`)

    let lastError = 'price_compare.py が見つかりませんでした（si リポジトリの中で開いてください）。'
    for (const py of PYTHONS) {
      for (const script of SCRIPT) {
        let r
        try {
          r = await $.process.run([py, script, ...words], { timeoutMs: 60_000 })
        } catch {
          break // この python は無い → 次の python へ
        }
        if (/Python was not found|not recognized/i.test(r.stderr)) break
        if (/can't open file|No such file/i.test(r.stderr)) continue
        $.ui.status(undefined)
        const body = (r.stdout + (r.exitCode !== 0 ? `\n${r.stderr}` : '')).trim()
        return {
          text: `【${words[0]} の価格比較】（${date} 調べ・楽天/Yahoo! 安い順）\n${body}`,
          context: [`/nedan の結果（${date}調べ）です。必要ならユーザーにおすすめを日本語で短く説明してください。`],
        }
      }
    }
    $.ui.status(undefined)
    return { text: lastError }
  })
}
