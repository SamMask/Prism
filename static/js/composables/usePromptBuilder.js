/**
 * usePromptBuilder.js - Prompt Builder Composable
 * Local Insight v1.0
 *
 * 功能：
 * - 管理 Prompt Builder 的所有狀態和邏輯
 * - 提供 i18n 翻譯功能
 * - 處理表單、選項、模板、Wizard 等功能
 * - 支援 narrativeOutput 智能造句
 * - 支援 copyMetaPrompt LLM 優化指令
 */

const { ref, computed, onMounted, onUnmounted, watch } = Vue;

// ==================== i18n System ====================
const currentLocale = ref(localStorage.getItem("localInsightLang") || "zh-TW");
const translations = ref({});
const i18nReady = ref(false);

// Load locale file
const loadLocale = async (locale) => {
  try {
    const response = await fetch(`/static/locales/${locale}.json`);
    if (response.ok) {
      translations.value = await response.json();
      i18nReady.value = true;
    }
  } catch (error) {
    console.error("[i18n] Failed to load locale:", error);
  }
};

// Translation function
const t = (key, fallback = "") => {
  if (!key) return fallback;
  const keys = key.split(".");
  let result = translations.value;
  for (const k of keys) {
    result = result?.[k];
    if (result === undefined) return fallback || key;
  }
  return result || fallback || key;
};

// Switch locale
const setLocale = async (locale) => {
  currentLocale.value = locale;
  localStorage.setItem("localInsightLang", locale);
  await loadLocale(locale);
};

// Available locales
const availableLocales = [
  { code: "zh-TW", name: "繁體中文" },
  { code: "en", name: "English" },
];

const getLocaleName = (code) => {
  return availableLocales.find((l) => l.code === code)?.name || code;
};

