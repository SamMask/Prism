import type { Category } from '../services/api';
import type { TranslationKey } from '../i18n';

type Translate = (key: TranslationKey | string) => string;

const defaultCategoryLabelKeys: Record<string, TranslationKey> = {
  '提示詞 | Prompt': 'categoryDefaults.prompt',
  '筆記 | Note': 'categoryDefaults.note',
  '教學 | Tutorial': 'categoryDefaults.tutorial',
  '資料 | Data': 'categoryDefaults.data',
  '靈感 | Inspiration': 'categoryDefaults.inspiration',
};

export function getDefaultCategoryLabelKey(name?: string | null): TranslationKey | null {
  if (!name) return null;
  return defaultCategoryLabelKeys[name.trim()] ?? null;
}

export function getCategoryDisplayName(
  name: string | undefined | null,
  t: Translate,
  fallback = '',
): string {
  const labelKey = getDefaultCategoryLabelKey(name);
  if (labelKey) return t(labelKey);
  return name || fallback;
}

export function getCategoryEditName(
  name: string | undefined | null,
  t: Translate,
  fallback = '',
): string {
  return getCategoryDisplayName(name, t, fallback);
}

export function getCategoryUpdateName(
  currentName: string | undefined | null,
  editedName: string,
  t: Translate,
): string | undefined {
  const trimmedName = editedName.trim();
  if (trimmedName === (currentName || '').trim()) return undefined;

  if (getDefaultCategoryLabelKey(currentName)) {
    const currentDisplayName = getCategoryDisplayName(currentName, t);
    if (trimmedName === currentDisplayName) return undefined;
  }

  return trimmedName;
}

export function getCategoryOptionLabel(category: Category, t: Translate): string {
  return `${category.icon || '📁'} ${getCategoryDisplayName(category.name, t)}`;
}
