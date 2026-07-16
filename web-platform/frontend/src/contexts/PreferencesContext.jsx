import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { applyColorMode } from '../theme/tokens';
import { translations } from '../i18n/translations';

const PreferencesContext = createContext(null);

const MODE_KEY = 'pref_theme_mode';
const LANG_KEY = 'pref_lang';

function initialMode() {
  const saved = localStorage.getItem(MODE_KEY);
  if (saved === 'light' || saved === 'dark') return saved;
  return 'dark';
}

function initialLang() {
  const saved = localStorage.getItem(LANG_KEY);
  if (saved === 'fr' || saved === 'en') return saved;
  if (saved === 'zh') return 'fr'; // legacy: migrate old Chinese preference to French
  // Default to English only for English browsers; otherwise French.
  return (navigator.language || '').toLowerCase().startsWith('en') ? 'en' : 'fr';
}

/** Interpolate {name} style placeholders. */
function interpolate(str, vars) {
  if (!vars) return str;
  return str.replace(/\{(\w+)\}/g, (_, k) => (vars[k] != null ? vars[k] : `{${k}}`));
}

export function PreferencesProvider({ children }) {
  const [mode, setMode] = useState(initialMode);
  const [lang, setLang] = useState(initialLang);

  // Keep the shared palette + <html data-theme> in sync with the mode.
  // Runs synchronously enough before paint via layout effect semantics; we
  // also mutate the palette immediately so first render is correct.
  applyColorMode(mode);

  useEffect(() => {
    applyColorMode(mode);
    document.documentElement.setAttribute('data-theme', mode);
    localStorage.setItem(MODE_KEY, mode);
  }, [mode]);

  useEffect(() => {
    document.documentElement.setAttribute('lang', lang === 'fr' ? 'fr' : 'en');
    localStorage.setItem(LANG_KEY, lang);
  }, [lang]);

  const value = useMemo(() => {
    const dict = translations[lang] || translations.en;
    const t = (key, vars) => {
      const raw = dict[key] ?? translations.en[key] ?? key;
      return interpolate(raw, vars);
    };
    return {
      mode,
      lang,
      t,
      isLight: mode === 'light',
      toggleMode: () => setMode((m) => (m === 'dark' ? 'light' : 'dark')),
      setMode,
      toggleLang: () => setLang((l) => (l === 'en' ? 'fr' : 'en')),
      setLang,
    };
  }, [mode, lang]);

  return <PreferencesContext.Provider value={value}>{children}</PreferencesContext.Provider>;
}

export function useI18n() {
  const ctx = useContext(PreferencesContext);
  if (!ctx) throw new Error('useI18n must be used within PreferencesProvider');
  return ctx;
}