// ==================== Main Composable ====================
export function usePromptBuilder() {
  const langDropdownOpen = ref(false);

  // Loading State
  const configLoading = ref(true);
  const configError = ref(null);

  // Output Mode
  const outputMode = ref("text");
  const copySuccess = ref(false);
  const useWeights = ref(false);

  // Edit Prompt State
  const showEditPrompt = ref(false);
  const editedPrompt = ref("");

  // Form State
  const form = ref({
    description: "",
    shotSize: "",
    cameraMovement: "",
    angle: "",
    focus: "",
    style: "",
    lighting: "",
    colorPalette: "",
    quality: "",
    negativePrompt: "",
    // Technical
    aspectRatio: "",
    resolution: "",
    styleModifier: "",
  });

  // Weights State
  const weights = ref({
    shotSize: 1.0,
    cameraMovement: 1.0,
    angle: 1.0,
    focus: 1.0,
    style: 1.0,
    lighting: 1.0,
    colorPalette: 1.0,
    quality: 1.0,
  });

  // Options (從 JSON 載入)
  const options = ref({
    shotSize: [],
    cameraMovement: [],
    angle: [],
    focus: [],
    style: [],
    lighting: [],
    colorPalette: [],
    quality: [],
  });

  // Quick Templates (從 JSON 載入)
  const quickTemplates = ref([]);

  // Negative Prompt Presets
  const negativePresets = ref([]);

  // Technical Options (從 wizard_options.json 載入)
  const technicalOptions = ref({
    aspectRatio: [],
    resolution: [],
    styleModifiers: [],
  });

  // Wizard Options (從 wizard_options.json 載入)
  const wizardOptions = ref({
    subject: { placeholder: "", options: [] },
    action: { placeholder: "", options: [] },
    environment: { placeholder: "", options: [] },
    details: { placeholder: "", options: [] },
  });

  // Wizard Modal State
  const wizardModal = ref({
    visible: false,
    subject: "",
    action: "",
    environment: "",
    details: "",
    append: true,
  });

  // Wizard Edit Modal State
  const wizardEditModal = ref({
    visible: false,
    dimension: "subject",
    options: [],
    newOption: "",
  });

  // Chaos Level (v0.8.7)
  const chaosLevel = ref(2);

  // 檢查是否有自定義詞庫
  const hasCustomOptions = computed(() => {
    return false;
  });

  // Dimension Icons
  const dimensionIcons = {
    subject: "👤",
    action: "🎬",
    environment: "🌍",
    details: "✨",
  };

  const getDimensionLabel = (key) => {
    const labels = {
      subject: t("wizard.subjectShort", "主體"),
      action: t("wizard.actionShort", "動作"),
      environment: t("wizard.environmentShort", "環境"),
      details: t("wizard.detailsShort", "細節"),
    };
    return labels[key] || key;
  };

  const getDimensionIcon = (key) => dimensionIcons[key] || "📝";

  // Category Labels - locale-aware
  const getCategoryLabel = (key) => {
    const labels = {
      shotSize: t("camera.shotSize", "景別"),
      cameraMovement: t("camera.cameraMovement", "鏡頭運動"),
      angle: t("camera.angle", "拍攝角度"),
      focus: t("camera.focus", "對焦"),
      style: t("style.artStyle", "藝術風格"),
      lighting: t("style.lighting", "光線"),
      colorPalette: t("style.colorPalette", "色調"),
      quality: t("style.quality", "品質強調"),
    };
    return labels[key] || key;
  };

  // i18n Helper Functions
  const getOptKey = (opt) => {
    if (typeof opt === "string") return opt;
    if (opt && typeof opt === "object") {
      return opt.key || opt.output || JSON.stringify(opt);
    }
    return String(opt);
  };

  const getOptDisplay = (opt) => {
    if (typeof opt === "string") return opt;
    if (opt && typeof opt === "object") {
      if (currentLocale.value === "en") {
        return opt.displayEN || opt.output || opt.display || "";
      }
      return opt.display || opt.output || "";
    }
    return String(opt || "");
  };

  const getOptOutput = (opt) => {
    if (typeof opt === "string") return opt;
    if (opt && typeof opt === "object") {
      return opt.output || opt.display || "";
    }
    return String(opt || "");
  };

  // Edit Modal State
  const editModal = ref({
    visible: false,
    category: "",
    options: [],
    newDisplay: "",
    newOutput: "",
  });

  // Template Modal State
  const templateModal = ref({
    visible: false,
    name: "",
  });

  // ==================== API Functions ====================

  // Load Config from API
  const loadConfig = async () => {
    try {
      const response = await fetch("/api/prompt-options");
      if (!response.ok) throw new Error("Failed to load config");

      const result = await response.json();
      if (result.status !== "success") throw new Error(result.message);

      const config = result.data;

      if (config.categories) {
        options.value.shotSize = config.categories.shotSize?.options || [];
        options.value.cameraMovement =
          config.categories.cameraMovement?.options || [];
        options.value.angle = config.categories.angle?.options || [];
        options.value.focus = config.categories.focus?.options || [];
        options.value.style = config.categories.style?.options || [];
        options.value.lighting = config.categories.lighting?.options || [];
        options.value.colorPalette =
          config.categories.colorPalette?.options || [];
        options.value.quality = config.categories.quality?.options || [];
      }

      if (config.quickTemplates) {
        quickTemplates.value = config.quickTemplates;
      }

      if (config.negativePromptPresets) {
        negativePresets.value = config.negativePromptPresets;
      }

      configLoading.value = false;
    } catch (error) {
      console.error("Load config error:", error);
      configError.value = "無法載入配置檔";
      configLoading.value = false;
    }
  };

  // Load Wizard Options
  const loadWizardOptions = async () => {
    try {
      const response = await fetch("/static/config/wizard_options.json");
      if (!response.ok) throw new Error("Failed to load wizard options");

      const config = await response.json();

      if (config.technicalSpecs) {
        technicalOptions.value.aspectRatio =
          config.technicalSpecs.aspectRatio?.options || [];
        technicalOptions.value.resolution =
          config.technicalSpecs.resolution?.options || [];
        technicalOptions.value.styleModifiers =
          config.technicalSpecs.styleModifiers?.options || [];
      }

      if (config.dimensions) {
        wizardOptions.value.subject = config.dimensions.subject || {
          placeholder: "",
          options: [],
        };
        wizardOptions.value.action = config.dimensions.action || {
          placeholder: "",
          options: [],
        };
        wizardOptions.value.environment = config.dimensions.environment || {
          placeholder: "",
          options: [],
        };
        wizardOptions.value.details = config.dimensions.details || {
          placeholder: "",
          options: [],
        };
      }
    } catch (error) {
      console.error("Load wizard options error:", error);
    }
  };

  // ==================== Form Functions ====================

  // Apply Template
  const applyTemplate = (template) => {
    Object.assign(form.value, template.preset);
  };

  // Reset Form
  const resetForm = () => {
    form.value = {
      description: "",
      shotSize: "",
      cameraMovement: "",
      angle: "",
      focus: "",
      style: "",
      lighting: "",
      colorPalette: "",
      quality: "",
      negativePrompt: "",
    };
    Object.keys(weights.value).forEach((key) => {
      weights.value[key] = 1.0;
    });
  };

  // Format with weight
  const formatWithWeight = (value, key) => {
    if (!value) return "";
    if (!useWeights.value) return value;
    const w = weights.value[key];
    if (w === 1.0) return value;
    return `(${value}:${w.toFixed(1)})`;
  };

  // ==================== Output Computed ====================

  // Text Output
  const textOutput = computed(() => {
    const parts = [];

    if (form.value.description) parts.push(form.value.description);
    if (form.value.shotSize)
      parts.push(formatWithWeight(form.value.shotSize, "shotSize"));
    if (form.value.cameraMovement)
      parts.push(formatWithWeight(form.value.cameraMovement, "cameraMovement"));
    if (form.value.angle)
      parts.push(formatWithWeight(form.value.angle, "angle"));
    if (form.value.focus)
      parts.push(formatWithWeight(form.value.focus, "focus"));
    if (form.value.style)
      parts.push(formatWithWeight(form.value.style, "style"));
    if (form.value.lighting)
      parts.push(formatWithWeight(form.value.lighting, "lighting"));
    if (form.value.colorPalette)
      parts.push(formatWithWeight(form.value.colorPalette, "colorPalette"));
    if (form.value.quality)
      parts.push(formatWithWeight(form.value.quality, "quality"));
    if (form.value.aspectRatio) parts.push(form.value.aspectRatio);
    if (form.value.resolution) parts.push(form.value.resolution);
    if (form.value.styleModifier) parts.push(form.value.styleModifier);

    return parts.join(", ");
  });

  // v0.8.9: A vs An helper
  const getArticle = (word) => {
    if (!word) return "";
    const firstLetter = word.trim().charAt(0).toLowerCase();
    return ["a", "e", "i", "o", "u"].includes(firstLetter) ? "An" : "A";
  };

  // v0.8.9: Narrative Output
  const narrativeOutput = computed(() => {
    const f = form.value;
    let sentence = "";

    if (f.description) {
      sentence = f.description.trim();
    }

    if (sentence && !sentence.endsWith(".")) sentence += ".";

    if (f.style) {
      const article = getArticle(f.style);
      const isPhoto =
        f.style.toLowerCase().includes("photo") ||
        f.style.toLowerCase().includes("realistic");
      if (isPhoto) {
        sentence = `${article} ${f.style} photograph: ${sentence}`;
      } else {
        sentence = `${article} ${f.style} artwork. ${sentence}`;
      }
    }

    if (f.lighting) {
      sentence += ` Illuminated by ${f.lighting}.`;
    }

    if (f.colorPalette) {
      sentence += ` Rendered in ${f.colorPalette} tones.`;
    }

    const techParams = [];
    if (f.shotSize) techParams.push(f.shotSize);
    if (f.angle) techParams.push(`shot from a ${f.angle}`);
    if (f.cameraMovement) techParams.push(`with ${f.cameraMovement}`);
    if (f.focus) techParams.push(f.focus);

    if (techParams.length > 0) {
      sentence += ` Captured ${techParams.join(", ")}.`;
    }

    if (f.quality) {
      sentence += ` ${f.quality}.`;
    }

    if (f.aspectRatio) {
      const match = f.aspectRatio.match(/(\d+:\d+)/);
      if (match) {
        sentence += ` --ar ${match[1]}`;
      } else {
        sentence += ` --${f.aspectRatio}`;
      }
    }

    if (f.resolution) {
      sentence += ` --${f.resolution}`;
    }
    if (f.styleModifier) {
      sentence += ` --${f.styleModifier}`;
    }

    return sentence.trim();
  });

  // JSON Output
  const jsonOutput = computed(() => {
    const output = {};

    if (form.value.description) output.description = form.value.description;
    if (form.value.shotSize) {
      output.shot_size = useWeights.value
        ? { value: form.value.shotSize, weight: weights.value.shotSize }
        : form.value.shotSize;
    }
    if (form.value.cameraMovement) {
      output.camera_movement = useWeights.value
        ? {
            value: form.value.cameraMovement,
            weight: weights.value.cameraMovement,
          }
        : form.value.cameraMovement;
    }
    if (form.value.angle) {
      output.angle = useWeights.value
        ? { value: form.value.angle, weight: weights.value.angle }
        : form.value.angle;
    }
    if (form.value.focus) {
      output.focus = useWeights.value
        ? { value: form.value.focus, weight: weights.value.focus }
        : form.value.focus;
    }
    if (form.value.style) {
      output.style = useWeights.value
        ? { value: form.value.style, weight: weights.value.style }
        : form.value.style;
    }
    if (form.value.lighting) {
      output.lighting = useWeights.value
        ? { value: form.value.lighting, weight: weights.value.lighting }
        : form.value.lighting;
    }
    if (form.value.colorPalette) {
      output.color_palette = useWeights.value
        ? { value: form.value.colorPalette, weight: weights.value.colorPalette }
        : form.value.colorPalette;
    }
    if (form.value.quality) {
      output.quality = useWeights.value
        ? { value: form.value.quality, weight: weights.value.quality }
        : form.value.quality;
    }
    if (form.value.negativePrompt)
      output.negative_prompt = form.value.negativePrompt;

    return JSON.stringify(output, null, 2);
  });

  // ==================== Action Functions ====================

  // Copy Output
  const copyOutput = async () => {
    const text =
      outputMode.value === "text"
        ? textOutput.value +
          (form.value.negativePrompt
            ? `\n\nNegative: ${form.value.negativePrompt}`
            : "")
        : jsonOutput.value;

    try {
      await navigator.clipboard.writeText(text);
      copySuccess.value = true;
      setTimeout(() => {
        copySuccess.value = false;
      }, 2000);
    } catch (error) {
      alert(t("messages.copyFailed", "複製失敗，請手動選取複製"));
    }
  };

  // Download JSON
  const downloadJSON = () => {
    const blob = new Blob([jsonOutput.value], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    const timestamp = new Date()
      .toISOString()
      .replace(/[:.]/g, "-")
      .slice(0, 19);
    a.href = url;
    a.download = `prompt_${timestamp}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // v0.8.9: Copy Meta-Prompt (i18n support)
  const copyMetaPromptSuccess = ref(false);
  const copyMetaPrompt = async () => {
    const f = form.value;

    const data = {
      subject: f.description || "Subject to be defined",
      action: "",
      environment: "",
      style: f.style || "Photorealistic",
      lighting: f.lighting || "",
      details: "",
      camera: [f.shotSize, f.angle, f.focus].filter(Boolean).join(", "),
    };

    // English Meta Prompt
    const metaPromptEN = `[ Role ] You are an AI image generation expert (Prompt Engineer) proficient in various visual arts (from photography, CGI to traditional crafts). Your task is to rewrite the "keyword fragments" I provide into a flowing, detail-rich Midjourney/DALL-E prompt that follows the logic of that artistic style.

[ Input Data ]

- **Subject & Description**: ${data.subject}
- **Art Style/Medium**: ${data.style} <-- KEY! Prioritize analyzing this
- **Lighting Atmosphere**: ${data.lighting || "Not specified"}
- **Camera Technique**: ${data.camera || "Not specified"}

[ Processing Rules (Important) ]

1. **Material Awareness**:
   - For "Knitted" style: Emphasize yarn texture, weaving patterns, soft touch.
   - For "Claymation": Emphasize fingerprint marks, plasticine texture, stop-motion lighting.
   - For "Miniature": Emphasize tilt-shift effect, depth of field, macro details.
   - For other styles, use domain-specific descriptors.

2. **Narrative Structure**: Don't just stack words. Use a complete descriptive sentence (e.g., "A huge knitted monster stands..." instead of "Knitted, monster, standing").

3. **Output Format**: Directly output the optimized English prompt (Prompt Only), no explanation needed.

[ Start Generation ]`;

    // Chinese Meta Prompt
    const metaPromptZH = `[ 角色設定 ] 你是一位精通各類視覺藝術（從攝影、CGI 到傳統工藝）的 AI 圖像生成專家 (Prompt Engineer)。你的任務是將我提供的「關鍵字片段」重寫為一段流暢、細節豐富且符合該藝術風格邏輯的 Midjourney/DALL-E 提示詞。

[ 輸入數據 ]

- **主體與描述**: ${data.subject}
- **藝術風格/媒材**: ${data.style} <-- 關鍵！請優先分析此項
- **光線氛圍**: ${data.lighting || "未指定"}
- **鏡頭技術**: ${data.camera || "未指定"}

[ 處理規則 (重要) ]

1. **媒材適應性 (Material Awareness)**：
   - 若風格為「針織/毛線 (Knitted)」：請強調毛線質感、編織紋理、柔軟觸感。
   - 若風格為「黏土動畫 (Claymation)」：請強調指紋痕跡、橡皮泥質感、定格動畫的光影感。
   - 若風格為「微縮模型 (Miniature)」：請強調移軸攝影效果 (Tilt-shift)、景深、微距細節。
   - 若為其他風格，請使用該領域專屬的形容詞。

2. **敘事結構**：不要只是堆疊單字，請用一句完整的描述性語言（例如 "A huge knitted monster stands..." 而非 "Knitted, monster, standing"）。

3. **輸出格式**：請直接輸出優化後的英文提示詞 (Prompt Only)，不需要解釋。

[ 開始生成 ]`;

    // Select prompt based on current locale
    const metaPrompt =
      currentLocale.value === "en" ? metaPromptEN : metaPromptZH;

    try {
      await navigator.clipboard.writeText(metaPrompt);
      copyMetaPromptSuccess.value = true;
      setTimeout(() => {
        copyMetaPromptSuccess.value = false;
      }, 3000);
    } catch (error) {
      alert(t("messages.copyFailed", "複製失敗"));
    }
  };

  // Toggle Edit Prompt
  const toggleEditPrompt = () => {
    showEditPrompt.value = !showEditPrompt.value;
    if (showEditPrompt.value && !editedPrompt.value) {
      editedPrompt.value =
        textOutput.value +
        (form.value.negativePrompt
          ? "\n\nNegative: " + form.value.negativePrompt
          : "");
    }
  };

  // Save to Library
  const saveToLibrary = async () => {
    if (!form.value.description) {
      alert(t("messages.enterDescriptionFirst", "請先輸入主要描述"));
      return;
    }

    try {
      const promptParams = {
        version: "1.0",
        mainDescription: form.value.description,
        params: {},
        isEdited: showEditPrompt.value && editedPrompt.value ? true : false,
      };

      const paramKeys = [
        "shotSize",
        "cameraMovement",
        "angle",
        "focus",
        "style",
        "lighting",
        "colorPalette",
        "quality",
      ];
      paramKeys.forEach((key) => {
        if (form.value[key]) {
          promptParams.params[key] = {
            value: form.value[key],
            weight: weights.value[key],
          };
        }
      });

      let contentToSave;
      if (showEditPrompt.value && editedPrompt.value.trim()) {
        contentToSave = editedPrompt.value;
      } else {
        contentToSave =
          textOutput.value +
          (form.value.negativePrompt
            ? "\n\n---\n\n**Negative Prompt:**\n" + form.value.negativePrompt
            : "");
      }

      const response = await fetch("/api/notes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: `Prompt: ${form.value.description.substring(0, 50)}...`,
          content: contentToSave,
          type: "提示詞",
          remarks: showEditPrompt.value
            ? "Edited via Prompt Builder v2"
            : "Generated by Prompt Builder v2",
          tags: ["Prompt Builder", form.value.style || "General"].filter(
            Boolean
          ),
          urls: [],
          prompt_params: promptParams,
        }),
      });

      const result = await response.json();
      if (result.status === "success") {
        alert(t("messages.savedToLibrary", "已儲存至筆記庫！"));
      } else {
        alert(
          t("messages.saveFailed", "儲存失敗") +
            ": " +
            (result.message || t("messages.unknownError", "未知錯誤"))
        );
      }
    } catch (error) {
      console.error("Save error:", error);
      alert(t("messages.saveFailedCheckNetwork", "儲存失敗，請檢查網路連線"));
    }
  };

  // Randomize Category
  const randomizeCategory = (group) => {
    if (group === "camera") {
      const keys = ["shotSize", "cameraMovement", "angle", "focus"];
      keys.forEach((key) => {
        const opts = options.value[key];
        if (opts && opts.length > 0) {
          const randomOpt = opts[Math.floor(Math.random() * opts.length)];
          form.value[key] = getOptOutput(randomOpt);
        }
      });
    } else if (group === "style") {
      const keys = ["style", "lighting", "colorPalette", "quality"];
      keys.forEach((key) => {
        const opts = options.value[key];
        if (opts && opts.length > 0) {
          const randomOpt = opts[Math.floor(Math.random() * opts.length)];
          form.value[key] = getOptOutput(randomOpt);
        }
      });
    }
  };

  // ==================== Wizard Functions ====================

  const openWizardModal = () => {
    wizardModal.value.subject = "";
    wizardModal.value.action = "";
    wizardModal.value.environment = "";
    wizardModal.value.details = "";
    wizardModal.value.append = form.value.description ? true : false;
    wizardModal.value.visible = true;
  };

  const randomizeWizardField = (field) => {
    const fieldOptions = wizardOptions.value[field]?.options || [];
    if (fieldOptions.length > 0) {
      wizardModal.value[field] =
        fieldOptions[Math.floor(Math.random() * fieldOptions.length)];
    }
  };

  const randomizeAllWizard = () => {
    ["subject", "action", "environment", "details"].forEach((field) => {
      randomizeWizardField(field);
    });
  };

  const chaosRandomize = () => {
    const level = chaosLevel.value;

    if (level === 3 && !hasCustomOptions.value) {
      alert(
        t(
          "messages.chaosModeRequiresCustom",
          "🔴 混沌模式需要自定義詞庫！\n\n請先在「編輯詞庫」中新增您的自定義選項，\n或選擇 Level 1/2 模式。"
        )
      );
      chaosLevel.value = 2;
      return;
    }

    wizardModal.value.subject = "";
    wizardModal.value.action = "";
    wizardModal.value.environment = "";
    wizardModal.value.details = "";

    const getRandomOption = (field) => {
      const opts = wizardOptions.value[field]?.options || [];
      if (opts.length === 0) return "";
      return opts[Math.floor(Math.random() * opts.length)];
    };

    const getRandomStyle = () => {
      const styles = options.value.style || [];
      if (styles.length === 0) return "";
      const opt = styles[Math.floor(Math.random() * styles.length)];
      return getOptOutput(opt);
    };

    if (level === 1) {
      wizardModal.value.subject = getRandomOption("subject");
      const styleText = getRandomStyle();
      if (styleText) {
        wizardModal.value.details = styleText + " style";
      }
    } else if (level === 2) {
      randomizeAllWizard();
      const styleText = getRandomStyle();
      const lightingOpts = options.value.lighting || [];
      if (lightingOpts.length > 0) {
        const lightOpt =
          lightingOpts[Math.floor(Math.random() * lightingOpts.length)];
        const lightText = getOptOutput(lightOpt);
        if (styleText && lightText) {
          wizardModal.value.details =
            (wizardModal.value.details || "") +
            `, ${styleText} style, ${lightText}`;
        }
      }
    } else if (level === 3) {
      randomizeAllWizard();

      const styles = options.value.style || [];
      if (styles.length >= 2) {
        const shuffled = [...styles].sort(() => Math.random() - 0.5);
        const style1 = getOptOutput(shuffled[0]);
        const style2 = getOptOutput(shuffled[1]);
        const dualStyle = `${style1}, ${style2}`;
        wizardModal.value.details =
          (wizardModal.value.details || "") + `, ${dualStyle} fusion style`;
      }

      const extraEffects = [
        "cinematic composition",
        "dramatic atmosphere",
        "surreal elements",
        "unexpected contrast",
        "chaotic energy",
      ];
      const randomEffect =
        extraEffects[Math.floor(Math.random() * extraEffects.length)];
      wizardModal.value.details += `, ${randomEffect}`;
    }
  };

  const wizardPreview = computed(() => {
    const parts = [];
    if (wizardModal.value.subject) parts.push(wizardModal.value.subject);
    if (wizardModal.value.action) parts.push(wizardModal.value.action);
    if (wizardModal.value.environment)
      parts.push(wizardModal.value.environment);
    if (wizardModal.value.details) parts.push(wizardModal.value.details);
    return parts.join(", ");
  });

  const confirmWizard = () => {
    const result = wizardPreview.value;
    if (!result) {
      alert(t("messages.fillAtLeastOneField", "請至少填寫一個欄位"));
      return;
    }

    if (wizardModal.value.append && form.value.description) {
      form.value.description = form.value.description.trim() + ", " + result;
    } else {
      form.value.description = result;
    }

    wizardModal.value.visible = false;
  };

  // ==================== Wizard Edit Modal Functions ====================

  const openWizardEditModal = () => {
    wizardEditModal.value.dimension = "subject";
    wizardEditModal.value.options = [
      ...(wizardOptions.value.subject?.options || []),
    ];
    wizardEditModal.value.newOption = "";
    wizardEditModal.value.visible = true;
  };

  const switchWizardDimension = (dim) => {
    wizardEditModal.value.dimension = dim;
    wizardEditModal.value.options = [
      ...(wizardOptions.value[dim]?.options || []),
    ];
    wizardEditModal.value.newOption = "";
  };

  const addWizardOption = async () => {
    const newOpt = wizardEditModal.value.newOption.trim();
    if (!newOpt) return;

    try {
      const response = await fetch(
        `/api/wizard-options/dimension/${wizardEditModal.value.dimension}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ value: newOpt }),
        }
      );

      const result = await response.json();
      if (result.status === "success") {
        wizardEditModal.value.options.push(newOpt);
        wizardOptions.value[wizardEditModal.value.dimension].options.push(
          newOpt
        );
        wizardEditModal.value.newOption = "";
      } else {
        alert(t("messages.addFailed", "新增失敗") + ": " + result.message);
      }
    } catch (error) {
      console.error("Add wizard option error:", error);
      alert(t("messages.addFailed", "新增失敗"));
    }
  };

  const deleteWizardOption = async (index) => {
    if (
      !confirm(t("messages.confirmDeleteInspiration", "確定要刪除此靈感詞嗎？"))
    )
      return;

    try {
      const response = await fetch(
        `/api/wizard-options/dimension/${wizardEditModal.value.dimension}/${index}`,
        {
          method: "DELETE",
        }
      );

      const result = await response.json();
      if (result.status === "success") {
        wizardEditModal.value.options.splice(index, 1);
        wizardOptions.value[wizardEditModal.value.dimension].options.splice(
          index,
          1
        );
      } else {
        alert(t("messages.deleteFailed", "刪除失敗") + ": " + result.message);
      }
    } catch (error) {
      console.error("Delete wizard option error:", error);
      alert(t("messages.deleteFailed", "刪除失敗"));
    }
  };

  // ==================== Edit Modal Functions ====================

  const openEditModal = (category) => {
    editModal.value.category = category;
    editModal.value.options = [...options.value[category]];
    editModal.value.newDisplay = "";
    editModal.value.newOutput = "";
    editModal.value.visible = true;
  };

  const closeEditModal = () => {
    editModal.value.visible = false;
  };

  const addOption = async () => {
    const display = editModal.value.newDisplay.trim();
    const output = editModal.value.newOutput.trim();

    if (!display && !output) {
      alert(t("messages.fillAtLeastOneField", "請至少填寫一個欄位"));
      return;
    }

    try {
      let newOpt;
      let bodyData;

      if (display && output) {
        newOpt = {
          key: output.toLowerCase().replace(/\s+/g, "_").replace(/[()]/g, ""),
          display: display,
          output: output,
        };
        bodyData = { display, output };
      } else {
        newOpt = display || output;
        bodyData = { value: newOpt };
      }

      const response = await fetch(
        `/api/prompt-options/category/${editModal.value.category}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(bodyData),
        }
      );

      const result = await response.json();
      if (result.status === "success") {
        const addedOpt = result.data.option || newOpt;
        editModal.value.options.push(addedOpt);
        options.value[editModal.value.category].push(addedOpt);
        editModal.value.newDisplay = "";
        editModal.value.newOutput = "";
      } else {
        alert(t("messages.addFailed", "新增失敗") + ": " + result.message);
      }
    } catch (error) {
      console.error("Add option error:", error);
      alert(t("messages.addFailed", "新增失敗"));
    }
  };

  const deleteOption = async (index) => {
    if (!confirm(t("messages.confirmDeleteOption", "確定要刪除此選項嗎？")))
      return;

    try {
      const response = await fetch(
        `/api/prompt-options/category/${editModal.value.category}/${index}`,
        {
          method: "DELETE",
        }
      );

      const result = await response.json();
      if (result.status === "success") {
        editModal.value.options.splice(index, 1);
        options.value[editModal.value.category].splice(index, 1);
      } else {
        alert(t("messages.deleteFailed", "刪除失敗") + ": " + result.message);
      }
    } catch (error) {
      alert(t("messages.deleteFailed", "刪除失敗"));
    }
  };

  // ==================== Template Modal Functions ====================

  const openSaveTemplateModal = () => {
    templateModal.value.name = "";
    templateModal.value.visible = true;
  };

  const saveTemplate = async () => {
    const name = templateModal.value.name.trim();
    if (!name) {
      alert(t("messages.enterTemplateName", "請輸入模板名稱"));
      return;
    }

    const preset = {};
    const paramKeys = [
      "shotSize",
      "cameraMovement",
      "angle",
      "focus",
      "style",
      "lighting",
      "colorPalette",
      "quality",
    ];
    paramKeys.forEach((key) => {
      if (form.value[key]) {
        preset[key] = form.value[key];
      }
    });

    if (Object.keys(preset).length === 0) {
      alert(t("messages.selectAtLeastOne", "請至少選擇一個參數設定"));
      return;
    }

    try {
      const response = await fetch("/api/prompt-options/template", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, preset }),
      });

      const result = await response.json();
      if (result.status === "success") {
        quickTemplates.value.push(result.data.template);
        templateModal.value.visible = false;
        alert(t("messages.templateSaved", "模板已儲存！"));
      } else {
        alert(t("messages.saveFailed", "儲存失敗") + ": " + result.message);
      }
    } catch (error) {
      alert(t("messages.saveFailed", "儲存失敗"));
    }
  };

  const deleteTemplate = async (templateId) => {
    if (!confirm(t("messages.confirmDelete", "確定要刪除這個模板嗎？"))) {
      return;
    }

    try {
      const response = await fetch(
        `/api/prompt-options/template/${templateId}`,
        {
          method: "DELETE",
        }
      );

      const result = await response.json();
      if (result.status === "success") {
        quickTemplates.value = quickTemplates.value.filter(
          (tmpl) => tmpl.id !== templateId
        );
        alert(t("messages.deleteSuccess", "模板已刪除！"));
      } else {
        alert(t("messages.deleteFailed", "刪除失敗") + ": " + result.message);
      }
    } catch (error) {
      console.error("Delete template error:", error);
      alert(t("messages.deleteFailed", "刪除失敗"));
    }
  };

  // ==================== Lifecycle ====================

  // Keyboard Shortcuts Handler
  const handleKeydown = (e) => {
    // Ctrl + Enter: Copy Output
    if (e.ctrlKey && e.key === "Enter") {
      e.preventDefault();
      copyOutput();
    }
    // Ctrl + S: Save to Library
    if (e.ctrlKey && (e.key === "s" || e.key === "S")) {
      e.preventDefault();
      saveToLibrary();
    }
  };

  // Initialize on mount
  const initialize = () => {
    loadLocale(currentLocale.value);
    loadConfig();
    loadWizardOptions();

    // Add Keyboard Shortcuts
    window.addEventListener("keydown", handleKeydown);
  };

  // Cleanup on unmount
  onUnmounted(() => {
    window.removeEventListener("keydown", handleKeydown);
  });

  // ==================== Return ====================

  return {
    // i18n
    t,
    currentLocale,
    availableLocales,
    setLocale,
    getLocaleName,
    langDropdownOpen,
    // State
    configLoading,
    configError,
    outputMode,
    copySuccess,
    useWeights,
    form,
    weights,
    options,
    quickTemplates,
    negativePresets,
    applyTemplate,
    resetForm,
    textOutput,
    jsonOutput,
    copyOutput,
    downloadJSON,
    saveToLibrary,
    randomizeCategory,
    getCategoryLabel,
    // Technical Options
    technicalOptions,
    // Edit Prompt
    showEditPrompt,
    editedPrompt,
    toggleEditPrompt,
    // i18n Helpers
    getOptKey,
    getOptDisplay,
    getOptOutput,
    // Edit Modal
    editModal,
    openEditModal,
    closeEditModal,
    addOption,
    deleteOption,
    // Template Modal
    templateModal,
    openSaveTemplateModal,
    saveTemplate,
    deleteTemplate,
    // Wizard
    wizardOptions,
    wizardModal,
    wizardPreview,
    openWizardModal,
    randomizeWizardField,
    randomizeAllWizard,
    confirmWizard,
    // Wizard Edit Modal
    wizardEditModal,
    openWizardEditModal,
    switchWizardDimension,
    addWizardOption,
    deleteWizardOption,
    getDimensionLabel,
    getDimensionIcon,
    // Chaos Factor
    chaosLevel,
    hasCustomOptions,
    chaosRandomize,
    // v1.8.9: Enhanced Output
    narrativeOutput,
    copyMetaPrompt,
    copyMetaPromptSuccess,
    // Initialize
    initialize,
  };
}
