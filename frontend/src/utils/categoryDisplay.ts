import type { Category } from '../services/api';
import type { TranslationKey } from '../i18n';

type Translate = (key: TranslationKey | string) => string;
type CategoryLike = Pick<Category, 'name' | 'system_key' | 'name_override'> | string | null | undefined;

const defaultCategoryLabelKeysByName: Record<string, TranslationKey> = {
  '提示詞 | Prompt': 'categoryDefaults.prompt',
  '筆記 | Note': 'categoryDefaults.note',
  '教學 | Tutorial': 'categoryDefaults.tutorial',
  '資料 | Data': 'categoryDefaults.data',
  '靈感 | Inspiration': 'categoryDefaults.inspiration',
};

const defaultCategoryLabelKeysBySystemKey: Record<string, TranslationKey> = {
  prompt: 'categoryDefaults.prompt',
  note: 'categoryDefaults.note',
  tutorial: 'categoryDefaults.tutorial',
  data: 'categoryDefaults.data',
  inspiration: 'categoryDefaults.inspiration',
};

function categoryName(category: CategoryLike): string {
  if (!category) return '';
  return typeof category === 'string' ? category : category.name || '';
}

function categorySystemKey(category: CategoryLike): string {
  if (!category || typeof category === 'string') return '';
  return category.system_key || '';
}

function categoryNameOverride(category: CategoryLike): string {
  if (!category || typeof category === 'string') return '';
  return (category.name_override || '').trim();
}

export function getDefaultCategoryLabelKey(category: CategoryLike): TranslationKey | null {
  const systemKey = categorySystemKey(category);
  if (systemKey) return defaultCategoryLabelKeysBySystemKey[systemKey] ?? null;
  const name = categoryName(category).trim();
  if (!name) return null;
  return defaultCategoryLabelKeysByName[name] ?? null;
}

export function getCategoryDisplayName(
  category: CategoryLike,
  t: Translate,
  fallback = '',
): string {
  const override = categoryNameOverride(category);
  if (override) return override;
  const labelKey = getDefaultCategoryLabelKey(category);
  if (labelKey) return t(labelKey);
  return categoryName(category) || fallback;
}

export function getCategoryEditName(
  category: CategoryLike,
  t: Translate,
  fallback = '',
): string {
  return getCategoryDisplayName(category, t, fallback);
}

export function getCategoryUpdatePayload(
  category: Category,
  editedName: string,
  t: Translate,
): { name?: string; name_override?: string | null } | undefined {
  const trimmedName = editedName.trim();
  const currentName = (category.name || '').trim();
  const currentOverride = (category.name_override || '').trim();
  const labelKey = getDefaultCategoryLabelKey(category);

  if (category.system_key) {
    const defaultDisplayName = labelKey ? t(labelKey) : currentName;
    if (currentOverride) {
      if (trimmedName === currentOverride) return undefined;
      if (trimmedName === defaultDisplayName) return { name_override: null };
      return { name_override: trimmedName };
    }
    if (trimmedName === defaultDisplayName) return undefined;
    return { name_override: trimmedName };
  }

  if (trimmedName === currentName) return undefined;
  if (labelKey && trimmedName === getCategoryDisplayName(category, t)) return undefined;
  return { name: trimmedName };
}

export function getCategoryOptionLabel(category: Category, t: Translate): string {
  return `${category.icon || '📁'} ${getCategoryDisplayName(category, t)}`;
}
