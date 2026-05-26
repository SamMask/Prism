/**
 * PromptBuilder Page - V2 React Implementation
 * 
 * Modular structure:
 * - usePromptBuilder: Core state & logic hook
 * - ParameterGroup: Collapsible sections
 * - ParameterSelect: Dropdown inputs
 * - OutputPreview: Result display
 * - QuickTemplates: Preset shortcuts
 */
import { Camera, Palette, Save, RotateCcw, Sparkles, Loader2 } from 'lucide-react'
import { usePromptBuilder } from '../hooks/usePromptBuilder'
import {
  ParameterGroup,
  ParameterSelect,
  OutputPreview,
  QuickTemplates,
  WizardModal
} from '../components/prompt-builder'
import { Button } from '../components/ui/Button'

export function PromptBuilder() {
  const {
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
    textOutput,
    narrativeOutput,
    jsonOutput,
    wizardModalOpen,
    wizardForm,
    wizardAppend,
    wizardOptions,
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
    openWizardModal,
    closeWizardModal,
    updateWizardForm,
    randomizeWizardField,
    confirmWizard,
    setWizardAppend,
  } = usePromptBuilder()

  // Loading State
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-4">
          <Loader2 size={48} className="animate-spin text-primary" />
          <p className="text-text-secondary">載入配置中...</p>
        </div>
      </div>
    )
  }

  // Error State
  if (error) {
    return (
      <div className="max-w-md mx-auto mt-20">
        <div className="glass rounded-xl p-6 text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-error/20 flex items-center justify-center">
            <span className="text-3xl">⚠️</span>
          </div>
          <h2 className="text-xl font-semibold text-text-primary mb-2">載入失敗</h2>
          <p className="text-text-secondary mb-4">{error}</p>
          <Button onClick={loadConfig} variant="primary">
            重試
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex gap-6 h-[calc(100vh-8rem)]">
      {/* Left Panel - Configuration */}
      <div className="w-1/2 overflow-y-auto pr-2 space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-accent 
                            flex items-center justify-center">
              <Sparkles size={20} className="text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-text-primary">Prompt Builder</h1>
              <p className="text-sm text-text-muted">結構化提示詞組裝器</p>
            </div>
          </div>
          
          {/* Weight Toggle */}
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={useWeights}
              onChange={(e) => setUseWeights(e.target.checked)}
              className="w-4 h-4 rounded border-border-subtle text-primary focus:ring-primary"
            />
            <span className="text-sm text-text-secondary">權重模式</span>
          </label>
        </div>

        {/* Quick Templates */}
        <QuickTemplates templates={quickTemplates} onApply={applyTemplate} />

        {/* Main Description */}
        <div className="glass rounded-xl p-4">
          <div className="flex items-center justify-between mb-2">
            <label className="block text-sm font-medium text-text-secondary">
              主要描述 *
            </label>
            <button
              onClick={openWizardModal}
              className="px-3 py-1.5 text-xs font-medium rounded-lg bg-gradient-to-r from-primary to-accent text-white hover:opacity-90 transition-opacity flex items-center gap-1.5 shadow-lg shadow-primary/20"
            >
              <Sparkles size={14} />
              靈感引導
            </button>
          </div>
          <textarea
            value={form.description}
            onChange={(e) => updateForm('description', e.target.value)}
            placeholder="描述你想要生成的圖像內容..."
            rows={3}
            className="w-full bg-bg-elevated border border-border-subtle rounded-lg px-4 py-3
                       text-text-primary placeholder:text-text-muted resize-none
                       focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary"
          />
        </div>

        {/* Camera Parameters */}
        <ParameterGroup 
          title="鏡頭設定" 
          icon={<Camera size={18} className="text-primary" />}
          onRandomize={() => randomizeCategory('camera')}
        >
          <div className="grid grid-cols-2 gap-4">
            <ParameterSelect
              label="景別"
              value={form.shotSize}
              options={options.shotSize}
              onChange={(v) => updateForm('shotSize', v)}
              weight={weights.shotSize}
              onWeightChange={(w) => updateWeight('shotSize', w)}
              showWeight={useWeights}
            />
            <ParameterSelect
              label="鏡頭運動"
              value={form.cameraMovement}
              options={options.cameraMovement}
              onChange={(v) => updateForm('cameraMovement', v)}
              weight={weights.cameraMovement}
              onWeightChange={(w) => updateWeight('cameraMovement', w)}
              showWeight={useWeights}
            />
            <ParameterSelect
              label="拍攝角度"
              value={form.angle}
              options={options.angle}
              onChange={(v) => updateForm('angle', v)}
              weight={weights.angle}
              onWeightChange={(w) => updateWeight('angle', w)}
              showWeight={useWeights}
            />
            <ParameterSelect
              label="對焦"
              value={form.focus}
              options={options.focus}
              onChange={(v) => updateForm('focus', v)}
              weight={weights.focus}
              onWeightChange={(w) => updateWeight('focus', w)}
              showWeight={useWeights}
            />
          </div>
        </ParameterGroup>

        {/* Style Parameters */}
        <ParameterGroup 
          title="風格設定" 
          icon={<Palette size={18} className="text-accent" />}
          onRandomize={() => randomizeCategory('style')}
        >
          <div className="grid grid-cols-2 gap-4">
            <ParameterSelect
              label="藝術風格"
              value={form.style}
              options={options.style}
              onChange={(v) => updateForm('style', v)}
              weight={weights.style}
              onWeightChange={(w) => updateWeight('style', w)}
              showWeight={useWeights}
            />
            <ParameterSelect
              label="光線"
              value={form.lighting}
              options={options.lighting}
              onChange={(v) => updateForm('lighting', v)}
              weight={weights.lighting}
              onWeightChange={(w) => updateWeight('lighting', w)}
              showWeight={useWeights}
            />
            <ParameterSelect
              label="色調"
              value={form.colorPalette}
              options={options.colorPalette}
              onChange={(v) => updateForm('colorPalette', v)}
              weight={weights.colorPalette}
              onWeightChange={(w) => updateWeight('colorPalette', w)}
              showWeight={useWeights}
            />
            <ParameterSelect
              label="品質強調"
              value={form.quality}
              options={options.quality}
              onChange={(v) => updateForm('quality', v)}
              weight={weights.quality}
              onWeightChange={(w) => updateWeight('quality', w)}
              showWeight={useWeights}
            />
          </div>
        </ParameterGroup>

        {/* Negative Prompt */}
        <div className="glass rounded-xl p-4">
          <div className="flex items-center justify-between mb-2">
            <label className="text-sm font-medium text-text-secondary">
              Negative Prompt
            </label>
            {negativePresets.length > 0 && (
              <select
                onChange={(e) => updateForm('negativePrompt', e.target.value)}
                className="text-xs bg-bg-elevated border border-border-subtle rounded px-2 py-1
                           text-text-muted cursor-pointer"
              >
                <option value="">預設...</option>
                {negativePresets.map((preset, idx) => (
                  <option key={idx} value={preset.value}>{preset.name}</option>
                ))}
              </select>
            )}
          </div>
          <textarea
            value={form.negativePrompt}
            onChange={(e) => updateForm('negativePrompt', e.target.value)}
            placeholder="不想要的元素..."
            rows={2}
            className="w-full bg-bg-elevated border border-border-subtle rounded-lg px-4 py-2
                       text-text-primary placeholder:text-text-muted resize-none text-sm
                       focus:outline-none focus:ring-2 focus:ring-primary/50"
          />
        </div>

        {/* Action Buttons */}
        <div className="flex gap-3">
          <Button onClick={saveToLibrary} variant="primary" className="flex-1 flex items-center justify-center gap-2">
            <Save size={18} />
            儲存至筆記庫
          </Button>
          <Button onClick={resetForm} variant="ghost" className="flex items-center gap-2">
            <RotateCcw size={18} />
            重置
          </Button>
        </div>
      </div>

      {/* Right Panel - Output Preview */}
      <div className="w-1/2">
        <OutputPreview
          textOutput={textOutput}
          narrativeOutput={narrativeOutput}
          jsonOutput={jsonOutput}
          negativePrompt={form.negativePrompt}
          outputMode={outputMode}
          onModeChange={setOutputMode}
          onCopy={copyOutput}
          onOptimize={copyForLLM}
          copySuccess={copySuccess}
        />
      </div>

      {/* Wizard Modal */}
      <WizardModal
        isOpen={wizardModalOpen}
        onClose={closeWizardModal}
        wizardForm={wizardForm}
        wizardOptions={wizardOptions}
        wizardAppend={wizardAppend}
        onUpdateField={updateWizardForm}
        onRandomizeField={randomizeWizardField}
        onConfirm={confirmWizard}
        onSetAppend={setWizardAppend}
      />
    </div>
  )
}
