export type View = { progress: string; usage: string }

declare module 'claude-code' {
  interface PluginState {
    'shinchoku-bar': { view: View }
  }
}
