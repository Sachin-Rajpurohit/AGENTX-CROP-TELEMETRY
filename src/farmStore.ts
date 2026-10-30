// The farmer's farms (from the server) and which one is selected (remembered in this browser).
// Every page reads the selected farm from here, so switching farms in the header updates them all.
import { useSyncExternalStore } from 'react';
import { api, type Farm } from './api';

interface FarmState {
  farms: Farm[];
  selectedId: string | null;
  loaded: boolean;
  error: string;
}

const SELECTED_KEY = 'uzhavan-selected-farm';

function readSelected(): string | null {
  try {
    return localStorage.getItem(SELECTED_KEY);
  } catch {
    return null;
  }
}

let state: FarmState = { farms: [], selectedId: readSelected(), loaded: false, error: '' };
const listeners = new Set<() => void>();

function setState(next: Partial<FarmState>) {
  state = { ...state, ...next };
  try {
    if (state.selectedId) localStorage.setItem(SELECTED_KEY, state.selectedId);
  } catch {
    // Blocked storage: the selection still lasts for this session.
  }
  listeners.forEach((l) => l());
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function useFarms() {
  const s = useSyncExternalStore(subscribe, () => state);
  const selected = s.farms.find((f) => f.id === s.selectedId) ?? null;
  return { ...s, selected };
}

/** Fetch the farm list; keep the selection if it still exists, else pick the first farm. */
export async function loadFarms(preferId?: string) {
  try {
    const farms = await api.farms();
    const wanted = preferId ?? state.selectedId;
    const selectedId = farms.some((f) => f.id === wanted) ? wanted : (farms[0]?.id ?? null);
    setState({ farms, selectedId, loaded: true, error: '' });
  } catch (e) {
    setState({ loaded: true, error: (e as Error).message });
  }
}

export function selectFarm(id: string) {
  setState({ selectedId: id });
}

export function selectedFarm(): Farm | null {
  return state.farms.find((f) => f.id === state.selectedId) ?? null;
}
