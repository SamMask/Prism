/**
 * usePromptBuilder.ts - React Hook for Prompt Builder
 * Prism V2 - Port from Vue 3 usePromptBuilder.js
 *
 * Features:
 * - Form state management
 * - Options loading from API
 * - Output generation (text, narrative, json)
 * - Wizard modal state
 */

import { useState, useEffect, useMemo, useCallback } from "react";

// Types
export interface PromptOption {
  display: string;
  displayEN?: string;
  output: string;
}

export interface PromptForm {
  description: string;
  shotSize: string;
  cameraMovement: string;
  angle: string;
  focus: string;
  style: string;
  lighting: string;
  colorPalette: string;
  quality: string;
  negativePrompt: string;
  aspectRatio: string;
  resolution: string;
  styleModifier: string;
}

export interface PromptWeights {
  shotSize: number;
  cameraMovement: number;
  angle: number;
  focus: number;
  style: number;
  lighting: number;
  colorPalette: number;
  quality: number;
}

export interface QuickTemplate {
  name: string;
  preset: Partial<PromptForm>;
}

export interface WizardOptions {
  subject: { placeholder: string; options: string[] };
  action: { placeholder: string; options: string[] };
  environment: { placeholder: string; options: string[] };
  details: { placeholder: string; options: string[] };
}

export interface TechnicalOptions {
  aspectRatio: PromptOption[];
  resolution: PromptOption[];
  styleModifiers: PromptOption[];
}

// Initial States
const initialForm: PromptForm = {
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
  aspectRatio: "",
  resolution: "",
  styleModifier: "",
};

const initialWeights: PromptWeights = {
  shotSize: 1.0,
  cameraMovement: 1.0,
  angle: 1.0,
  focus: 1.0,
  style: 1.0,
  lighting: 1.0,
  colorPalette: 1.0,
  quality: 1.0,
};

// Helper Functions
const getOptOutput = (opt: string | PromptOption): string => {
  if (typeof opt === "string") return opt;
  return opt?.output || opt?.display || "";
};

const getOptDisplay = (
  opt: string | PromptOption,
  locale: string = "zh-TW"
): string => {
  if (typeof opt === "string") return opt;
  if (locale === "en") {
    return opt?.displayEN || opt?.output || opt?.display || "";
  }
  return opt?.display || opt?.output || "";
};

