import { useCallback, useState } from 'react';

function read<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw === null ? fallback : (JSON.parse(raw) as T);
  } catch {
    return fallback;
  }
}

function write<T>(key: string, value: T) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Storage full or blocked (private window): the value still lives until the page is left.
  }
}

/** useState that is saved to localStorage, so it survives page switches and refreshes.
 *  The setter writes storage immediately, so a request that finishes after the farmer
 *  has left the page still leaves its result for when they come back. */
export function usePersistedState<T>(key: string, initial: T) {
  const [value, setValue] = useState<T>(() => read(key, initial));
  const set = useCallback(
    (next: T) => {
      write(key, next);
      setValue(next);
    },
    [key],
  );
  return [value, set] as const;
}
