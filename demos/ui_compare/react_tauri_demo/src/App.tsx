import { useEffect, useRef, useState } from "react";

type StepItem = {
  id: number;
  label: string;
  done: boolean;
};

const steps: StepItem[] = [
  { id: 1, label: "Loop test completed", done: true },
  { id: 2, label: "Voltage inspection completed", done: true },
  { id: 3, label: "Phase sequence inspection in progress", done: false }
];

const logItems = [
  "14:09  Detected mismatch on PT1 secondary output.",
  "14:10  User opened PT1 blackbox.",
  "14:12  Step 3 measurements updated.",
  "14:13  Waiting for wiring correction."
];

const WAVEFORM_W = 700;
const WAVEFORM_H = 160;
const WAVEFORM_POINTS = 300;  // 横轴采样点数

const wavePhases = [
  { label: "A", offset: 0,             color: "#e05c5c" },
  { label: "B", offset: (2 * Math.PI) / 3, color: "#4caf8a" },
  { label: "C", offset: (4 * Math.PI) / 3, color: "#5b8fdf" },
];

function WaveformChart() {
  const [tick, setTick] = useState(0);
  const rafRef = useRef<number>(0);
  const lastRef = useRef<number>(0);

  useEffect(() => {
    const animate = (ts: number) => {
      if (lastRef.current) {
        const delta = ts - lastRef.current;
        setTick(t => t + delta * 0.003); // 控制波形滚动速度
      }
      lastRef.current = ts;
      rafRef.current = requestAnimationFrame(animate);
    };
    rafRef.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(rafRef.current);
  }, []);

  const cx = WAVEFORM_W;
  const cy = WAVEFORM_H / 2;
  const amp = WAVEFORM_H * 0.42;
  const freq = (2 * Math.PI) / WAVEFORM_POINTS * 3; // 显示约3个完整周期

  // 将采样点转为 SVG polyline points 字符串
  const buildPath = (phaseOffset: number) => {
    const pts: string[] = [];
    for (let i = 0; i <= WAVEFORM_POINTS; i++) {
      const x = (i / WAVEFORM_POINTS) * WAVEFORM_W;
      const y = cy - amp * Math.sin(freq * i - tick + phaseOffset);
      pts.push(`${x.toFixed(1)},${y.toFixed(1)}`);
    }
    return pts.join(" ");
  };

  // 纵轴刻度
  const gridLines = [-1, -0.5, 0, 0.5, 1];

  return (
    <div className="waveform-wrap">
      <svg width="100%" viewBox={`0 0 ${WAVEFORM_W} ${WAVEFORM_H}`} preserveAspectRatio="none"
        style={{ display: "block" }}>
        {/* 网格线 */}
        {gridLines.map(v => {
          const y = cy - v * amp;
          return (
            <line key={v} x1={0} y1={y} x2={WAVEFORM_W} y2={y}
              stroke={v === 0 ? "#bdb2a4" : "#e2d9ca"}
              strokeWidth={v === 0 ? 1 : 0.6}
              strokeDasharray={v === 0 ? "none" : "4 4"} />
          );
        })}
        {/* 三相波形 */}
        {wavePhases.map(({ label, offset, color }) => (
          <polyline key={label}
            points={buildPath(offset)}
            fill="none"
            stroke={color}
            strokeWidth={2}
            strokeLinejoin="round"
          />
        ))}
      </svg>
      {/* 图例 */}
      <div className="phasor-legend" style={{ marginTop: 10 }}>
        {wavePhases.map(({ label, color }) => (
          <span key={label} className="legend-item">
            <span className="legend-dot" style={{ background: color }} />
            Phase {label}
          </span>
        ))}
      </div>
    </div>
  );
}

