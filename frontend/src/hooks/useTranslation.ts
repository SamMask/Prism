import { availableLocales, translate } from '../i18n';
import { useAppStore } from '../stores/appStore';
import { useCallback } from 'react';

export function useTranslation() {
  const locale = useAppStore((state) => state.locale);
  const setLocale = useAppStore((state) => state.setLocale);
  const t = useCallback(
    (key: string, params?: Record<string, string | number>) => translate(locale, key, params),
    [locale],
  );

  return {
    locale,
    setLocale,
    availableLocales,
    t,
  };
}