// Main Hook
export function usePromptBuilder() {
  // Loading State
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Form State
  const [form, setForm] = useState<PromptForm>(initialForm);
  const [weights, setWeights] = useState<PromptWeights>(initialWeights);
  const [useWeights, setUseWeights] = useState(false);

  // Output Mode
  const [outputMode, setOutputMode] = useState<"text" | "narrative" | "json">(
    "text"
  );
  const [copySuccess, setCopySuccess] = useState(false);

  // Options (loaded from API)
  const [options, setOptions] = useState<Record<string, PromptOption[]>>({
    shotSize: [],
    cameraMovement: [],
    angle: [],
    focus: [],
    style: [],
    lighting: [],
    colorPalette: [],
    quality: [],
  });

  // Quick Templates
  const [quickTemplates, setQuickTemplates] = useState<QuickTemplate[]>([]);

  // Negative Presets
  const [negativePresets, setNegativePresets] = useState<
    { name: string; value: string }[]
  >([]);

  // Technical Options
  const [technicalOptions, setTechnicalOptions] = useState<TechnicalOptions>({
    aspectRatio: [],
    resolution: [],
    styleModifiers: [],
  });

  // Wizard Options
  const [wizardOptions, setWizardOptions] = useState<WizardOptions>({
    subject: { placeholder: "", options: [] },
    action: { placeholder: "", options: [] },
    environment: { placeholder: "", options: [] },
    details: { placeholder: "", options: [] },
  });

  // Wizard Modal State
  const [wizardModalOpen, setWizardModalOpen] = useState(false);
  const [wizardForm, setWizardForm] = useState({
    subject: "",
    action: "",
    environment: "",
    details: "",
  });
  const [wizardAppend, setWizardAppend] = useState(false);

  // Load Config from API
  const loadConfig = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await fetch("/api/prompt-options");
      if (!response.ok) throw new Error("Failed to load config");

      const result = await response.json();
      if (result.status !== "success") throw new Error(result.message);

      const config = result.data;

      if (config.categories) {
        setOptions({
          shotSize: config.categories.shotSize?.options || [],
          cameraMovement: config.categories.cameraMovement?.options || [],
          angle: config.categories.angle?.options || [],
          focus: config.categories.focus?.options || [],
          style: config.categories.style?.options || [],
          lighting: config.categories.lighting?.options || [],
          colorPalette: config.categories.colorPalette?.options || [],
          quality: config.categories.quality?.options || [],
        });
      }

      if (config.quickTemplates) {
        setQuickTemplates(config.quickTemplates);
      }

      if (config.negativePromptPresets) {
        setNegativePresets(config.negativePromptPresets);
      }

      setIsLoading(false);
    } catch (err) {
      console.error("Load config error:", err);
      setError(err instanceof Error ? err.message : "Unknown error");
      setIsLoading(false);
    }
  }, []);

  // Load Wizard Options
  const loadWizardOptions = useCallback(async () => {
    try {
      const response = await fetch("/api/wizard-options");
      if (!response.ok) throw new Error("Failed to load wizard options");

      const result = await response.json();
      if (result.status !== "success") throw new Error(result.message);
      const config = result.data;

      if (config.technicalSpecs) {
        setTechnicalOptions({
          aspectRatio: config.technicalSpecs.aspectRatio?.options || [],
          resolution: config.technicalSpecs.resolution?.options || [],
          styleModifiers: config.technicalSpecs.styleModifiers?.options || [],
        });
      }

      if (config.dimensions) {
        setWizardOptions({
          subject: config.dimensions.subject || {
            placeholder: "",
            options: [],
          },
          action: config.dimensions.action || { placeholder: "", options: [] },
          environment: config.dimensions.environment || {
            placeholder: "",
            options: [],
          },
          details: config.dimensions.details || {
            placeholder: "",
            options: [],
          },
        });
      }
    } catch (err) {
      console.error("Load wizard options error:", err);
    }
  }, []);

  // Initialize
  useEffect(() => {
    loadConfig();
    loadWizardOptions();
  }, [loadConfig, loadWizardOptions]);

  // Form Update Helper
  const updateForm = useCallback((key: keyof PromptForm, value: string) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  }, []);

  // Weight Update Helper
  const updateWeight = useCallback(
    (key: keyof PromptWeights, value: number) => {
      setWeights((prev) => ({ ...prev, [key]: value }));
    },
    []
  );

  // Format with Weight
  const formatWithWeight = useCallback(
    (value: string, key: keyof PromptWeights): string => {
      if (!value) return "";
      if (!useWeights) return value;
      const w = weights[key];
      if (w === 1.0) return value;
      return `(${value}:${w.toFixed(1)})`;
    },
    [useWeights, weights]
  );

  // Text Output
  const textOutput = useMemo(() => {
    const parts: string[] = [];

    if (form.description) parts.push(form.description);
    if (form.shotSize) parts.push(formatWithWeight(form.shotSize, "shotSize"));
    if (form.cameraMovement)
      parts.push(formatWithWeight(form.cameraMovement, "cameraMovement"));
    if (form.angle) parts.push(formatWithWeight(form.angle, "angle"));
    if (form.focus) parts.push(formatWithWeight(form.focus, "focus"));
    if (form.style) parts.push(formatWithWeight(form.style, "style"));
    if (form.lighting) parts.push(formatWithWeight(form.lighting, "lighting"));
    if (form.colorPalette)
      parts.push(formatWithWeight(form.colorPalette, "colorPalette"));
    if (form.quality) parts.push(formatWithWeight(form.quality, "quality"));
    if (form.aspectRatio) parts.push(form.aspectRatio);
    if (form.resolution) parts.push(form.resolution);
    if (form.styleModifier) parts.push(form.styleModifier);

    return parts.join(", ");
  }, [form, formatWithWeight]);

  // Narrative Output (Natural Language)
  const narrativeOutput = useMemo(() => {
    let sentence = "";

    if (form.description) {
      sentence = form.description.trim();
    }
    if (sentence && !sentence.endsWith(".")) sentence += ".";

    if (form.style) {
      const firstLetter = form.style.trim().charAt(0).toLowerCase();
      const article = ["a", "e", "i", "o", "u"].includes(firstLetter)
        ? "An"
        : "A";
      const isPhoto =
        form.style.toLowerCase().includes("photo") ||
        form.style.toLowerCase().includes("realistic");

      if (isPhoto) {
        sentence = `${article} ${form.style} photograph: ${sentence}`;
      } else {
        sentence = `${article} ${form.style} artwork. ${sentence}`;
      }
    }

    if (form.lighting) {
      sentence += ` Illuminated by ${form.lighting}.`;
    }
    if (form.colorPalette) {
      sentence += ` Rendered in ${form.colorPalette} tones.`;
    }

    const techParams: string[] = [];
    if (form.shotSize) techParams.push(form.shotSize);
    if (form.angle) techParams.push(`shot from a ${form.angle}`);
    if (form.cameraMovement) techParams.push(`with ${form.cameraMovement}`);
    if (form.focus) techParams.push(form.focus);

    if (techParams.length > 0) {
      sentence += ` Captured ${techParams.join(", ")}.`;
    }
    if (form.quality) {
      sentence += ` ${form.quality}.`;
    }

    // Midjourney Parameters
    if (form.aspectRatio) {
      const match = form.aspectRatio.match(/(\d+:\d+)/);
      if (match) {
        sentence += ` --ar ${match[1]}`;
      }
    }
    if (form.resolution) {
      sentence += ` --${form.resolution}`;
    }
    if (form.styleModifier) {
      sentence += ` --${form.styleModifier}`;
    }

    return sentence.trim();
  }, [form]);

  // JSON Output
  const jsonOutput = useMemo(() => {
    const output: Record<string, unknown> = {};

    if (form.description) output.description = form.description;
    if (form.shotSize) {
      output.shot_size = useWeights
        ? { value: form.shotSize, weight: weights.shotSize }
        : form.shotSize;
    }
    if (form.cameraMovement) {
      output.camera_movement = useWeights
        ? { value: form.cameraMovement, weight: weights.cameraMovement }
        : form.cameraMovement;
    }
    if (form.angle) {
      output.angle = useWeights
        ? { value: form.angle, weight: weights.angle }
        : form.angle;
    }
    if (form.focus) {
      output.focus = useWeights
        ? { value: form.focus, weight: weights.focus }
        : form.focus;
    }
    if (form.style) {
      output.style = useWeights
        ? { value: form.style, weight: weights.style }
        : form.style;
    }
    if (form.lighting) {
      output.lighting = useWeights
        ? { value: form.lighting, weight: weights.lighting }
        : form.lighting;
    }
    if (form.colorPalette) {
      output.color_palette = useWeights
        ? { value: form.colorPalette, weight: weights.colorPalette }
        : form.colorPalette;
    }
    if (form.quality) {
      output.quality = useWeights
        ? { value: form.quality, weight: weights.quality }
        : form.quality;
    }
    if (form.negativePrompt) output.negative_prompt = form.negativePrompt;

    return JSON.stringify(output, null, 2);
  }, [form, useWeights, weights]);

  // Copy Output
  const copyOutput = useCallback(async () => {
    let text = "";
    if (outputMode === "text") {
      text =
        textOutput +
        (form.negativePrompt ? `\n\nNegative: ${form.negativePrompt}` : "");
    } else if (outputMode === "narrative") {
      text =
        narrativeOutput +
        (form.negativePrompt ? `\n\nNegative: ${form.negativePrompt}` : "");
    } else {
      text = jsonOutput;
    }

    try {
      await navigator.clipboard.writeText(text);
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 2000);
    } catch (err) {
      console.error("Copy failed:", err);
      alert("複製失敗，請手動選取複製");
    }
  }, [
    outputMode,
    textOutput,
    narrativeOutput,
    jsonOutput,
    form.negativePrompt,
  ]);

  // Copy for LLM Optimization
  const copyForLLM = useCallback(async () => {
    const currentOutput = outputMode === "narrative" ? narrativeOutput : textOutput;
    if (!currentOutput) {
      alert("尚無輸出內容");
      return;
    }

    const llmPrompt = `請幫我優化以下 AI 圖像生成提示詞，保持原有意圖但讓描述更具表現力和細節：

原始提示詞：
${currentOutput}
${form.negativePrompt ? `\nNegative Prompt: ${form.negativePrompt}` : ""}

請提供：
1. 優化後的正向提示詞 (Enhanced Positive Prompt)
2. 建議的負面提示詞 (Suggested Negative Prompt)
3. 簡短說明你做了哪些改進`;

    try {
      await navigator.clipboard.writeText(llmPrompt);
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 2000);
      alert("已複製 LLM 優化指令！\n貼到 ChatGPT 或 Claude 即可獲得優化建議。");
    } catch (err) {
      console.error("Copy failed:", err);
      alert("複製失敗，請手動選取複製");
    }
  }, [outputMode, textOutput, narrativeOutput, form.negativePrompt]);

  // Reset Form
  const resetForm = useCallback(() => {
    setForm(initialForm);
    setWeights(initialWeights);
  }, []);

  // Apply Template
  const applyTemplate = useCallback((template: QuickTemplate) => {
    setForm((prev) => ({ ...prev, ...template.preset }));
  }, []);

  // Randomize Category
  const randomizeCategory = useCallback(
    (group: "camera" | "style") => {
      const getRandomOpt = (opts: PromptOption[]) => {
        if (!opts || opts.length === 0) return "";
        const randomOpt = opts[Math.floor(Math.random() * opts.length)];
        return getOptOutput(randomOpt);
      };

      if (group === "camera") {
        setForm((prev) => ({
          ...prev,
          shotSize: getRandomOpt(options.shotSize),
          cameraMovement: getRandomOpt(options.cameraMovement),
          angle: getRandomOpt(options.angle),
          focus: getRandomOpt(options.focus),
        }));
      } else if (group === "style") {
        setForm((prev) => ({
          ...prev,
          style: getRandomOpt(options.style),
          lighting: getRandomOpt(options.lighting),
          colorPalette: getRandomOpt(options.colorPalette),
          quality: getRandomOpt(options.quality),
        }));
      }
    },
    [options]
  );

  // Save to Library
  const saveToLibrary = useCallback(async () => {
    if (!form.description) {
      alert("請先輸入主要描述");
      return;
    }

    try {
      // Phase 0 Step 0.1.2: 先取得「提示詞」分類的 ID
      const categoriesResponse = await fetch("/api/categories");
      const categoriesData = await categoriesResponse.json();

      let promptCategoryId = null;
      if (categoriesData.status === "success") {
        const promptCategory = categoriesData.data.find(
          (cat: any) => cat.name === "提示詞 | Prompt" || cat.name.includes("提示")
        );
        promptCategoryId = promptCategory?.id;
      }

      const promptParams = {
        version: "1.0",
        mainDescription: form.description,
        params: {} as Record<string, { value: string; weight: number }>,
      };

      const paramKeys: (keyof PromptWeights)[] = [
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
        if (form[key]) {
          promptParams.params[key] = {
            value: form[key],
            weight: weights[key],
          };
        }
      });

      const contentToSave =
        textOutput +
        (form.negativePrompt
          ? "\n\n---\n\n**Negative Prompt:**\n" + form.negativePrompt
          : "");

      const notePayload: any = {
        title: `Prompt: ${form.description.substring(0, 50)}...`,
        content: contentToSave,
        remarks: "Generated by Prompt Builder V2",
        tags: ["Prompt Builder", form.style || "General"].filter(Boolean),
        urls: [],
        prompt_params: promptParams,
      };

      // Phase 0 Step 0.1.2: 使用 category_id 而非 type
      if (promptCategoryId) {
        notePayload.category_id = promptCategoryId;
      }

      const response = await fetch("/api/notes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(notePayload),
      });

      const result = await response.json();
      if (result.status === "success") {
        alert("已儲存至筆記庫！");
      } else {
        alert("儲存失敗: " + (result.message || "未知錯誤"));
      }
    } catch (err) {
      console.error("Save error:", err);
      alert("儲存失敗，請檢查網路連線");
    }
  }, [form, weights, textOutput]);

  // Wizard Functions
  const openWizardModal = useCallback(() => {
    setWizardModalOpen(true);
  }, []);

  const closeWizardModal = useCallback(() => {
    setWizardModalOpen(false);
  }, []);

  const updateWizardForm = useCallback((field: string, value: string) => {
    setWizardForm((prev) => ({ ...prev, [field]: value }));
  }, []);

  const randomizeWizardField = useCallback((field: keyof WizardOptions) => {
    const fieldOptions = wizardOptions[field]?.options || [];
    if (fieldOptions.length > 0) {
      const randomOption = fieldOptions[Math.floor(Math.random() * fieldOptions.length)];
      setWizardForm((prev) => ({ ...prev, [field]: randomOption }));
    }
  }, [wizardOptions]);

  const confirmWizard = useCallback(() => {
    const parts = [];
    if (wizardForm.subject) parts.push(wizardForm.subject);
    if (wizardForm.action) parts.push(wizardForm.action);
    if (wizardForm.environment) parts.push(wizardForm.environment);
    if (wizardForm.details) parts.push(wizardForm.details);

    const result = parts.join(", ");

    if (!result) {
      alert("請至少填寫一個欄位");
      return;
    }

    if (wizardAppend && form.description) {
      setForm((prev) => ({
        ...prev,
        description: prev.description.trim() + ", " + result,
      }));
    } else {
      setForm((prev) => ({
        ...prev,
        description: result,
      }));
    }

    // Reset wizard form and close modal
    setWizardForm({
      subject: "",
      action: "",
      environment: "",
      details: "",
    });
    setWizardAppend(false);
    setWizardModalOpen(false);
  }, [wizardForm, wizardAppend, form.description]);

  return {
    // State
    isLoading,
    error,
    form,
    weights,
    useWeights,
    outputMode,
    copySuccess,
    options,
    quickTemplates,
    negativePresets,
    technicalOptions,
    wizardOptions,

    // Wizard State
    wizardModalOpen,
    wizardForm,
    wizardAppend,

    // Outputs
    textOutput,
    narrativeOutput,
    jsonOutput,

    // Actions
    updateForm,
    updateWeight,
    setUseWeights,
    setOutputMode,
    copyOutput,
    copyForLLM,
    resetForm,
    applyTemplate,
    randomizeCategory,
    saveToLibrary,
    loadConfig,

    // Wizard Actions
    openWizardModal,
    closeWizardModal,
    updateWizardForm,
    randomizeWizardField,
    confirmWizard,
    setWizardAppend,

    // Helpers
    getOptDisplay,
    getOptOutput,
  };
}
