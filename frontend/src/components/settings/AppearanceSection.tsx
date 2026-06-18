
import { useState } from 'react';
import { Sun, Moon, Check, LayoutGrid, List, AlignJustify, Languages } from 'lucide-react';
import { Button, toast } from '../ui';
import { Category } from '../../services/api';
import { useAppStore, type ViewMode } from '../../stores/appStore';
import { useTranslation } from '../../hooks/useTranslation';
import { type Locale, translate } from '../../i18n';
import { getCategoryDisplayName, getCategoryOptionLabel } from '../../utils/categoryDisplay';

interface AppearanceSectionProps {
  categories: Category[];
}

type AccentColor = 'default' | 'cyberpunk' | 'eye-care' | 'elegant' | 'ocean' | 'sunset';
type BackgroundScheme = 'neutral' | 'black' | 'warm' | 'green' | 'paper';
type CardOpenMode = 'preview' | 'edit';
const SIDEBAR_WIDTH_MIN = 150;
const SIDEBAR_WIDTH_MAX = 320;

const clampNumber = (value: number, min: number, max: number) => {
  return Math.min(Math.max(value, min), max);
};

const readNumberSetting = (key: string, fallback: number, min: number, max: number) => {
  const value = Number(localStorage.getItem(key));
  return Number.isFinite(value) ? clampNumber(value, min, max) : fallback;
};

const setRootPixelVariable = (name: string, value: number) => {
  document.documentElement.style.setProperty(name, `${value}px`);
};

const readCardOpenMode = (): CardOpenMode => {
  return localStorage.getItem('cardOpenMode') === 'edit' ? 'edit' : 'preview';
};

const accentOptions: Array<{ id: AccentColor; name: string; labelKey: string; color: string }> = [
  { id: 'default', name: '專業藍', labelKey: 'settings.appearance.accent.default', color: '#3b82f6' },
  { id: 'cyberpunk', name: '賽博龐克', labelKey: 'settings.appearance.accent.cyberpunk', color: '#e879f9' },
  { id: 'eye-care', name: '護眼綠', labelKey: 'settings.appearance.accent.eyeCare', color: '#34d399' },
  { id: 'elegant', name: '典雅金', labelKey: 'settings.appearance.accent.elegant', color: '#d4a574' },
  { id: 'ocean', name: '海洋青', labelKey: 'settings.appearance.accent.ocean', color: '#14b8a6' },
  { id: 'sunset', name: '夕陽橙', labelKey: 'settings.appearance.accent.sunset', color: '#f97316' },
];

const backgroundOptions: Array<{ id: BackgroundScheme; name: string; labelKey: string; colors: [string, string, string] }> = [
  { id: 'neutral', name: '預設藍灰', labelKey: 'settings.appearance.background.neutral', colors: ['#0b1020', '#141a2a', '#263247'] },
  { id: 'black', name: '純黑', labelKey: 'settings.appearance.background.black', colors: ['#000000', '#080808', '#1a1a1a'] },
  { id: 'warm', name: '暖灰', labelKey: 'settings.appearance.background.warm', colors: ['#17130f', '#211c17', '#3a3128'] },
  { id: 'green', name: '護眼灰綠', labelKey: 'settings.appearance.background.green', colors: ['#0d1511', '#14201a', '#2a3a31'] },
  { id: 'paper', name: '紙張米色', labelKey: 'settings.appearance.background.paper', colors: ['#f4ecd9', '#fbf5e4', '#d4c8a4'] },
];

