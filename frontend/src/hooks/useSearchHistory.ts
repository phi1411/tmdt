import { useState, useCallback } from 'react';

const STORAGE_KEY = 'novamart_search_history';
const MAX_HISTORY_ITEMS = 8;

export const DEFAULT_TRENDING_SEARCHES = [
  'Điện thoại 5G',
  'Áo thun oversize',
  'Nồi chiên không dầu',
  'Tai nghe bluetooth',
  'Giày sneaker',
  'Robot hút bụi',
  'Sạc nhanh 65W',
];

export function useSearchHistory() {
  const [history, setHistory] = useState<string[]>(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (!stored) return [];
      const parsed = JSON.parse(stored);
      return Array.isArray(parsed) ? parsed.slice(0, MAX_HISTORY_ITEMS) : [];
    } catch {
      return [];
    }
  });

  const saveHistory = useCallback((items: string[]) => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
    } catch {
      // Ignore localStorage write failures
    }
  }, []);

  const addSearch = useCallback(
    (query: string) => {
      const trimmed = query.trim();
      if (!trimmed) return;

      setHistory((prev) => {
        const filtered = prev.filter((item) => item.toLowerCase() !== trimmed.toLowerCase());
        const updated = [trimmed, ...filtered].slice(0, MAX_HISTORY_ITEMS);
        saveHistory(updated);
        return updated;
      });
    },
    [saveHistory]
  );

  const removeSearch = useCallback(
    (query: string) => {
      const trimmed = query.trim();
      setHistory((prev) => {
        const updated = prev.filter((item) => item.toLowerCase() !== trimmed.toLowerCase());
        saveHistory(updated);
        return updated;
      });
    },
    [saveHistory]
  );

  const clearHistory = useCallback(() => {
    setHistory([]);
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      // Ignore localStorage remove failures
    }
  }, []);

  return {
    history,
    addSearch,
    removeSearch,
    clearHistory,
    trendingSearches: DEFAULT_TRENDING_SEARCHES,
  };
}
