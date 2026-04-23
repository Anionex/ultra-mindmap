import { useState, useMemo } from 'react';
import { BarChart3, Loader2, ChevronDown } from 'lucide-react';
import { runBench, extractErrorMessage } from '../services/api';

const DIMENSIONS = [
  { key: 'coverage', label: '覆盖度' },
  { key: 'hierarchy', label: '层级' },
  { key: 'balance', label: '均衡' },
  { key: 'conciseness', label: '简洁' },
  { key: 'accuracy', label: '忠实' },
];

function CompactParams({ schema, params, onChange }) {
  const entries = Object.entries(schema);
  if (entries.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-x-3 gap-y-1.5 mt-1.5">
      {entries.map(([key, prop]) => {
        if (prop.enum) {
          return (
            <div key={key} className="flex items-center gap-1">
              <span className="text-[10px] text-gray-400">{prop.title || key}</span>
              <select
                value={params[key] ?? prop.default}
                onChange={(e) => onChange({ ...params, [key]: e.target.value })}
                className="px-1.5 py-0.5 text-[11px] bg-white border border-gray-200 rounded"
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
            <div key={key} className="flex items-center gap-1">
              <span className="text-[10px] text-gray-400">{prop.title || key}</span>
              <input
                type="number"
                step={prop.step ?? (prop.type === 'integer' ? 1 : 0.1)}
                value={params[key] ?? prop.default ?? 0}
                onChange={(e) => {
                  const v = prop.type === 'integer' ? parseInt(e.target.value) : parseFloat(e.target.value);
                  if (!isNaN(v)) onChange({ ...params, [key]: v });
                }}
                className="w-16 px-1.5 py-0.5 text-[11px] bg-white border border-gray-200 rounded font-mono"
              />
            </div>
          );
        }
        return null;
      })}
    </div>
  );
}

function EngineRow({ engines, label, selected, onSelect, params, onParamsChange }) {
  const engine = useMemo(() => engines.find((e) => e.name === selected), [engines, selected]);
  const schema = engine?.params_schema?.properties || {};

  return (
    <div className="p-3 bg-gray-50 rounded-lg">
      <div className="flex items-center gap-2">
        <span className="text-[10px] font-semibold text-gray-400 uppercase w-6 shrink-0">{label}</span>
        <select
          value={selected}
          onChange={(e) => {
            onSelect(e.target.value);
            const eng = engines.find((en) => en.name === e.target.value);
            const defaults = {};
            const props = eng?.params_schema?.properties || {};
            for (const [k, p] of Object.entries(props)) {
              if (p.default !== undefined) defaults[k] = p.default;
            }
            onParamsChange(defaults);
          }}
          className="flex-1 px-2 py-1.5 text-sm bg-white border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-300"
        >
          {engines.map((e) => (
            <option key={e.name} value={e.name}>{e.display_name}</option>
          ))}
        </select>
      </div>
      <CompactParams schema={schema} params={params} onChange={onParamsChange} />
    </div>
  );
}

