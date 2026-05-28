
import { useState } from 'react';
import { Sun, Moon, Check, LayoutGrid, List, AlignJustify } from 'lucide-react';
import { Button, toast } from '../ui';
import { Category } from '../../services/api';
import { useAppStore, type ViewMode } from '../../stores/appStore';

interface AppearanceSectionProps {
  categories: Category[];
}

type AccentColor = 'default' | 'cyberpunk' | 'eye-care' | 'elegant' | 'ocean' | 'sunset';
type BackgroundScheme = 'neutral' | 'black' | 'warm' | 'green' | 'paper';

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

const accentOptions: Array<{ id: AccentColor; name: string; color: string }> = [
  { id: 'default', name: '專業藍', color: '#3b82f6' },
  { id: 'cyberpunk', name: '賽博龐克', color: '#e879f9' },
  { id: 'eye-care', name: '護眼綠', color: '#34d399' },
  { id: 'elegant', name: '典雅金', color: '#d4a574' },
  { id: 'ocean', name: '海洋青', color: '#14b8a6' },
  { id: 'sunset', name: '夕陽橙', color: '#f97316' },
];

const backgroundOptions: Array<{ id: BackgroundScheme; name: string; colors: [string, string, string] }> = [
  { id: 'neutral', name: '預設藍灰', colors: ['#0b1020', '#141a2a', '#263247'] },
  { id: 'black', name: '純黑', colors: ['#000000', '#080808', '#1a1a1a'] },
  { id: 'warm', name: '暖灰', colors: ['#17130f', '#211c17', '#3a3128'] },
  { id: 'green', name: '護眼灰綠', colors: ['#0d1511', '#14201a', '#2a3a31'] },
  { id: 'paper', name: '紙張米色', colors: ['#f4ecd9', '#fbf5e4', '#d4c8a4'] },
];