export function AppearanceSection({ categories }: AppearanceSectionProps) {
  const { viewMode, setViewMode } = useAppStore();
  const { locale, setLocale, availableLocales, t } = useTranslation();
  const [theme, setTheme] = useState<'dark' | 'light'>(() => {
    return (localStorage.getItem('theme') as 'dark' | 'light') || 'light';
  });
  const [accentColor, setAccentColor] = useState<AccentColor>(() => {
    const savedAccent =
      (localStorage.getItem('prism.accentColor') || localStorage.getItem('colorTheme')) as AccentColor | null;
    return savedAccent && accentOptions.some((option) => option.id === savedAccent) ? savedAccent : 'elegant';
  });
  const [backgroundScheme, setBackgroundScheme] = useState<BackgroundScheme>(() => {
    const savedScheme = localStorage.getItem('prism.backgroundScheme') as BackgroundScheme | null;
    return savedScheme && backgroundOptions.some((option) => option.id === savedScheme) ? savedScheme : 'warm';
  });
  const [cornerRadius, setCornerRadius] = useState(() => readNumberSetting('prism.cornerRadius', 10, 4, 24));
  const [sidebarWidth, setSidebarWidth] = useState(() => (
    readNumberSetting('prism.sidebarWidth', 248, SIDEBAR_WIDTH_MIN, SIDEBAR_WIDTH_MAX)
  ));
  const [cardOpenMode, setCardOpenMode] = useState<CardOpenMode>(() => readCardOpenMode());
  const [autoLoadMore, setAutoLoadMore] = useState(() => localStorage.getItem('autoLoadMore') !== 'false');

  // Toggle theme
  const toggleTheme = () => {
    const newTheme = theme === 'dark' ? 'light' : 'dark';
    setTheme(newTheme);
    localStorage.setItem('theme', newTheme);
    document.documentElement.classList.toggle('light', newTheme === 'light');
    document.documentElement.setAttribute('data-mode', newTheme);
    toast.success(t('settings.appearance.theme.switched', {
      theme: t(newTheme === 'dark' ? 'settings.appearance.theme.dark' : 'settings.appearance.theme.light'),
    }));
  };

  const setAccent = (color: AccentColor, label: string) => {
    setAccentColor(color);
    localStorage.setItem('prism.accentColor', color);
    localStorage.setItem('colorTheme', color);
    document.documentElement.setAttribute('data-accent', color);
    toast.success(t('settings.appearance.accent.changed', { label }));
  };

  const setBackground = (scheme: BackgroundScheme, label: string) => {
    setBackgroundScheme(scheme);
    localStorage.setItem('prism.backgroundScheme', scheme);
    document.documentElement.setAttribute('data-bg', scheme);
    toast.success(t('settings.appearance.background.changed', { label }));
  };

  const updateCornerRadius = (value: number) => {
    const nextValue = clampNumber(value, 4, 24);
    setCornerRadius(nextValue);
    localStorage.setItem('prism.cornerRadius', String(nextValue));
    setRootPixelVariable('--prism-corner-radius', nextValue);
  };

  const updateSidebarWidth = (value: number) => {
    const nextValue = clampNumber(value, SIDEBAR_WIDTH_MIN, SIDEBAR_WIDTH_MAX);
    setSidebarWidth(nextValue);
    localStorage.setItem('prism.sidebarWidth', String(nextValue));
    setRootPixelVariable('--prism-sidebar-width', nextValue);
    setRootPixelVariable('--sidebar-w', nextValue);
  };

  const viewOptions: Array<{ value: ViewMode; label: string; labelKey: string; icon: typeof LayoutGrid }> = [
    { value: 'grid', label: '網格', labelKey: 'settings.appearance.view.grid', icon: LayoutGrid },
    { value: 'list', label: '列表', labelKey: 'settings.appearance.view.list', icon: List },
    { value: 'compact', label: '精簡', labelKey: 'settings.appearance.view.compact', icon: AlignJustify },
  ];

  return (
    <div className="glass rounded-xl p-6">
      <h2 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
        <Sun size={20} className="text-primary" />
        {t('settings.appearance.title')}
      </h2>
      
      {/* Dark/Light Mode */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <p className="text-text-primary">{t('settings.appearance.theme.title')}</p>
          <p className="text-text-muted text-sm">
            {t('settings.appearance.theme.description')}
          </p>
        </div>
        <Button
          onClick={toggleTheme}
          variant="secondary"
          className="flex items-center gap-2"
        >
          {theme === 'dark' ? <Moon size={18} /> : <Sun size={18} />}
          {t(theme === 'dark' ? 'settings.appearance.theme.dark' : 'settings.appearance.theme.light')}
        </Button>
      </div>

      <div className="flex items-center justify-between gap-4 pt-6 border-t border-border-subtle">
        <div>
          <p className="text-text-primary">{t('settings.appearance.language.title')}</p>
          <p className="text-text-muted text-sm">
            {t('settings.appearance.language.description')}
          </p>
        </div>
        <div className="relative min-w-[180px]">
          <Languages size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
          <select
            value={locale}
            onChange={(event) => {
              const nextLocale = event.target.value as Locale;
              const language = availableLocales.find((option) => option.code === nextLocale)?.nativeName || nextLocale;
              setLocale(nextLocale);
              toast.success(translate(nextLocale, 'settings.appearance.language.changed', { language }));
            }}
            className="w-full rounded-lg border border-border-default bg-bg-elevated py-2 pl-9 pr-3 text-text-primary transition-colors focus:border-primary focus:outline-none"
            aria-label={t('settings.appearance.language.title')}
            data-testid="language-select"
          >
            {availableLocales.map((option) => (
              <option key={option.code} value={option.code}>
                {option.nativeName}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Background Scheme */}
      <div className="pt-6 border-t border-border-subtle">
        <div className="mb-3">
          <p className="text-text-primary">{t('settings.appearance.background.title')}</p>
          <p className="text-text-muted text-sm">
            {t('settings.appearance.background.description')}
          </p>
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {backgroundOptions.map((option) => {
            const isSelected = backgroundScheme === option.id;
            return (
              <button
                key={option.id}
                type="button"
                onClick={() => setBackground(option.id, t(option.labelKey))}
                className={`flex items-center gap-3 rounded-lg border p-3 text-left transition-all
                  ${isSelected
                    ? 'border-primary bg-primary/10'
                    : 'border-border-default bg-bg-elevated hover:border-border-default hover:bg-bg-hover'
                  }`}
                aria-pressed={isSelected}
                data-testid={`background-scheme-${option.id}`}
              >
                <span className="flex h-8 w-8 shrink-0 overflow-hidden rounded-full border border-border-subtle">
                  {option.colors.map((color) => (
                    <span key={color} className="flex-1" style={{ backgroundColor: color }} />
                  ))}
                </span>
                <span className={`min-w-0 flex-1 text-sm font-medium ${isSelected ? 'text-primary' : 'text-text-primary'}`}>
                  {t(option.labelKey)}
                </span>
                {isSelected && <Check size={16} className="shrink-0 text-primary" />}
              </button>
            );
          })}
        </div>
      </div>

      {/* Default View Mode */}
      <div className="pt-6 border-t border-border-subtle">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-text-primary">{t('settings.appearance.view.title')}</p>
            <p className="text-text-muted text-sm">
              {t('settings.appearance.view.description')}
            </p>
          </div>
          <div className="inline-flex w-fit items-center gap-1 rounded-lg bg-bg-elevated p-1">
            {viewOptions.map(({ value, labelKey, icon: Icon }) => (
              <button
                key={value}
                type="button"
                onClick={() => {
                  setViewMode(value);
                  toast.success(t('settings.appearance.view.changed', { label: t(labelKey) }));
                }}
                className={`inline-flex items-center gap-2 rounded-md px-3 py-1.5 text-sm transition-colors
                  ${viewMode === value
                    ? 'bg-primary text-white'
                    : 'text-text-secondary hover:bg-bg-hover hover:text-text-primary'
                  }`}
                aria-pressed={viewMode === value}
              >
                <Icon size={16} />
                {t(labelKey)}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Color Theme */}
      <div className="pt-6 border-t border-border-subtle">
        <div className="mb-3">
          <p className="text-text-primary">{t('settings.appearance.accent.title')}</p>
          <p className="text-text-muted text-sm">
            {t('settings.appearance.accent.description')}
          </p>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {accentOptions.map((themeOption) => {
            const isSelected = accentColor === themeOption.id;
            return (
              <button
                key={themeOption.id}
                type="button"
                onClick={() => setAccent(themeOption.id, t(themeOption.labelKey))}
                className={`
                  flex items-center gap-3 p-3 rounded-lg border
                  transition-all duration-200
                  ${isSelected
                    ? 'border-primary bg-primary/10'
                    : 'border-border-default hover:border-border-hover hover:bg-bg-elevated'
                  }
                `}
                aria-pressed={isSelected}
                data-testid={`accent-color-${themeOption.id}`}
              >
                <div
                  className="w-8 h-8 rounded-full flex-shrink-0"
                  style={{ backgroundColor: themeOption.color }}
                />
                <div className="text-left flex-1">
                  <div className={`font-medium ${isSelected ? 'text-primary' : 'text-text-primary'}`}>
                    {t(themeOption.labelKey)}
                  </div>
                </div>
                {isSelected && (
                  <Check size={18} className="text-primary flex-shrink-0" />
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Geometry Controls */}
      <div className="pt-6 border-t border-border-subtle">
        <div className="space-y-6">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <p className="text-text-primary">{t('settings.appearance.geometry.cornerRadius')}</p>
              <p className="text-text-muted text-sm">
                {t('settings.appearance.geometry.cornerRadiusDescription')}
              </p>
            </div>
            <div className="flex min-w-[220px] items-center gap-4">
              <input
                type="range"
                min={4}
                max={24}
                step={1}
                value={cornerRadius}
                onChange={(event) => updateCornerRadius(Number(event.target.value))}
                className="prism-slider flex-1"
                aria-label={t('settings.appearance.geometry.cornerRadius')}
                data-testid="corner-radius-slider"
              />
              <span className="w-12 text-right text-sm tabular-nums text-text-primary">{cornerRadius}px</span>
            </div>
          </div>

          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <p className="text-text-primary">{t('settings.appearance.geometry.sidebarWidth')}</p>
              <p className="text-text-muted text-sm">
                {t('settings.appearance.geometry.sidebarWidthDescription')}
              </p>
            </div>
            <div className="flex min-w-[220px] items-center gap-4">
              <input
                type="range"
                min={SIDEBAR_WIDTH_MIN}
                max={SIDEBAR_WIDTH_MAX}
                step={4}
                value={sidebarWidth}
                onChange={(event) => updateSidebarWidth(Number(event.target.value))}
                className="prism-slider flex-1"
                aria-label={t('settings.appearance.geometry.sidebarWidth')}
                data-testid="sidebar-width-slider"
              />
              <span className="w-14 text-right text-sm tabular-nums text-text-primary">{sidebarWidth}px</span>
            </div>
          </div>
        </div>
      </div>

      {/* Card Open Mode */}
      <div className="pt-6 border-t border-border-subtle">
        <div className="mb-3">
            <p className="text-text-primary">{t('settings.appearance.cardOpenMode.title')}</p>
            <p className="text-text-muted text-sm">
              {t('settings.appearance.cardOpenMode.description')}
            </p>
        </div>
        <select
          value={cardOpenMode}
          onChange={(e) => {
            const nextMode = e.target.value === 'edit' ? 'edit' : 'preview';
            setCardOpenMode(nextMode);
            localStorage.setItem('cardOpenMode', nextMode);
            const modeKey = nextMode === 'preview'
              ? 'settings.appearance.cardOpenMode.previewLabel'
              : 'settings.appearance.cardOpenMode.editLabel';
            toast.success(t('settings.appearance.cardOpenMode.changed', { mode: t(modeKey) }));
          }}
          className="w-full px-4 py-2 rounded-lg
                     bg-bg-elevated border border-border-default
                     text-text-primary
                     focus:outline-none focus:border-primary
                     transition-colors"
        >
          <option value="preview">{t('settings.appearance.cardOpenMode.preview')}</option>
          <option value="edit">{t('settings.appearance.cardOpenMode.edit')}</option>
        </select>
      </div>

      {/* Image Save Mode */}
      <div className="pt-6 border-t border-border-subtle">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-text-primary">{t('settings.appearance.imageSaveMode.title')}</p>
            <p className="text-text-muted text-sm">
              {t('settings.appearance.imageSaveMode.description')}
            </p>
          </div>
          <select
            value={localStorage.getItem('imageSaveMode') || 'both'}
            onChange={(e) => {
              localStorage.setItem('imageSaveMode', e.target.value);
              const modeKey = e.target.value === 'both'
                ? 'settings.appearance.imageSaveMode.bothLabel'
                : 'settings.appearance.imageSaveMode.thumbnailOnlyLabel';
              toast.success(t('settings.appearance.imageSaveMode.changed', { mode: t(modeKey) }));
            }}
            className="px-4 py-2 rounded-lg
                       bg-bg-elevated border border-border-default
                       text-text-primary
                       focus:outline-none focus:border-primary
                       transition-colors"
          >
            <option value="both">{t('settings.appearance.imageSaveMode.both')}</option>
            <option value="thumbnail_only">{t('settings.appearance.imageSaveMode.thumbnailOnly')}</option>
          </select>
        </div>
      </div>

      {/* Quick Add Default Category */}
      <div className="pt-6 border-t border-border-subtle">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-text-primary">{t('settings.appearance.quickAdd.title')}</p>
            <p className="text-text-muted text-sm">
              {t('settings.appearance.quickAdd.description')}
            </p>
          </div>
          <select
            value={localStorage.getItem('quickAddDefaultCategory') || ''}
            onChange={(e) => {
              localStorage.setItem('quickAddDefaultCategory', e.target.value);
              const selectedCategory = categories.find(c => c.id === Number(e.target.value));
              const categoryName = getCategoryDisplayName(
                selectedCategory,
                t,
                t('settings.appearance.quickAdd.uncategorized'),
              );
              toast.success(t('settings.appearance.quickAdd.changed', { category: categoryName }));
            }}
            className="px-4 py-2 rounded-lg
                       bg-bg-elevated border border-border-default
                       text-text-primary
                       focus:outline-none focus:border-primary
                       transition-colors"
          >
            <option value="">{t('settings.appearance.quickAdd.empty')}</option>
            {categories.map((cat) => (
              <option key={cat.id} value={cat.id}>
                {getCategoryOptionLabel(cat, t)}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Auto Load More */}
      <div className="pt-6 border-t border-border-subtle">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-text-primary">{t('settings.appearance.autoLoadMore.title')}</p>
            <p className="text-text-muted text-sm">
              {t('settings.appearance.autoLoadMore.description')}
            </p>
          </div>
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={autoLoadMore}
              onChange={(e) => {
                const newValue = e.target.checked;
                setAutoLoadMore(newValue);
                localStorage.setItem('autoLoadMore', String(newValue));
                toast.success(t(newValue ? 'settings.appearance.autoLoadMore.enabled' : 'settings.appearance.autoLoadMore.disabled'));
              }}
              className="sr-only peer"
            />
            <div className="w-11 h-6 bg-bg-hover rounded-full peer 
                            peer-checked:bg-primary
                            peer-focus:ring-2 peer-focus:ring-primary/50
                            after:content-[''] after:absolute after:top-0.5 after:left-0.5
                            after:bg-white after:rounded-full after:h-5 after:w-5
                            after:transition-all peer-checked:after:translate-x-5">
            </div>
          </label>
        </div>
      </div>
    </div>
  );
}
