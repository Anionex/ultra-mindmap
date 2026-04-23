import { useEffect, useRef } from 'react';
import { X, Info, CheckCircle, AlertTriangle, XCircle } from 'lucide-react';
import gsap from 'gsap';

const VARIANTS = {
  info: { border: 'border-l-blue-500', bg: 'bg-blue-50', text: 'text-blue-800', Icon: Info },
  success: { border: 'border-l-green-500', bg: 'bg-green-50', text: 'text-green-800', Icon: CheckCircle },
  warning: { border: 'border-l-yellow-500', bg: 'bg-yellow-50', text: 'text-yellow-800', Icon: AlertTriangle },
  error: { border: 'border-l-red-500', bg: 'bg-red-50', text: 'text-red-800', Icon: XCircle },
};

export default function TipCard({ type = 'info', message, onClose }) {
  const ref = useRef(null);
  const v = VARIANTS[type] || VARIANTS.info;

  useEffect(() => {
    gsap.fromTo(ref.current, { opacity: 0, y: -12 }, { opacity: 1, y: 0, duration: 0.3, ease: 'power2.out' });
    if (type !== 'error') {
      const timer = setTimeout(() => {
        gsap.to(ref.current, {
          opacity: 0, y: -12, duration: 0.25,
          onComplete: () => onClose?.(),
        });
      }, 4000);
      return () => clearTimeout(timer);
    }
  }, []);

  return (
    <div ref={ref} className={`flex items-start gap-3 p-3 rounded-lg border-l-4 ${v.border} ${v.bg} shadow-sm`}>
      <v.Icon size={18} className={`${v.text} mt-0.5 flex-shrink-0`} />
      <p className={`text-sm ${v.text} flex-1`}>{message}</p>
      <button onClick={onClose} className="text-gray-400 hover:text-gray-600 flex-shrink-0">
        <X size={14} />
      </button>
    </div>
  );
}
