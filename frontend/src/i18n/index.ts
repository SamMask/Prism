/**
 * Prism V2 - i18n (多語系) 預留架構
 * 
 * 使用方式:
 * import { t, setLocale, getLocale } from '../i18n'
 * 
 * 範例:
 * <button>{t('common.save')}</button>
 */

export type Locale = 'zh-TW' | 'en';

// 預設語系
let currentLocale: Locale = 'zh-TW';

// 翻譯字典類型
type TranslationDict = {
  [key: string]: string | TranslationDict;
};

// 繁體中文
const zhTW: TranslationDict = {
  common: {
    save: '儲存',
    cancel: '取消',
    delete: '刪除',
    edit: '編輯',
    add: '新增',
    search: '搜尋',
    loading: '載入中...',
    success: '成功',
    error: '錯誤',
    confirm: '確認',
    close: '關閉',
    back: '返回',
  },
  note: {
    title: '標題',
    content: '內容',
    category: '分類',
    tags: '標籤',
    createNote: '新增筆記',
    editNote: '編輯筆記',
    deleteConfirm: '確定要刪除此筆記嗎？此操作無法復原。',
    noTitle: '無標題',
    wordCount: '{count}字',
  },
  settings: {
    title: '設定',
    theme: '主題模式',
    darkMode: '深色模式',
    lightMode: '淺色模式',
    language: '語言',
    aiStatus: 'AI 服務狀態',
    searchStatus: '語意搜尋狀態',
    export: '匯出備份',
    exportJSON: '匯出 JSON',
    exportDB: '匯出資料庫',
    dangerZone: '危險區域',
    cleanupImages: '清理未使用的圖片',
    statistics: '統計資訊',
    about: '關於',
  },
  ai: {
    analyze: 'AI 分析',
    analyzing: '分析中...',
    suggestions: 'AI 建議標籤',
    addTag: '加入標籤',
    batchTagging: '批次 AI 分析',
    modelSelection: '模型選擇',
    visionModel: '視覺模型',
    textModel: '文字模型',
  },
  history: {
    title: '歷史版本',
    restore: '還原',
    restoreConfirm: '確定要還原到此版本嗎？目前的內容會被覆蓋。',
    noHistory: '沒有歷史版本記錄',
    contentChanged: '內容變更',
  },
  pin: {
    pin: '置頂',
    unpin: '取消置頂',
    pinned: '已置頂',
    unpinned: '已取消置頂',
  },
};

// 英文
const en: TranslationDict = {
  common: {
    save: 'Save',
    cancel: 'Cancel',
    delete: 'Delete',
    edit: 'Edit',
    add: 'Add',
    search: 'Search',
    loading: 'Loading...',
    success: 'Success',
    error: 'Error',
    confirm: 'Confirm',
    close: 'Close',
    back: 'Back',
  },
  note: {
    title: 'Title',
    content: 'Content',
    category: 'Category',
    tags: 'Tags',
    createNote: 'New Note',
    editNote: 'Edit Note',
    deleteConfirm: 'Are you sure you want to delete this note? This action cannot be undone.',
    noTitle: 'Untitled',
    wordCount: '{count} words',
  },
  settings: {
    title: 'Settings',
    theme: 'Theme',
    darkMode: 'Dark Mode',
    lightMode: 'Light Mode',
    language: 'Language',
    aiStatus: 'AI Service Status',
    searchStatus: 'Semantic Search Status',
    export: 'Export & Backup',
    exportJSON: 'Export JSON',
    exportDB: 'Export Database',
    dangerZone: 'Danger Zone',
    cleanupImages: 'Clean Unused Images',
    statistics: 'Statistics',
    about: 'About',
  },
  ai: {
    analyze: 'AI Analyze',
    analyzing: 'Analyzing...',
    suggestions: 'AI Suggested Tags',
    addTag: 'Add Tag',
    batchTagging: 'Batch AI Tagging',
    modelSelection: 'Model Selection',
    visionModel: 'Vision Model',
    textModel: 'Text Model',
  },
  history: {
    title: 'History',
    restore: 'Restore',
    restoreConfirm: 'Are you sure you want to restore to this version? Current content will be overwritten.',
    noHistory: 'No history records',
    contentChanged: 'Content changed',
  },
  pin: {
    pin: 'Pin',
    unpin: 'Unpin',
    pinned: 'Pinned',
    unpinned: 'Unpinned',
  },
};

// 語系字典
const translations: Record<Locale, TranslationDict> = {
  'zh-TW': zhTW,
  'en': en,
};

/**
 * 取得翻譯字串
 * @param key - 翻譯鍵值，例如 'common.save'
 * @param params - 可選的參數替換，例如 { count: 100 }
 */
export function t(key: string, params?: Record<string, string | number>): string {
  const keys = key.split('.');
  let result: string | TranslationDict = translations[currentLocale];
  
  for (const k of keys) {
    if (typeof result === 'object' && k in result) {
      result = result[k];
    } else {
      // 找不到翻譯，返回鍵值
      console.warn(`[i18n] Missing translation: ${key}`);
      return key;
    }
  }
  
  if (typeof result !== 'string') {
    console.warn(`[i18n] Invalid translation key: ${key}`);
    return key;
  }
  
  // 參數替換
  if (params) {
    return result.replace(/\{(\w+)\}/g, (_, name) => {
      return params[name]?.toString() || '';
    });
  }
  
  return result;
}

/**
 * 設定目前語系
 */
export function setLocale(locale: Locale): void {
  currentLocale = locale;
  localStorage.setItem('locale', locale);
}

/**
 * 取得目前語系
 */
export function getLocale(): Locale {
  return currentLocale;
}

/**
 * 從 localStorage 初始化語系
 */
export function initLocale(): void {
  const saved = localStorage.getItem('locale') as Locale;
  if (saved && translations[saved]) {
    currentLocale = saved;
  }
}

// 自動初始化
initLocale();

// 導出可用語系
export const availableLocales: { code: Locale; name: string }[] = [
  { code: 'zh-TW', name: '繁體中文' },
  { code: 'en', name: 'English' },
];
