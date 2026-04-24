import { useState, useEffect, useMemo } from 'react';
import { ChevronDown, Settings } from 'lucide-react';

function ParamField({ name, schema, value, onChange }) {
  if (schema.enum) {
    return (
      <div className="flex flex-col gap-1.5">
        <label className="text-xs font-medium text-gray-600">{schema.title || name}</label>
        <select
          value={value ?? schema.default}
          onChange={(e) => onChange(e.target.value)}
          className="w-full px-3 py-2 text-sm bg-white border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-300 appearance-none"
        >
          {schema.enum.map((opt) => (
            <option key={opt} value={opt}>{opt}</option>
          ))}
        </select>
      </div>
    );
  }

  if (schema.type === 'string' && !schema.enum) {
    return (
      <div className="flex flex-col gap-1.5">
        <label className="text-xs font-medium text-gray-600">{schema.title || name}</label>
        <input
          type="text"
          value={value ?? schema.default ?? ''}
          onChange={(e) => onChange(e.target.value)}
          className="w-full px-3 py-2 text-sm bg-white border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-300 font-mono"
        />
      </div>
    );
  }

  if (schema.type === 'number' || schema.type === 'integer') {
    const step = schema.step ?? (schema.type === 'integer' ? 1 : 0.1);
    const current = value ?? schema.default ?? 0;

    return (
      <div className="flex flex-col gap-1.5">
        <label className="text-xs font-medium text-gray-600">{schema.title || name}</label>
        <input
          type="number"
          step={step}
          value={current}
          onChange={(e) => {
            const raw = e.target.value;
            if (raw === '') return;
            const v = schema.type === 'integer' ? parseInt(raw) : parseFloat(raw);
            if (!isNaN(v)) onChange(v);
          }}
          className="w-full px-3 py-2 text-sm bg-white border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-300 font-mono"
        />
      </div>
    );
  }

  return null;
}

export default function EnginePanel({ engines, selectedEngine, onEngineChange, params, onParamsChange }) {
  const engine = useMemo(() => engines.find((e) => e.name === selectedEngine), [engines, selectedEngine]);
  const schema = engine?.params_schema?.properties || {};

  useEffect(() => {
    if (engine && Object.keys(params).length === 0) {
      const defaults = {};
      for (const [key, prop] of Object.entries(schema)) {
        if (prop.default !== undefined) defaults[key] = prop.default;
      }
      onParamsChange(defaults);
    }
  }, [selectedEngine]);

  return (
    <div className="flex flex-col gap-3">
      <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide flex items-center gap-2">
        <Settings size={14} />
        生成引擎
      </h3>

      <div className="flex flex-col gap-1">
        {engines.map((e) => (
          <button
            key={e.name}
            onClick={() => {
              onEngineChange(e.name);
              const defaults = {};
              const props = e.params_schema?.properties || {};
              for (const [key, prop] of Object.entries(props)) {
                if (prop.default !== undefined) defaults[key] = prop.default;
              }
              onParamsChange(defaults);
            }}
            className={`
              w-full text-left px-3 py-2.5 rounded-lg text-sm transition-all duration-150
              ${selectedEngine === e.name
                ? 'bg-gray-900 text-white shadow-sm'
                : 'text-gray-700 hover:bg-gray-100'}
            `}
          >
            <div className="font-medium">{e.display_name}</div>
            <div className={`text-xs mt-0.5 ${selectedEngine === e.name ? 'text-gray-300' : 'text-gray-400'}`}>
              {e.description}
            </div>
          </button>
        ))}
      </div>

      {engine && Object.keys(schema).length > 0 && (
        <div className="flex flex-col gap-4 p-3 bg-gray-50 rounded-xl">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">参数配置</p>
          {Object.entries(schema).map(([key, propSchema]) => (
            <ParamField
              key={key}
              name={key}
              schema={propSchema}
              value={params[key]}
              onChange={(v) => onParamsChange({ ...params, [key]: v })}
            />
          ))}
        </div>
      )}
    </div>
  );
}