// 相量图：三相 A/B/C + 参考相量，带动画旋转
function PhasorDiagram() {
  const [angle, setAngle] = useState(0);
  const rafRef = useRef<number>(0);
  const lastRef = useRef<number>(0);

  useEffect(() => {
    const animate = (ts: number) => {
      if (lastRef.current) {
        const delta = ts - lastRef.current;
        // 50 Hz → 360°/20ms，这里慢一点方便观察，用 0.05°/ms
        setAngle(a => (a + delta * 0.05) % 360);
      }
      lastRef.current = ts;
      rafRef.current = requestAnimationFrame(animate);
    };
    rafRef.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(rafRef.current);
  }, []);

  const cx = 130, cy = 130, r = 100;
  const deg2rad = (d: number) => (d * Math.PI) / 180;

  // 三相偏移 0° / -120° / -240°
  const phases = [
    { label: "A", offset: 0,    color: "#e05c5c" },
    { label: "B", offset: -120, color: "#4caf8a" },
    { label: "C", offset: -240, color: "#5b8fdf" },
  ];

  return (
    <div className="phasor-wrap">
      <svg width={260} height={260} viewBox="0 0 260 260">
        {/* 背景圆 */}
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="#e2d9ca" strokeWidth={1} />
        <circle cx={cx} cy={cy} r={r * 0.5} fill="none" stroke="#e2d9ca" strokeWidth={0.5} strokeDasharray="4 4" />
        {/* 十字基准线 */}
        <line x1={cx - r - 10} y1={cy} x2={cx + r + 10} y2={cy} stroke="#ccc" strokeWidth={0.8} />
        <line x1={cx} y1={cy - r - 10} x2={cx} y2={cy + r + 10} stroke="#ccc" strokeWidth={0.8} />

        {phases.map(({ label, offset, color }) => {
          const rad = deg2rad(angle + offset);
          const x = cx + r * Math.cos(rad);
          const y = cy - r * Math.sin(rad);  // SVG y轴向下，取反
          const tx = cx + (r + 16) * Math.cos(rad);
          const ty = cy - (r + 16) * Math.sin(rad);
          return (
            <g key={label}>
              {/* 相量箭头主体 */}
              <line
                x1={cx} y1={cy} x2={x} y2={y}
                stroke={color} strokeWidth={2.5} strokeLinecap="round"
              />
              {/* 箭头头部（小三角） */}
              <circle cx={x} cy={y} r={3.5} fill={color} />
              {/* 标签 */}
              <text x={tx} y={ty} fill={color} fontSize={13} fontWeight="700"
                textAnchor="middle" dominantBaseline="middle">
                {label}
              </text>
            </g>
          );
        })}

        {/* 圆心点 */}
        <circle cx={cx} cy={cy} r={4} fill="#1f2a31" />
      </svg>

      {/* 图例 */}
      <div className="phasor-legend">
        {phases.map(({ label, color }) => (
          <span key={label} className="legend-item">
            <span className="legend-dot" style={{ background: color }} />
            Phase {label}
          </span>
        ))}
      </div>
    </div>
  );
}

function App() {
  return (
    <main className="shell">
      <header className="hero">
        <div>
          <p className="eyebrow">React + Tauri demo</p>
          <h1>Three-Phase Training Console</h1>
          <p className="subcopy">
            A simple web-style desktop UI with cards, pills and a compact activity feed.
          </p>
        </div>
        <div className="pill">Engineering Mode</div>
      </header>

      <section className="grid">
        <article className="card">
          <h2>Session Snapshot</h2>
          <p className="muted">Current scene and quick metrics.</p>
          <div className="metrics">
            <div>
              <strong>E12</strong>
              <span>fault scene</span>
            </div>
            <div>
              <strong>3 / 5</strong>
              <span>step</span>
            </div>
            <div>
              <strong>02:18</strong>
              <span>elapsed</span>
            </div>
          </div>
        </article>

        <article className="card">
          <h2>Step Progress</h2>
          <p className="muted">The same content as the PyQt demo, rendered with CSS layout.</p>
          <div className="step-list">
            {steps.map((step) => (
              <div className="step-row" key={step.id}>
                <span className={`step-badge ${step.done ? "done" : "open"}`}>{step.id}</span>
                <span>{step.label}</span>
                <span className="step-state">{step.done ? "Done" : "Open"}</span>
              </div>
            ))}
          </div>
        </article>

        {/* 波形图卡片，占满整行 */}
        <article className="card card-full">
          <h2>Waveform</h2>
          <p className="muted">三相正弦波实时滚动（A/B/C 各差 120°）</p>
          <WaveformChart />
        </article>

        {/* 相量图卡片，占满整行 */}
        <article className="card card-full">
          <h2>Phasor Diagram</h2>
          <p className="muted">三相相量实时旋转（对比 PyQt5 QPainter 版本）</p>
          <PhasorDiagram />
        </article>

        <article className="card">
          <h2>Actions</h2>
          <p className="muted">This version is easier to extend with animated cards and responsive layout.</p>
          <div className="actions">
            <button className="primary">Open Blackbox</button>
            <button className="secondary">Generate Report</button>
          </div>
        </article>

        <article className="card">
          <h2>Event Log</h2>
          <p className="muted">A lightweight activity feed.</p>
          <ul className="log-list">
            {logItems.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </article>
      </section>
    </main>
  );
}

export default App;
