import { useState, useEffect, useCallback } from 'react';
import { Brain, Loader2 } from 'lucide-react';
import FileLibrary from './components/FileLibrary';
import EnginePanel from './components/EnginePanel';
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

  const addTip = useCallback((type, message) => {
    const id = ++tipId;
    setTips((prev) => [...prev, { id, type, message }]);
  }, []);

  const removeTip = useCallback((id) => {
    setTips((prev) => prev.filter((t) => t.id !== id));
  }, []);

  useEffect(() => {
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
      <div className="w-[360px] flex-shrink-0 border-r border-gray-200 flex flex-col">
        {/* Header */}
        <div className="px-5 py-4 border-b border-gray-100">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 bg-gray-900 rounded-lg flex items-center justify-center">
              <Brain size={18} className="text-white" />
            </div>
            <div>
              <h1 className="text-base font-semibold text-gray-900">Ultra MindMap</h1>
              <p className="text-xs text-gray-400">文本 → 思维导图</p>
            </div>
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
            <EnginePanel
              engines={engines}
              selectedEngine={selectedEngine}
              onEngineChange={setSelectedEngine}
              params={params}
              onParamsChange={setParams}
            />
          )}
        </div>

        {/* Generate Button */}
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
    </div>
  );
}
