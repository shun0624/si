import { atom, update } from 'claude-code'
import type { Register } from 'claude-code'

// 顧問先フォルダの場所（「01_税務会計」の中の「10_顧問先」）。
// 説明文などに名前が出ただけで反応しないよう、フォルダの区切りつきで探す
const MARK = new RegExp(['01_税務会計', '10_顧問先'].join('[\\\\/]+'))
// 読んだ結果の中身まで見るのは Google 系（ドライブ等）だけ。ほかは操作の指示（開いた場所）だけを見る
const RESULT_CHECKED = /^mcp__Google_/

// 外へデータが出ていく操作
const OUTBOUND_TOOLS = new Set(['WebFetch', 'WebSearch'])
const OUTBOUND_BASH =
  /\b(curl|wget|Invoke-WebRequest|iwr|ssh|scp|rsync|ftp|nc)\b|price_compare|rakuten_search|yahoo_search|https?:\/\/|git\s+push|requests\./i
// Google系（ドライブ・ドキュメント等＝保管場所そのもの）は外部送信とみなさない
const SAFE_MCP = /^mcp__(Google_|claude-code-remote__|ccd_session__|plugin-authoring__)/

const tainted = atom({ plugin: 'komonsaki-guard', key: 'isTainted' } as const, false)

function isOutbound(e: { tool: string; [k: string]: unknown }): boolean {
  if (OUTBOUND_TOOLS.has(e.tool)) return true
  if (e.tool === 'Bash' || e.tool === 'PowerShell') {
    return OUTBOUND_BASH.test(String(e.command ?? ''))
  }
  if (e.tool.startsWith('mcp__')) return !SAFE_MCP.test(e.tool)
  return false
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'komonsaki-off',
      description: '【顧問先解除】顧問先ガードを解除する（顧問先の資料を扱い終わったとき）',
    })
    return next(e)
  })

  on('command.run', { command: 'komonsaki-off' }, async $ => {
    await update($, tainted, () => false)
    $.ui.status(undefined)
    return { text: '顧問先ガードを解除しました。外部サービスへの送信はふだんどおりに戻ります。' }
  })

  on('tool.call', async ($, e, next) => {
    let isOn = false
    await update($, tainted, v => ((isOn = v), v))

    if (isOn && isOutbound(e)) {
      let answer = ''
      try {
        answer = await $.ui.ask(
          `顧問先の資料を読んだあとに、外部へ送る操作（${e.tool}）をしようとしています。許可しますか？`,
          ['止める', '今回だけ許可'],
        )
      } catch {
        answer = '止める'
      }
      if (answer !== '今回だけ許可') {
        return {
          deny:
            '顧問先ガード: 顧問先の資料を読んだあとなので、外部サービスへの送信を止めました。' +
            '顧問先の情報を含めずに進めるか、ユーザーに確認してください（解除はユーザーが /komonsaki-off）。',
        }
      }
    }

    const ran = await next(e)

    if (!isOn) {
      const seen =
        JSON.stringify(e) +
        (RESULT_CHECKED.test(e.tool) && ran.deny === undefined ? String(ran.text ?? '') : '')
      if (MARK.test(seen)) {
        await update($, tainted, () => true)
        $.ui.status('顧問先ガード：ON（外部送信は確認あり）')
        $.ui.toast('顧問先の資料を読んだので、外部送信の前に確認します')
      }
    }
    return ran
  }).catch(($, e, next) =>
    next.called ? next(e) : { deny: '顧問先ガード: 確認の仕組みでエラーが起きたため、念のため止めました。' },
  )
}
