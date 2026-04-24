import { useState, useEffect, useCallback, useRef } from 'react';
import { Brain, Loader2, Settings } from 'lucide-react';
import FileLibrary from './components/FileLibrary';
import EnginePanel from './components/EnginePanel';
import BenchPanel from './components/BenchPanel';
import SettingsModal, { syncSettingsOnBoot } from './components/SettingsPanel';
import MindMapView from './components/MindMapView';
import TipCard from './components/TipCard';
import * as api from './services/api';

let tipId = 0;

export default function App() {
  const [files, setFiles] = useState([]);
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [engines, setEngines] = useState([]);
  const [selectedEngine, setSelectedEngine] = useState('');
  const [params, setParams] = useState({});
  const [mindmapData, setMindmapData] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [tips, setTips] = useState([]);
  const [activeTab, setActiveTab] = useState('generate');
  const [sidebarWidth, setSidebarWidth] = useState(360);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const dragging = useRef(false);

  useEffect(() => {
    const onMouseMove = (e) => {
      if (!dragging.current) return;
      setSidebarWidth(Math.min(Math.max(e.clientX, 280), 800));
    };
    const onMouseUp = () => { dragging.current = false; document.body.style.cursor = ''; document.body.style.userSelect = ''; };
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
    return () => { window.removeEventListener('mousemove', onMouseMove); window.removeEventListener('mouseup', onMouseUp); };
  }, []);

  const addTip = useCallback((type, message) => {
    const id = ++tipId;
    setTips((prev) => [...prev, { id, type, message }]);
  }, []);

  const removeTip = useCallback((id) => {
    setTips((prev) => prev.filter((t) => t.id !== id));
  }, []);

  useEffect(() => {
    syncSettingsOnBoot();
    api.listFiles().then(setFiles).catch((e) => addTip('error', api.extractErrorMessage(e)));
    api.listEngines().then((data) => {
      setEngines(data);
      if (data.length > 0) setSelectedEngine(data[0].name);
    }).catch((e) => addTip('error', api.extractErrorMessage(e)));
  }, []);

  const handleUpload = async (fileList) => {
    try {
      const result = await api.uploadFiles(fileList);
      setFiles((prev) => [...result, ...prev]);
      addTip('success', `成功上传 ${result.length} 个文件`);
    } catch (e) {
      addTip('error', api.extractErrorMessage(e));
    }
  };

  const handleDelete = async (id) => {
    try {
      await api.deleteFile(id);
      setFiles((prev) => prev.filter((f) => f.id !== id));
      setSelectedIds((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    } catch (e) {
      addTip('error', api.extractErrorMessage(e));
    }
  };

  const handleGenerate = async () => {
    if (selectedIds.size === 0) {
      addTip('warning', '请先选择至少一个文件');
      return;
    }
    if (!selectedEngine) {
      addTip('warning', '请先选择生成引擎');
      return;
    }

    setGenerating(true);
    try {
      const result = await api.generateMindmap(Array.from(selectedIds), selectedEngine, params);
      setMindmapData(result);
      addTip('success', '思维导图生成成功');
    } catch (e) {
      addTip('error', api.extractErrorMessage(e));
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="h-screen flex bg-white">
      {/* Left Panel */}
      <div style={{ width: sidebarWidth }} className="flex-shrink-0 border-r border-gray-200 flex flex-col relative">
        {/* Header */}
        <div className="px-5 py-4 border-b border-gray-100">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <Brain size={22} className="text-gray-900" />
              <div>
                <h1 className="text-base font-semibold text-gray-900">Ultra MindMap</h1>
                <p className="text-xs text-gray-400">文本 → 思维导图</p>
              </div>
            </div>
            <button
              onClick={() => setSettingsOpen(true)}
              className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
            >
              <Settings size={16} />
            </button>
          </div>
        </div>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto px-5 py-4 flex flex-col gap-6">
          <FileLibrary
            files={files}
            selectedIds={selectedIds}
            onSelectChange={setSelectedIds}
            onUpload={handleUpload}
            onDelete={handleDelete}
          />

          {engines.length > 0 && (
            <>
              {/* Tab Bar */}
              <div className="flex border-b border-gray-200">
                <button
                  onClick={() => setActiveTab('generate')}
                  className={`px-4 py-2 text-xs font-medium transition-colors ${
                    activeTab === 'generate'
                      ? 'text-gray-900 border-b-2 border-gray-900'
                      : 'text-gray-400 hover:text-gray-600'
                  }`}
                >
                  生成
                </button>
                <button
                  onClick={() => setActiveTab('bench')}
                  className={`px-4 py-2 text-xs font-medium transition-colors ${
                    activeTab === 'bench'
                      ? 'text-gray-900 border-b-2 border-gray-900'
                      : 'text-gray-400 hover:text-gray-600'
                  }`}
                >
                  对比
                </button>
              </div>

              {activeTab === 'generate' ? (
                <EnginePanel
                  engines={engines}
                  selectedEngine={selectedEngine}
                  onEngineChange={setSelectedEngine}
                  params={params}
                  onParamsChange={setParams}
                />
              ) : (
                <BenchPanel
                  engines={engines}
                  selectedIds={selectedIds}
                  addTip={addTip}
                />
              )}
            </>
          )}
        </div>

        {/* Generate Button */}
        {activeTab === 'generate' && (
        <div className="px-5 py-4 border-t border-gray-100">
          <button
            onClick={handleGenerate}
            disabled={generating || selectedIds.size === 0}
            className={`
              w-full py-3 rounded-xl text-sm font-medium transition-all duration-200 flex items-center justify-center gap-2
              ${generating || selectedIds.size === 0
                ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                : 'bg-gray-900 text-white hover:bg-gray-800 shadow-sm hover:shadow-md active:scale-[0.98]'}
            `}
          >
            {generating ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                生成中...
              </>
            ) : (
              <>生成思维导图 {selectedIds.size > 0 && `(${selectedIds.size} 个文件)`}</>
            )}
          </button>
        </div>
        )}

        {/* Resize Handle */}
        <div
          onMouseDown={() => { dragging.current = true; document.body.style.cursor = 'col-resize'; document.body.style.userSelect = 'none'; }}
          className="absolute top-0 right-0 w-1 h-full cursor-col-resize hover:bg-gray-300 active:bg-gray-400 transition-colors z-10"
        />
      </div>

      {/* Right Panel - Mind Map */}
      <div className="flex-1 flex flex-col relative">
        <MindMapView data={mindmapData} />

        {/* Floating Tips */}
        <div className="absolute top-4 right-4 w-80 flex flex-col gap-2 z-50">
          {tips.map((tip) => (
            <TipCard key={tip.id} type={tip.type} message={tip.message} onClose={() => removeTip(tip.id)} />
          ))}
        </div>
      </div>

      <SettingsModal open={settingsOpen} onClose={() => setSettingsOpen(false)} addTip={addTip} />
    </div>
  );
}
