declare module 'claude-code' {
  interface PluginState {
    'komonsaki-guard': { isTainted: boolean }
  }
}
export type Tainted = boolean
