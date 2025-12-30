
import React, { useState } from 'react';
import { Sun, Moon, Check } from 'lucide-react';
import { Button, toast } from '../ui';
import { Category } from '../../services/api';

interface AppearanceSectionProps {
  categories: Category[];
}

export function AppearanceSection({ categories }: AppearanceSectionProps) {
  const [theme, setTheme] = useState<'dark' | 'light'>(() => {
    return (localStorage.getItem('theme') as 'dark' | 'light') || 'dark';
  });

  const [autoLoadMore, setAutoLoadMore] = useState(() => localStorage.getItem('autoLoadMore') === 'true');

  // Toggle theme
  const toggleTheme = () => {
    const newTheme = theme === 'dark' ? 'light' : 'dark';
    setTheme(newTheme);
    localStorage.setItem('theme', newTheme);
    document.documentElement.classList.toggle('light', newTheme === 'light');
    toast.success(`已切換至${newTheme === 'dark' ? '深色' : '淺色'}主題`);
  };

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

      {/* Color Theme */}
      <div className="pt-6 border-t border-border-subtle">
        <div className="mb-3">
          <p className="text-text-primary">主題色彩</p>
          <p className="text-text-muted text-sm">
            選擇你喜歡的配色方案
          </p>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {[
            { id: 'default', name: '專業藍', color: '#3b82f6' },
            { id: 'cyberpunk', name: '賽博龐克', color: '#e879f9' },
            { id: 'eye-care', name: '護眼綠', color: '#34d399' },
            { id: 'elegant', name: '典雅金', color: '#d4a574' },
            { id: 'ocean', name: '海洋青', color: '#14b8a6' },
            { id: 'sunset', name: '夕陽橙', color: '#f97316' },
          ].map((themeOption) => {
            const isSelected = document.documentElement.getAttribute('data-theme') === themeOption.id;
            return (
              <button
                key={themeOption.id}
                onClick={() => {
                  document.documentElement.setAttribute('data-theme', themeOption.id);
                  localStorage.setItem('colorTheme', themeOption.id);
                  toast.success(`已切換至「${themeOption.name}」主題`);
                }}
                className={`
                  flex items-center gap-3 p-3 rounded-lg border
                  transition-all duration-200
                  ${isSelected
                    ? 'border-primary bg-primary/10'
                    : 'border-border-default hover:border-border-hover hover:bg-bg-elevated'
                  }
                `}
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
