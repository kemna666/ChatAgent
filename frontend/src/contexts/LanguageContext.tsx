import { createContext, ReactNode, useContext, useEffect, useMemo, useState } from 'react';
import {
  LANGUAGE_STORAGE_KEY,
  Language,
  translate,
  TranslationKey,
} from '../i18n/translations';

interface LanguageContextValue {
  language: Language;
  setLanguage: (language: Language) => void;
  t: (key: TranslationKey, variables?: Record<string, string>) => string;
}

const LanguageContext = createContext<LanguageContextValue | null>(null);

function getInitialLanguage(): Language {
  const savedLanguage = localStorage.getItem(LANGUAGE_STORAGE_KEY);
  return savedLanguage === 'en' ? 'en' : 'zh';
}

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguage] = useState<Language>(getInitialLanguage);

  useEffect(() => {
    localStorage.setItem(LANGUAGE_STORAGE_KEY, language);
    document.documentElement.lang = language === 'zh' ? 'zh-CN' : 'en';
  }, [language]);

  const value = useMemo<LanguageContextValue>(() => ({
    language,
    setLanguage,
    t: (key, variables) => translate(language, key, variables),
  }), [language]);

  return (
    <LanguageContext.Provider value={value}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const context = useContext(LanguageContext);

  if (!context) {
    throw new Error('useLanguage must be used within a LanguageProvider');
  }

  return context;
}
