import { useEffect, useRef } from 'react';
import { Markmap } from 'markmap-view';
import gsap from 'gsap';

function toMarkmapData(node) {
  if (!node) return { content: '', children: [] };
  return {
    content: node.name || '',
    children: (node.children || []).map(toMarkmapData),
  };
}

export default function MindMapView({ data }) {
  const svgRef = useRef(null);
  const mmRef = useRef(null);
  const containerRef = useRef(null);

  useEffect(() => {
    if (!data || !svgRef.current) return;

    const markmapData = toMarkmapData(data);

    if (mmRef.current) {
      mmRef.current.setData(markmapData);
      mmRef.current.fit();
    } else {
      mmRef.current = Markmap.create(svgRef.current, {
        autoFit: true,
        duration: 300,
        paddingX: 16,
      }, markmapData);
    }

    gsap.fromTo(containerRef.current, { opacity: 0 }, { opacity: 1, duration: 0.5, ease: 'power2.out' });
  }, [data]);

  if (!data) {
    return (
      <div className="flex-1 flex items-center justify-center text-gray-400">
        <div className="text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gray-100 flex items-center justify-center">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <circle cx="12" cy="12" r="3" />
              <path d="M12 9V4M12 15v5M15 12h5M9 12H4" />
              <path d="M5.5 5.5l2.5 2.5M16 16l2.5 2.5M5.5 18.5l2.5-2.5M16 8l2.5-2.5" />
            </svg>
          </div>
          <p className="text-sm">选择文件并生成思维导图</p>
        </div>
      </div>
    );
  }

  return (
    <div ref={containerRef} className="markmap-container flex-1 relative">
      <svg ref={svgRef} className="w-full h-full" />
    </div>
  );
}
