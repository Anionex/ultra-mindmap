import { useState, useMemo } from 'react';
import { BarChart3, Loader2, ChevronDown } from 'lucide-react';
import { runBench, extractErrorMessage } from '../services/api';

const DIMENSIONS = [
  { key: 'coverage', label: '全文覆盖' },
  { key: 'hierarchy', label: '层级合理性' },
  { key: 'balance', label: '分支均衡' },
  { key: 'conciseness', label: '简洁性' },
  { key: 'accuracy', label: '忠实度' },
];

function EngineSelector({ engines, label, selected, onSelect, params, onParamsChange }) {
  const engine = useMemo(() => engines.find((e) => e.name === selected), [engines, selected]);
  const schema = engine?.params_schema?.properties || {};

  return (
    <div className="flex flex-col gap-2">
      <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</label>
      <select
        value={selected}
        onChange={(e) => {
          onSelect(e.target.value);
          const eng = engines.find((en) => en.name === e.target.value);
          const defaults = {};
          const props = eng?.params_schema?.properties || {};
          for (const [key, prop] of Object.entries(props)) {
            if (prop.default !== undefined) defaults[key] = prop.default;
          }
          onParamsChange(defaults);
        }}
        className="w-full px-3 py-2 text-sm bg-white border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-300"
      >
        {engines.map((e) => (
          <option key={e.name} value={e.name}>{e.display_name}</option>
        ))}
      </select>
      {Object.keys(schema).length > 0 && (
        <div className="flex flex-col gap-2 mt-1">
          {Object.entries(schema).map(([key, prop]) => {
            if (prop.enum) {
              return (
                <div key={key} className="flex items-center gap-2">
                  <label className="text-xs text-gray-500 min-w-[60px]">{prop.title || key}</label>
                  <select
                    value={params[key] ?? prop.default}
                    onChange={(e) => onParamsChange({ ...params, [key]: e.target.value })}
                    className="flex-1 px-2 py-1 text-xs bg-white border border-gray-200 rounded"
                  >
                    {prop.enum.map((opt) => (
                      <option key={opt} value={opt}>{opt}</option>
                    ))}
                  </select>
                </div>
              );
            }
            if (prop.type === 'number' || prop.type === 'integer') {
              return (
                <div key={key} className="flex items-center gap-2">
                  <label className="text-xs text-gray-500 min-w-[60px]">{prop.title || key}</label>
                  <input
                    type="number"
                    step={prop.step ?? (prop.type === 'integer' ? 1 : 0.1)}
                    value={params[key] ?? prop.default ?? 0}
                    onChange={(e) => {
                      const v = prop.type === 'integer' ? parseInt(e.target.value) : parseFloat(e.target.value);
                      if (!isNaN(v)) onParamsChange({ ...params, [key]: v });
                    }}
                    className="flex-1 px-2 py-1 text-xs bg-white border border-gray-200 rounded font-mono"
                  />
                </div>
              );
            }
            return null;
          })}
        </div>
      )}
    </div>
  );
}

