import { availableLocales, translate, type TranslationKey, type TranslationParams } from '../i18n';
import { useAppStore } from '../stores/appStore';
import { useCallback } from 'react';

type TranslateFunction = {
  (key: TranslationKey, params?: TranslationParams): string;
  (key: string, params?: TranslationParams): string;
};

export function useTranslation() {
  const locale = useAppStore((state) => state.locale);
  const setLocale = useAppStore((state) => state.setLocale);
  const t = useCallback(((key: string, params?: TranslationParams) => (
    translate(locale, key, params)
  )) as TranslateFunction, [locale]);

  return {
    locale,
    setLocale,
    availableLocales,
    t,
  };
}
