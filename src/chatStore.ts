// Chat history kept outside the Chat page so it survives page switches, and saved to
// localStorage so it survives a refresh. A question still waiting for an answer keeps
// running when the farmer leaves the page; its reply lands here either way.
import { useSyncExternalStore } from 'react';
import { api, type ChatReply } from './api';

export type Message =
  | { role: 'user'; text: string }
  | { role: 'bot'; reply: ChatReply }
  | { role: 'error'; text: string };

interface ChatState {
  messages: Message[];
  busy: boolean;
}

const STORAGE_KEY = 'uzhavan-chat-v1';
const MAX_SAVED = 50;

function load(): Message[] {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]');
    return Array.isArray(saved) ? saved : [];
  } catch {
    return [];
  }
}

function save(messages: Message[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(messages.slice(-MAX_SAVED)));
  } catch {
    // Storage full or blocked (private window): history still lives for this session.
  }
}

let state: ChatState = { messages: load(), busy: false };
const listeners = new Set<() => void>();

function setState(next: Partial<ChatState>) {
  state = { ...state, ...next };
  save(state.messages);
  listeners.forEach((l) => l());
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function useChat() {
  return useSyncExternalStore(subscribe, () => state);
}

export async function sendMessage(text: string) {
  const q = text.trim();
  if (!q || state.busy) return;
  setState({ messages: [...state.messages, { role: 'user', text: q }], busy: true });
  try {
    const reply = await api.chat(q);
    setState({ messages: [...state.messages, { role: 'bot', reply }], busy: false });
  } catch (e) {
    setState({ messages: [...state.messages, { role: 'error', text: (e as Error).message }], busy: false });
  }
}

export function clearChat() {
  if (!state.busy) setState({ messages: [] });
}