function ScoreBar({ value, max = 5 }) {
  const pct = (value / max) * 100;
  return (
    <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
      <div
        className="h-full bg-gray-800 rounded-full transition-all duration-500"
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

function ResultCard({ result, engines }) {
  const [expanded, setExpanded] = useState(false);
  const nameA = engines.find((e) => e.name === result.engine_a)?.display_name || result.engine_a;
  const nameB = engines.find((e) => e.name === result.engine_b)?.display_name || result.engine_b;
  const sumA = DIMENSIONS.reduce((s, d) => s + (result.score_a[d.key] || 0), 0);
  const sumB = DIMENSIONS.reduce((s, d) => s + (result.score_b[d.key] || 0), 0);
  const winner = sumA > sumB ? 'A' : sumB > sumA ? 'B' : 'tie';

  return (
    <div className="border border-gray-200 rounded-xl overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-3 flex items-center justify-between text-left hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-3 min-w-0">
          <span className="text-sm font-medium text-gray-900 truncate">{result.filename}</span>
          <span className="text-xs text-gray-400 shrink-0">{result.elapsed_s}s</span>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
            winner === 'A' ? 'bg-gray-900 text-white' :
            winner === 'B' ? 'bg-gray-200 text-gray-700' :
            'bg-gray-100 text-gray-500'
          }`}>
            {winner === 'A' ? nameA : winner === 'B' ? nameB : '平局'}
            {winner !== 'tie' && ` +${Math.abs(sumA - sumB)}`}
          </span>
          <ChevronDown size={14} className={`text-gray-400 transition-transform ${expanded ? 'rotate-180' : ''}`} />
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-4 border-t border-gray-100">
          <div className="grid grid-cols-[1fr_auto_auto] gap-x-4 gap-y-2 mt-3">
            <div className="text-xs text-gray-400" />
            <div className="text-xs font-medium text-gray-600 text-center min-w-[60px]">{nameA}</div>
            <div className="text-xs font-medium text-gray-600 text-center min-w-[60px]">{nameB}</div>
            {DIMENSIONS.map((d) => {
              const a = result.score_a[d.key] || 0;
              const b = result.score_b[d.key] || 0;
              return (
                <div key={d.key} className="contents">
                  <div className="text-xs text-gray-500 py-1">{d.label}</div>
                  <div className="text-center">
                    <div className="text-sm font-mono font-medium text-gray-900">{a}</div>
                    <ScoreBar value={a} />
                  </div>
                  <div className="text-center">
                    <div className="text-sm font-mono font-medium text-gray-900">{b}</div>
                    <ScoreBar value={b} />
                  </div>
                </div>
              );
            })}
            <div className="contents">
              <div className="text-xs font-medium text-gray-700 py-1 border-t border-gray-100 pt-2">总分</div>
              <div className="text-center border-t border-gray-100 pt-2">
                <div className="text-sm font-mono font-bold text-gray-900">{sumA}/25</div>
              </div>
              <div className="text-center border-t border-gray-100 pt-2">
                <div className="text-sm font-mono font-bold text-gray-900">{sumB}/25</div>
              </div>
            </div>
          </div>

          {(result.score_a.rationale || result.score_b.rationale) && (
            <div className="mt-3 space-y-2">
              {result.score_a.rationale && (
                <div className="text-xs text-gray-500">
                  <span className="font-medium">{nameA}:</span> {result.score_a.rationale}
                </div>
              )}
              {result.score_b.rationale && (
                <div className="text-xs text-gray-500">
                  <span className="font-medium">{nameB}:</span> {result.score_b.rationale}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function AggregateView({ results, engines }) {
  if (!results || results.length === 0) return null;

  const nameA = engines.find((e) => e.name === results[0].engine_a)?.display_name || results[0].engine_a;
  const nameB = engines.find((e) => e.name === results[0].engine_b)?.display_name || results[0].engine_b;

  const avg = (key, side) => {
    const vals = results.map((r) => r[side][key] || 0);
    return (vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(1);
  };

  const winsA = results.filter((r) => {
    const a = DIMENSIONS.reduce((s, d) => s + (r.score_a[d.key] || 0), 0);
    const b = DIMENSIONS.reduce((s, d) => s + (r.score_b[d.key] || 0), 0);
    return a > b;
  }).length;
  const winsB = results.filter((r) => {
    const a = DIMENSIONS.reduce((s, d) => s + (r.score_a[d.key] || 0), 0);
    const b = DIMENSIONS.reduce((s, d) => s + (r.score_b[d.key] || 0), 0);
    return b > a;
  }).length;
  const ties = results.length - winsA - winsB;

  return (
    <div className="bg-gray-50 rounded-xl p-4 space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">汇总 ({results.length} 个文件)</p>
        <div className="flex gap-2 text-xs">
          <span className="px-2 py-0.5 bg-gray-900 text-white rounded-full">{nameA} {winsA}胜</span>
          <span className="px-2 py-0.5 bg-gray-200 text-gray-700 rounded-full">{nameB} {winsB}胜</span>
          {ties > 0 && <span className="px-2 py-0.5 bg-gray-100 text-gray-500 rounded-full">{ties}平</span>}
        </div>
      </div>
      <div className="grid grid-cols-[1fr_auto_auto] gap-x-4 gap-y-1.5">
        <div className="text-xs text-gray-400" />
        <div className="text-xs font-medium text-gray-600 text-center min-w-[50px]">{nameA}</div>
        <div className="text-xs font-medium text-gray-600 text-center min-w-[50px]">{nameB}</div>
        {DIMENSIONS.map((d) => (
          <div key={d.key} className="contents">
            <div className="text-xs text-gray-500">{d.label}</div>
            <div className="text-xs font-mono text-center text-gray-900">{avg(d.key, 'score_a')}</div>
            <div className="text-xs font-mono text-center text-gray-900">{avg(d.key, 'score_b')}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function BenchPanel({ engines, selectedIds, addTip }) {
  const [engineA, setEngineA] = useState(engines[0]?.name || '');
  const [paramsA, setParamsA] = useState(() => {
    const defaults = {};
    const props = engines[0]?.params_schema?.properties || {};
    for (const [key, prop] of Object.entries(props)) {
      if (prop.default !== undefined) defaults[key] = prop.default;
    }
    return defaults;
  });
  const [engineB, setEngineB] = useState(engines[1]?.name || engines[0]?.name || '');
  const [paramsB, setParamsB] = useState(() => {
    const eng = engines[1] || engines[0];
    const defaults = {};
    const props = eng?.params_schema?.properties || {};
    for (const [key, prop] of Object.entries(props)) {
      if (prop.default !== undefined) defaults[key] = prop.default;
    }
    return defaults;
  });
  const [judgeModel, setJudgeModel] = useState('gpt-4o');
  const [running, setRunning] = useState(false);
  const [results, setResults] = useState(null);

  const handleRun = async () => {
    if (selectedIds.size === 0) {
      addTip('warning', '请先选择至少一个文件');
      return;
    }
    setRunning(true);
    try {
      const data = await runBench(
        Array.from(selectedIds), engineA, paramsA, engineB, paramsB, judgeModel
      );
      setResults(data);
      addTip('success', `Bench 完成：${data.length} 个文件已评测`);
    } catch (e) {
      addTip('error', extractErrorMessage(e));
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-2">
        <BarChart3 size={14} className="text-gray-600" />
        <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">引擎对比</h3>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <EngineSelector
          engines={engines}
          label="引擎 A"
          selected={engineA}
          onSelect={setEngineA}
          params={paramsA}
          onParamsChange={setParamsA}
        />
        <EngineSelector
          engines={engines}
          label="引擎 B"
          selected={engineB}
          onSelect={setEngineB}
          params={paramsB}
          onParamsChange={setParamsB}
        />
      </div>

      <div className="flex items-center gap-2">
        <label className="text-xs text-gray-500">评审模型</label>
        <select
          value={judgeModel}
          onChange={(e) => setJudgeModel(e.target.value)}
          className="flex-1 px-2 py-1 text-xs bg-white border border-gray-200 rounded"
        >
          <option value="gpt-4o">gpt-4o</option>
          <option value="gpt-4o-mini">gpt-4o-mini</option>
        </select>
      </div>

      <button
        onClick={handleRun}
        disabled={running || selectedIds.size === 0}
        className={`
          w-full py-2.5 rounded-xl text-sm font-medium transition-all duration-200 flex items-center justify-center gap-2
          ${running || selectedIds.size === 0
            ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
            : 'bg-gray-900 text-white hover:bg-gray-800 shadow-sm'}
        `}
      >
        {running ? (
          <>
            <Loader2 size={14} className="animate-spin" />
            评测中...
          </>
        ) : (
          <>运行 Bench {selectedIds.size > 0 && `(${selectedIds.size} 个文件)`}</>
        )}
      </button>

      {results && (
        <div className="flex flex-col gap-3">
          <AggregateView results={results} engines={engines} />
          {results.map((r, i) => (
            <ResultCard key={i} result={r} engines={engines} />
          ))}
        </div>
      )}
    </div>
  );
}