function ScoreBar({ value, max = 5 }) {
  const pct = (value / max) * 100;
  return (
    <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden flex-1">
      <div
        className="h-full bg-gray-700 rounded-full transition-all duration-500"
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
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-3 py-2.5 flex items-center justify-between text-left hover:bg-gray-50 transition-colors"
      >
        <span className="text-xs font-medium text-gray-900 truncate mr-2">{result.filename}</span>
        <div className="flex items-center gap-2 shrink-0">
          <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${
            winner === 'A' ? 'bg-gray-900 text-white' :
            winner === 'B' ? 'bg-gray-200 text-gray-700' :
            'bg-gray-100 text-gray-500'
          }`}>
            {winner === 'A' ? nameA : winner === 'B' ? nameB : '平局'}
          </span>
          <ChevronDown size={12} className={`text-gray-400 transition-transform ${expanded ? 'rotate-180' : ''}`} />
        </div>
      </button>

      {expanded && (
        <div className="px-3 pb-3 border-t border-gray-100 space-y-2">
          {/* Column headers */}
          <div className="flex items-center gap-2 mt-2 text-[10px] font-medium text-gray-400 uppercase">
            <div className="w-10 shrink-0" />
            <div className="flex-1 text-center">{nameA}</div>
            <div className="flex-1 text-center">{nameB}</div>
          </div>

          {/* Dimension rows */}
          {DIMENSIONS.map((d) => {
            const a = result.score_a[d.key] || 0;
            const b = result.score_b[d.key] || 0;
            return (
              <div key={d.key} className="flex items-center gap-2">
                <div className="w-10 shrink-0 text-[10px] text-gray-400">{d.label}</div>
                <div className="flex-1 flex items-center gap-1.5">
                  <ScoreBar value={a} />
                  <span className="text-xs font-mono text-gray-700 w-3 text-right">{a}</span>
                </div>
                <div className="flex-1 flex items-center gap-1.5">
                  <ScoreBar value={b} />
                  <span className="text-xs font-mono text-gray-700 w-3 text-right">{b}</span>
                </div>
              </div>
            );
          })}

          {/* Total */}
          <div className="flex items-center gap-2 pt-1.5 border-t border-gray-100">
            <div className="w-10 shrink-0 text-[10px] font-medium text-gray-600">总分</div>
            <div className="flex-1 text-center text-xs font-mono font-bold text-gray-900">{sumA}/25</div>
            <div className="flex-1 text-center text-xs font-mono font-bold text-gray-900">{sumB}/25</div>
          </div>

          {/* Rationale */}
          {(result.score_a.rationale || result.score_b.rationale) && (
            <div className="pt-1.5 border-t border-gray-100 space-y-1">
              {result.score_a.rationale && (
                <p className="text-[10px] text-gray-400 leading-relaxed">
                  <span className="font-medium text-gray-500">{nameA}:</span> {result.score_a.rationale}
                </p>
              )}
              {result.score_b.rationale && (
                <p className="text-[10px] text-gray-400 leading-relaxed">
                  <span className="font-medium text-gray-500">{nameB}:</span> {result.score_b.rationale}
                </p>
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
    <div className="bg-gray-50 rounded-lg p-3 space-y-2.5">
      <div className="flex items-center justify-between">
        <p className="text-[10px] font-medium text-gray-400 uppercase tracking-wide">汇总 ({results.length} 文件)</p>
        <div className="flex gap-1.5 text-[10px]">
          <span className="px-1.5 py-0.5 bg-gray-900 text-white rounded">{nameA} {winsA}W</span>
          <span className="px-1.5 py-0.5 bg-gray-200 text-gray-700 rounded">{nameB} {winsB}W</span>
          {ties > 0 && <span className="px-1.5 py-0.5 bg-gray-100 text-gray-500 rounded">{ties}T</span>}
        </div>
      </div>

      {/* Avg scores */}
      <div className="space-y-1">
        {DIMENSIONS.map((d) => (
          <div key={d.key} className="flex items-center gap-2 text-[11px]">
            <span className="w-10 shrink-0 text-gray-400">{d.label}</span>
            <span className="w-7 text-right font-mono text-gray-700">{avg(d.key, 'score_a')}</span>
            <div className="flex-1 flex items-center gap-0.5">
              <div className="flex-1 h-1 bg-gray-200 rounded-full overflow-hidden">
                <div className="h-full bg-gray-700 rounded-full" style={{ width: `${(avg(d.key, 'score_a') / 5) * 100}%` }} />
              </div>
              <div className="flex-1 h-1 bg-gray-200 rounded-full overflow-hidden">
                <div className="h-full bg-gray-400 rounded-full" style={{ width: `${(avg(d.key, 'score_b') / 5) * 100}%` }} />
              </div>
            </div>
            <span className="w-7 text-left font-mono text-gray-500">{avg(d.key, 'score_b')}</span>
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
    <div className="flex flex-col gap-3">
      <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide flex items-center gap-2">
        <BarChart3 size={14} />
        引擎对比
      </h3>

      <div className="flex flex-col gap-2">
        <EngineRow
          engines={engines} label="A" selected={engineA}
          onSelect={setEngineA} params={paramsA} onParamsChange={setParamsA}
        />
        <div className="flex items-center gap-2 px-2">
          <div className="flex-1 border-t border-gray-200" />
          <span className="text-[10px] text-gray-300 uppercase">vs</span>
          <div className="flex-1 border-t border-gray-200" />
        </div>
        <EngineRow
          engines={engines} label="B" selected={engineB}
          onSelect={setEngineB} params={paramsB} onParamsChange={setParamsB}
        />
      </div>

      <div className="flex items-center gap-2">
        <label className="text-[10px] text-gray-400 uppercase tracking-wide">Judge</label>
        <select
          value={judgeModel}
          onChange={(e) => setJudgeModel(e.target.value)}
          className="flex-1 px-2 py-1.5 text-xs bg-white border border-gray-200 rounded-lg"
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
            : 'bg-gray-900 text-white hover:bg-gray-800 shadow-sm active:scale-[0.98]'}
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
        <div className="flex flex-col gap-2">
          <AggregateView results={results} engines={engines} />
          {results.map((r, i) => (
            <ResultCard key={i} result={r} engines={engines} />
          ))}
        </div>
      )}
    </div>
  );
}
