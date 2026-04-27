import { useEffect, useRef } from 'react';
import { Transformer } from 'markmap-lib';
import { Markmap } from 'markmap-view';
import { Network } from 'lucide-react';
import gsap from 'gsap';

const transformer = new Transformer();

function treeToMarkdown(node, depth = 1) {
  if (!node) return '';
  const lines = [];
  if (node.name) lines.push(`${'#'.repeat(depth)} ${node.name}`);
  (node.children || []).forEach((child) => {
    const childMarkdown = treeToMarkdown(child, depth + 1);
    if (childMarkdown) lines.push(childMarkdown);
  });
  return lines.join('\n');
}

function getMarkdown(data) {
  if (!data) return '';
  if (typeof data.markdown === 'string' && data.markdown.trim()) {
    return data.markdown.trim();
  }
  return treeToMarkdown(data).trim();
}

export default function MindMapView({ data }) {
  const svgRef = useRef(null);
  const mmRef = useRef(null);
  const containerRef = useRef(null);

  useEffect(() => {
    if (!data || !svgRef.current) return;

    const markdown = getMarkdown(data);
    const { root } = transformer.transform(markdown);

    if (mmRef.current) {
      mmRef.current.setData(root);
      mmRef.current.fit();
    } else {
      mmRef.current = Markmap.create(svgRef.current, {
        autoFit: true,
        duration: 300,
        paddingX: 16,
      }, root);
    }

    gsap.fromTo(containerRef.current, { opacity: 0 }, { opacity: 1, duration: 0.5, ease: 'power2.out' });
  }, [data]);

  if (!data) {
    return (
      <div className="flex-1 flex items-center justify-center text-gray-400">
        <div className="text-center">
          <Network size={36} className="mx-auto mb-4 text-gray-300" />
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
