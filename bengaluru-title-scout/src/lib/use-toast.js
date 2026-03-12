import { useState, useEffect, useCallback } from 'react'

const TOAST_LIMIT = 5
const TOAST_REMOVE_DELAY = 4000

let toastCount = 0
let listeners = []
let memoryState = { toasts: [] }

function dispatch(action) {
  memoryState = reducer(memoryState, action)
  listeners.forEach(l => l(memoryState))
}

function reducer(state, action) {
  switch (action.type) {
    case 'ADD_TOAST':
      return { ...state, toasts: [action.toast, ...state.toasts].slice(0, TOAST_LIMIT) }
    case 'DISMISS_TOAST':
      return { ...state, toasts: state.toasts.map(t => t.id === action.toastId ? { ...t, open: false } : t) }
    case 'REMOVE_TOAST':
      return { ...state, toasts: state.toasts.filter(t => t.id !== action.toastId) }
    default:
      return state
  }
}

export function toast({ title, description, variant, duration = TOAST_REMOVE_DELAY }) {
  const id = String(++toastCount)
  dispatch({ type: 'ADD_TOAST', toast: { id, title, description, variant, open: true } })
  setTimeout(() => dispatch({ type: 'DISMISS_TOAST', toastId: id }), duration)
  setTimeout(() => dispatch({ type: 'REMOVE_TOAST', toastId: id }), duration + 300)
  return id
}

export function useToast() {
  const [state, setState] = useState(memoryState)
  useEffect(() => {
    listeners.push(setState)
    return () => { listeners = listeners.filter(l => l !== setState) }
  }, [])
  return { toasts: state.toasts, toast }
}
