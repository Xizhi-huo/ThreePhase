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
