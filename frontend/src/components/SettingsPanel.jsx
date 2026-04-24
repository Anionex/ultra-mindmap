import { useState, useEffect } from 'react';
import { X, Eye, EyeOff, Check, Loader2 } from 'lucide-react';
import * as api from '../services/api';

const STORAGE_KEY = 'ultra-mindmap-settings';

function loadLocal() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {};
  } catch {
    return {};
  }
}

export function syncSettingsOnBoot() {
  const local = loadLocal();
  if (local.api_key || local.api_base) {
    api.updateSettings({ api_key: local.api_key || '', api_base: local.api_base || '' }).catch(() => {});
  }
}

export default function SettingsModal({ open, onClose, addTip }) {
  const [apiKey, setApiKey] = useState('');
  const [apiBase, setApiBase] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [saving, setSaving] = useState(false);
  const [serverHint, setServerHint] = useState(null);
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    if (!open) return;
    const local = loadLocal();
    setApiKey(local.api_key || '');
    setApiBase(local.api_base || '');
    setDirty(false);
    api.getSettings().then(setServerHint).catch(() => {});
  }, [open]);

  if (!open) return null;

  const handleSave = async () => {
    setSaving(true);
    try {
      const result = await api.updateSettings({ api_key: apiKey, api_base: apiBase });
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ api_key: apiKey, api_base: apiBase }));
      setServerHint(result);
      setDirty(false);
      addTip('success', '设置已保存');
    } catch (e) {
      addTip('error', api.extractErrorMessage(e));
    } finally {
      setSaving(false);
    }
  };

  const status = serverHint?.api_key_set;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center">
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-md mx-4 overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <h2 className="text-sm font-semibold text-gray-900">系统设置</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 transition-colors">
            <X size={18} />
          </button>
        </div>

        <div className="px-6 py-5 flex flex-col gap-5">
          <div className="flex flex-col gap-1.5">
            <div className="flex items-center justify-between">
              <label className="text-xs font-medium text-gray-600">API Key</label>
              {status !== undefined && (
                <span className={`text-xs ${status ? 'text-green-600' : 'text-amber-600'}`}>
                  {status ? `已配置 (${serverHint.api_key_hint})` : '未配置'}
                </span>
              )}
            </div>
            <div className="relative">
              <input
                type={showKey ? 'text' : 'password'}
                value={apiKey}
                onChange={(e) => { setApiKey(e.target.value); setDirty(true); }}
                placeholder="sk-..."
                className="w-full px-3 py-2 pr-9 text-sm bg-white border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-300 font-mono"
              />
              <button
                type="button"
                onClick={() => setShowKey(!showKey)}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                {showKey ? <EyeOff size={14} /> : <Eye size={14} />}
              </button>
            </div>
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-gray-600">API Base URL</label>
            <input
              type="text"
              value={apiBase}
              onChange={(e) => { setApiBase(e.target.value); setDirty(true); }}
              placeholder="留空使用默认值"
              className="w-full px-3 py-2 text-sm bg-white border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-300 font-mono"
            />
          </div>
        </div>

        <div className="px-6 py-4 border-t border-gray-100 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg text-xs font-medium text-gray-600 hover:bg-gray-100 transition-colors"
          >
            取消
          </button>
          <button
            onClick={handleSave}
            disabled={saving || !dirty}
            className={`
              px-4 py-2 rounded-lg text-xs font-medium transition-all duration-150 flex items-center gap-1.5
              ${saving || !dirty
                ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                : 'bg-gray-900 text-white hover:bg-gray-800 active:scale-[0.98]'}
            `}
          >
            {saving ? <Loader2 size={13} className="animate-spin" /> : <Check size={13} />}
            {saving ? '保存中...' : '保存'}
          </button>
        </div>
      </div>
    </div>
  );
}
