import React from 'react';

export function Header({ backendHealth, onSelectSample, onClear }) {
  const isOnline = backendHealth && backendHealth.status === 'ok';

  return (
    <header className="header">
      <div className="header-brand">
        <div className="brand-logo">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
          </svg>
        </div>
        <div>
          <h1 className="brand-title">Untangle</h1>
          <p className="brand-tagline">Explainable Writing Analysis &amp; Controlled Reconstruction</p>
        </div>
      </div>

      <div className="header-actions">
        <div className={`status-pill ${isOnline ? 'status-online' : 'status-offline'}`}>
          <span className="status-dot"></span>
          <span>{isOnline ? `Backend v${backendHealth.version || '0.1.0'}` : 'Backend Offline'}</span>
        </div>

        <div className="sample-buttons">
          <span className="sample-label">Load sample:</span>
          <button
            type="button"
            className="btn btn-sm btn-ghost"
            onClick={() => onSelectSample('repetitive_transitions')}
          >
            Repetitive Cadence
          </button>
          <button
            type="button"
            className="btn btn-sm btn-ghost"
            onClick={() => onSelectSample('wordy_technical')}
          >
            Wordy Technical
          </button>
          <button
            type="button"
            className="btn btn-sm btn-ghost"
            onClick={() => onSelectSample('clean_academic')}
          >
            Clean Academic
          </button>
          <button
            type="button"
            className="btn btn-sm btn-ghost btn-danger-ghost"
            onClick={onClear}
            title="Clear editor text"
          >
            Clear
          </button>
        </div>
      </div>
    </header>
  );
}