export function AppearanceSection({ categories }: AppearanceSectionProps) {
  const { viewMode, setViewMode } = useAppStore();
  const [theme, setTheme] = useState<'dark' | 'light'>(() => {
    return (localStorage.getItem('theme') as 'dark' | 'light') || 'dark';
  });
  const [accentColor, setAccentColor] = useState<AccentColor>(() => {
    const savedAccent =
      (localStorage.getItem('prism.accentColor') || localStorage.getItem('colorTheme')) as AccentColor | null;
    return savedAccent && accentOptions.some((option) => option.id === savedAccent) ? savedAccent : 'default';
  });
  const [backgroundScheme, setBackgroundScheme] = useState<BackgroundScheme>(() => {
    const savedScheme = localStorage.getItem('prism.backgroundScheme') as BackgroundScheme | null;
    return savedScheme && backgroundOptions.some((option) => option.id === savedScheme) ? savedScheme : 'neutral';
  });
  const [cornerRadius, setCornerRadius] = useState(() => readNumberSetting('prism.cornerRadius', 10, 4, 24));
  const [sidebarWidth, setSidebarWidth] = useState(() => readNumberSetting('prism.sidebarWidth', 248, 208, 320));

  const [autoLoadMore, setAutoLoadMore] = useState(() => localStorage.getItem('autoLoadMore') === 'true');

  // Toggle theme
  const toggleTheme = () => {
    const newTheme = theme === 'dark' ? 'light' : 'dark';
    setTheme(newTheme);
    localStorage.setItem('theme', newTheme);
    document.documentElement.classList.toggle('light', newTheme === 'light');
    document.documentElement.setAttribute('data-mode', newTheme);
    toast.success(`已切換至${newTheme === 'dark' ? '深色' : '淺色'}主題`);
  };

  const setAccent = (color: AccentColor, label: string) => {
    setAccentColor(color);
    localStorage.setItem('prism.accentColor', color);
    localStorage.setItem('colorTheme', color);
    document.documentElement.setAttribute('data-accent', color);
    toast.success(`已切換至「${label}」強調色`);
  };

  const setBackground = (scheme: BackgroundScheme, label: string) => {
    setBackgroundScheme(scheme);
    localStorage.setItem('prism.backgroundScheme', scheme);
    document.documentElement.setAttribute('data-bg', scheme);
    toast.success(`已切換至「${label}」背景色調`);
  };

  const updateCornerRadius = (value: number) => {
    const nextValue = clampNumber(value, 4, 24);
    setCornerRadius(nextValue);
    localStorage.setItem('prism.cornerRadius', String(nextValue));
    setRootPixelVariable('--prism-corner-radius', nextValue);
  };

  const updateSidebarWidth = (value: number) => {
    const nextValue = clampNumber(value, 208, 320);
    setSidebarWidth(nextValue);
    localStorage.setItem('prism.sidebarWidth', String(nextValue));
    setRootPixelVariable('--prism-sidebar-width', nextValue);
    setRootPixelVariable('--sidebar-w', nextValue);
  };

  const viewOptions: Array<{ value: ViewMode; label: string; icon: typeof LayoutGrid }> = [
    { value: 'grid', label: '網格', icon: LayoutGrid },
    { value: 'list', label: '列表', icon: List },
    { value: 'compact', label: '精簡', icon: AlignJustify },
  ];

  return (
    <div className="glass rounded-xl p-6">
      <h2 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
        <Sun size={20} className="text-primary" />
        外觀
      </h2>
      
      {/* Dark/Light Mode */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <p className="text-text-primary">主題模式</p>
          <p className="text-text-muted text-sm">
            選擇深色或淺色主題
          </p>
        </div>
        <Button
          onClick={toggleTheme}
          variant="secondary"
          className="flex items-center gap-2"
        >
          {theme === 'dark' ? <Moon size={18} /> : <Sun size={18} />}
          {theme === 'dark' ? '深色' : '淺色'}
        </Button>
      </div>

      {/* Background Scheme */}
      <div className="pt-6 border-t border-border-subtle">
        <div className="mb-3">
          <p className="text-text-primary">背景色調</p>
          <p className="text-text-muted text-sm">
            調整底色、卡片層次與邊框色階
          </p>
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {backgroundOptions.map((option) => {
            const isSelected = backgroundScheme === option.id;
            return (
              <button
                key={option.id}
                type="button"
                onClick={() => setBackground(option.id, option.name)}
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
                  {option.name}
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
            <p className="text-text-primary">筆記顯示模式</p>
            <p className="text-text-muted text-sm">
              設定 Home 筆記列表的預設密度
            </p>
          </div>
          <div className="inline-flex w-fit items-center gap-1 rounded-lg bg-bg-elevated p-1">
            {viewOptions.map(({ value, label, icon: Icon }) => (
              <button
                key={value}
                type="button"
                onClick={() => {
                  setViewMode(value);
                  toast.success(`已切換為「${label}」顯示`);
                }}
                className={`inline-flex items-center gap-2 rounded-md px-3 py-1.5 text-sm transition-colors
                  ${viewMode === value
                    ? 'bg-primary text-white'
                    : 'text-text-secondary hover:bg-bg-hover hover:text-text-primary'
                  }`}
                aria-pressed={viewMode === value}
              >
                <Icon size={16} />
                {label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Color Theme */}
      <div className="pt-6 border-t border-border-subtle">
        <div className="mb-3">
          <p className="text-text-primary">強調色</p>
          <p className="text-text-muted text-sm">
            只影響按鈕、焦點、標籤與啟用狀態
          </p>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {accentOptions.map((themeOption) => {
            const isSelected = accentColor === themeOption.id;
            return (
              <button
                key={themeOption.id}
                type="button"
                onClick={() => setAccent(themeOption.id, themeOption.name)}
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
                    {themeOption.name}
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
              <p className="text-text-primary">邊角圓潤度</p>
              <p className="text-text-muted text-sm">
                影響卡片、按鈕、輸入框等所有圓角
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
                aria-label="邊角圓潤度"
                data-testid="corner-radius-slider"
              />
              <span className="w-12 text-right text-sm tabular-nums text-text-primary">{cornerRadius}px</span>
            </div>
          </div>

          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <p className="text-text-primary">側邊欄寬度</p>
              <p className="text-text-muted text-sm">
                調整桌面版側邊欄與筆記區的空間比例
              </p>
            </div>
            <div className="flex min-w-[220px] items-center gap-4">
              <input
                type="range"
                min={208}
                max={320}
                step={4}
                value={sidebarWidth}
                onChange={(event) => updateSidebarWidth(Number(event.target.value))}
                className="prism-slider flex-1"
                aria-label="側邊欄寬度"
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
          <p className="text-text-primary">卡片開啟模式</p>
          <p className="text-text-muted text-sm">
            選擇點擊卡片時的預設開啟模式
          </p>
        </div>
        <select
          value={localStorage.getItem('cardOpenMode') || 'reading'}
          onChange={(e) => {
            localStorage.setItem('cardOpenMode', e.target.value);
            const modeName = e.target.value === 'preview' ? '預覽' : e.target.value === 'reading' ? '閱讀' : '編輯';
            toast.success(`已設定為「${modeName}」模式`);
          }}
          className="w-full px-4 py-2 rounded-lg
                     bg-bg-elevated border border-border-default
                     text-text-primary
                     focus:outline-none focus:border-primary
                     transition-colors"
        >
          <option value="preview">預覽模式 (Preview) - 快速瀏覽內容</option>
          <option value="reading">閱讀模式 (Reading) - 沉浸式閱讀</option>
          <option value="edit">編輯模式 (Edit) - 直接編輯</option>
        </select>
      </div>

      {/* Image Save Mode */}
      <div className="pt-6 border-t border-border-subtle">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-text-primary">圖片保存模式</p>
            <p className="text-text-muted text-sm">
              選擇上傳圖片時保存原圖或僅縮圖（節省空間）
            </p>
          </div>
          <select
            value={localStorage.getItem('imageSaveMode') || 'both'}
            onChange={(e) => {
              localStorage.setItem('imageSaveMode', e.target.value);
              const modeName = e.target.value === 'both' ? '原圖+縮圖' : '僅縮圖';
              toast.success(`已設定為「${modeName}」模式`);
            }}
            className="px-4 py-2 rounded-lg
                       bg-bg-elevated border border-border-default
                       text-text-primary
                       focus:outline-none focus:border-primary
                       transition-colors"
          >
            <option value="both">原圖+縮圖 (Both) - 保留完整品質</option>
            <option value="thumbnail_only">僅縮圖 (Thumbnail Only) - 節省儲存空間</option>
          </select>
        </div>
      </div>

      {/* Quick Add Default Category */}
      <div className="pt-6 border-t border-border-subtle">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-text-primary">快速新增預設分類</p>
            <p className="text-text-muted text-sm">
              Header 新增按鈕預設選擇的分類
            </p>
          </div>
          <select
            value={localStorage.getItem('quickAddDefaultCategory') || ''}
            onChange={(e) => {
              localStorage.setItem('quickAddDefaultCategory', e.target.value);
              const categoryName = categories.find(c => c.id === Number(e.target.value))?.name || '無分類';
              toast.success(`快速新增預設分類設定為「${categoryName}」`);
            }}
            className="px-4 py-2 rounded-lg
                       bg-bg-elevated border border-border-default
                       text-text-primary
                       focus:outline-none focus:border-primary
                       transition-colors"
          >
            <option value="">無（每次選擇）</option>
            {categories.map((cat) => (
              <option key={cat.id} value={cat.id}>
                {cat.icon} {cat.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Auto Load More */}
      <div className="pt-6 border-t border-border-subtle">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-text-primary">自動載入更多</p>
            <p className="text-text-muted text-sm">
              滾動到底部時自動載入下一頁（無限滾動）
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
                toast.success(newValue ? '已開啟無限滾動' : '已關閉無限滾動');
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
