
import { useEffect, useState } from 'react';
import { Sparkles, Loader2, Check, AlertCircle, RefreshCw } from 'lucide-react';
import { Button, toast } from '../ui';


interface AIStatus {
  available: boolean;
  models: string[];
  vision_ready: boolean;
  text_ready: boolean;
  error?: string;
}

interface AIConfigSectionProps {
  aiStatus: AIStatus | null;
  isChecking: boolean;
  onRefresh: () => void;
}

export function AIConfigSection({ aiStatus, isChecking, onRefresh }: AIConfigSectionProps) {
  const [selectedVisionModel, setSelectedVisionModel] = useState<string>('');
  const [selectedTextModel, setSelectedTextModel] = useState<string>('');

  // Auto-select default models when AI status is loaded
  useEffect(() => {
    // Load saved preferences
    const savedVisionModel = localStorage.getItem('ai_vision_model');
    const savedTextModel = localStorage.getItem('ai_text_model');
    if (savedVisionModel) setSelectedVisionModel(savedVisionModel);
    if (savedTextModel) setSelectedTextModel(savedTextModel);

    if (aiStatus?.available && aiStatus.models.length > 0) {
      // Set default vision model if not already set or saved
      if (!savedVisionModel) {
        const visionModels = aiStatus.models.filter(m => 
          m.includes('llava') || m.includes('bakllava') || m.includes('moondream')
        );
        if (visionModels.length > 0) {
          setSelectedVisionModel(visionModels[0]);
          localStorage.setItem('ai_vision_model', visionModels[0]);
        }
      }
      
      // Set default text model if not already set or saved
      if (!savedTextModel) {
        const textModels = aiStatus.models.filter(m => 
          !m.includes('llava') && !m.includes('bakllava')
        );
        if (textModels.length > 0) {
          setSelectedTextModel(textModels[0]);
          localStorage.setItem('ai_text_model', textModels[0]);
        }
      }
    }
  }, [aiStatus]);

  return (
    <div className="glass rounded-xl p-6">
      <h2 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
        <Sparkles size={20} className="text-accent" />
        AI 服務狀態
      </h2>
      
      {isChecking ? (
        <div className="flex items-center gap-2 text-text-muted">
          <Loader2 size={18} className="animate-spin" />
          正在檢查 Ollama 服務...
        </div>
      ) : aiStatus ? (
        <div className="space-y-4">
          {/* Connection Status */}
          <div className="flex items-center gap-3">
            {aiStatus.available ? (
              <span className="flex items-center gap-2 text-success">
                <Check size={18} />
                Ollama 已連線
              </span>
            ) : (
              <span className="flex items-center gap-2 text-error">
                <AlertCircle size={18} />
                Ollama 未連線
              </span>
            )}
          </div>

          {/* Model Status Row */}
          <div className="flex flex-wrap gap-4">
            <div className="flex items-center gap-2">
              {aiStatus.vision_ready ? (
                <span className="flex items-center gap-1.5 text-success text-sm">
                  <Check size={16} />
                  視覺模型
                </span>
              ) : (
                <span className="flex items-center gap-1.5 text-warning text-sm">
                  <AlertCircle size={16} />
                  視覺模型未安裝
                </span>
              )}
            </div>
            <div className="flex items-center gap-2">
              {aiStatus.text_ready ? (
                <span className="flex items-center gap-1.5 text-success text-sm">
                  <Check size={16} />
                  文字模型
                </span>
              ) : (
                <span className="flex items-center gap-1.5 text-warning text-sm">
                  <AlertCircle size={16} />
                  文字模型未安裝
                </span>
              )}
            </div>
          </div>

          {/* Model List & Selection */}
          {aiStatus.available && aiStatus.models.length > 0 && (
            <div className="space-y-3 pt-3 border-t border-border-subtle">
              {/* Installed Models */}
              <div>
                <p className="text-text-secondary text-sm mb-2">已安裝模型：</p>
                <div className="flex flex-wrap gap-2">
                  {aiStatus.models.map((model) => (
                    <span
                      key={model}
                      className={`px-2.5 py-1 text-xs rounded-full
                        ${model.includes('llava') || model.includes('bakllava')
                          ? 'bg-accent/10 text-accent border border-accent/30'
                          : 'bg-primary/10 text-primary border border-primary/30'
                        }`}
                    >
                      {model}
                      {(model.includes('llava') || model.includes('bakllava')) && (
                        <span className="ml-1 opacity-60">👁️</span>
                      )}
                    </span>
                  ))}
                </div>
              </div>

              {/* Model Selectors */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Vision Model Selector */}
                <div>
                  <label className="text-text-secondary text-sm mb-1.5 block">
                    圖片分析模型 (Vision)
                  </label>
                  <select
                    value={selectedVisionModel}
                    onChange={(e) => {
                      setSelectedVisionModel(e.target.value);
                      localStorage.setItem('ai_vision_model', e.target.value);
                      toast.success(`視覺模型已設定為 ${e.target.value}`);
                    }}
                    className="w-full px-3 py-2 rounded-lg
                               bg-bg-elevated border border-border-default
                               text-text-primary text-sm
                               focus:outline-none focus:border-primary"
                  >
                    {aiStatus.models
                      .filter(m => m.includes('llava') || m.includes('bakllava') || m.includes('moondream'))
                      .map((model) => (
                        <option key={model} value={model}>
                          {model}
                        </option>
                      ))}
                    {!aiStatus.models.some(m => m.includes('llava') || m.includes('bakllava') || m.includes('moondream')) && (
                      <option value="" disabled>無可用視覺模型</option>
                    )}
                  </select>
                </div>

                {/* Text Model Selector */}
                <div>
                  <label className="text-text-secondary text-sm mb-1.5 block">
                    文字摘要模型 (Text)
                  </label>
                  <select
                    value={selectedTextModel}
                    onChange={(e) => {
                      setSelectedTextModel(e.target.value);
                      localStorage.setItem('ai_text_model', e.target.value);
                      toast.success(`文字模型已設定為 ${e.target.value}`);
                    }}
                    className="w-full px-3 py-2 rounded-lg
                               bg-bg-elevated border border-border-default
                               text-text-primary text-sm
                               focus:outline-none focus:border-primary"
                  >
                    {aiStatus.models
                      .filter(m => !m.includes('llava') && !m.includes('bakllava'))
                      .map((model) => (
                        <option key={model} value={model}>
                          {model}
                        </option>
                      ))}
                    {!aiStatus.models.some(m => !m.includes('llava') && !m.includes('bakllava')) && (
                      <option value="" disabled>無可用文字模型</option>
                    )}
                  </select>
                </div>
              </div>

              <p className="text-text-muted text-xs">
                💡 使用 <code className="bg-bg-elevated px-1 rounded">ollama pull 模型名稱</code> 來下載更多模型
              </p>
            </div>
          )}

          {aiStatus.error && (
            <p className="text-error text-sm">{aiStatus.error}</p>
          )}
        </div>
      ) : (
        <p className="text-text-muted">無法取得 AI 狀態</p>
      )}

      <div className="mt-4 flex justify-end">
        <Button
          onClick={onRefresh}
          variant="ghost"
          className="text-sm"
          disabled={isChecking}
        >
          <RefreshCw size={16} className={isChecking ? 'animate-spin' : ''} />
          重新檢查
        </Button>
      </div>
    </div>
  );
}
