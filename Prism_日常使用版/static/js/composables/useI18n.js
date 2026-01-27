/**
 * useI18n.js - 國際化 (i18n) Composable
 * Local Insight v0.8.9
 * 
 * 功能：
 * - 載入語系檔
 * - 提供 t() 翻譯函數
 * - 支援語言切換
 * - 自動保存語言偏好到 localStorage
 * - v0.8.9: 支援 provide/inject 模式，不再需要逐層傳遞 t()
 */

const { ref, computed, watch, inject, provide } = Vue;

// i18n injection key (Symbol 確保唯一性)
export const i18nKey = Symbol('i18n');

// 可用語系列表
const AVAILABLE_LOCALES = ['zh-TW', 'en'];
const DEFAULT_LOCALE = 'zh-TW';
const STORAGE_KEY = 'local-insight-locale';

// 全域語系資料 (shared across all components)
const currentLocale = ref(localStorage.getItem(STORAGE_KEY) || DEFAULT_LOCALE);
const messages = ref({});
const isLoading = ref(false);

// 載入語系檔
const loadLocale = async (locale) => {
    if (!AVAILABLE_LOCALES.includes(locale)) {
        console.warn(`[i18n] Locale "${locale}" not supported, falling back to ${DEFAULT_LOCALE}`);
        locale = DEFAULT_LOCALE;
    }
    
    isLoading.value = true;
    
    try {
        const response = await fetch(`/static/locales/${locale}.json?v=${Date.now()}`);
        if (!response.ok) {
            throw new Error(`Failed to load locale: ${locale}`);
        }
        
        const data = await response.json();
        messages.value = data;
        currentLocale.value = locale;
        localStorage.setItem(STORAGE_KEY, locale);
        
        // 更新 HTML lang 屬性
        document.documentElement.lang = locale;
        
        console.log(`[i18n] Loaded locale: ${locale}`);
    } catch (error) {
        console.error('[i18n] Load error:', error);
        // 如果載入失敗且不是預設語系，嘗試載入預設
        if (locale !== DEFAULT_LOCALE) {
            await loadLocale(DEFAULT_LOCALE);
        }
    } finally {
        isLoading.value = false;
    }
};

// 翻譯函數 - 支援嵌套鍵值 (e.g., "editor.title")
const t = (key, fallback = null) => {
    if (!key) return fallback || '';
    
    const keys = key.split('.');
    let value = messages.value;
    
    for (const k of keys) {
        if (value && typeof value === 'object' && k in value) {
            value = value[k];
        } else {
            // 找不到翻譯，返回 fallback 或 key
            return fallback !== null ? fallback : key;
        }
    }
    
    return typeof value === 'string' ? value : (fallback !== null ? fallback : key);
};

// 切換語言
const setLocale = async (locale) => {
    if (locale === currentLocale.value) return;
    await loadLocale(locale);
};

// 取得語系名稱
const getLocaleName = (locale) => {
    const names = {
        'zh-TW': '繁體中文',
        'en': 'English'
    };
    return names[locale] || locale;
};

export function useI18n() {
    // 初始化時載入語系
    if (Object.keys(messages.value).length === 0) {
        loadLocale(currentLocale.value);
    }
    
    return {
        // State
        currentLocale,
        messages,
        isLoading,
        availableLocales: AVAILABLE_LOCALES,
        
        // Methods
        t,
        setLocale,
        loadLocale,
        getLocaleName,
    };
}

/**
 * 在根組件中 provide i18n (v0.8.9)
 * 使用方式: 在 app setup() 中調用 provideI18n()
 */
export function provideI18n() {
    const i18n = useI18n();
    provide(i18nKey, i18n);
    return i18n;
}

/**
 * 在子 composable 或組件中 inject t() 函數 (v0.8.9)
 * 使用方式: const t = injectT();
 * 
 * @returns {Function} t() 翻譯函數
 */
export function injectT() {
    const i18n = inject(i18nKey, null);
    if (i18n) {
        return i18n.t;
    }
    // Fallback: 如果沒有被 provide，返回預設函數
    console.warn('[i18n] No i18n context found, using fallback');
    return (key, fallback = null) => fallback !== null ? fallback : key;
}

/**
 * 在子 composable 或組件中 inject 完整 i18n (v0.8.9)
 * 使用方式: const { t, currentLocale, setLocale } = injectI18n();
 */
export function injectI18n() {
    const i18n = inject(i18nKey, null);
    if (i18n) {
        return i18n;
    }
    // Fallback
    console.warn('[i18n] No i18n context found, using fallback');
    return {
        t: (key, fallback = null) => fallback !== null ? fallback : key,
        currentLocale: ref('zh-TW'),
        setLocale: () => {},
        isLoading: ref(false),
        availableLocales: AVAILABLE_LOCALES,
        getLocaleName: (locale) => locale
    };
}
