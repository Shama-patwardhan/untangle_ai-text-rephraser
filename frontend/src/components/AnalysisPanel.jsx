import React from 'react';

export function AnalysisPanel({ data, onSwitchToImprove }) {
  if (!data) {
    return (
      <div className="empty-panel">
        <div className="empty-icon">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <line x1="18" y1="20" x2="18" y2="10"></line>
            <line x1="12" y1="20" x2="12" y2="4"></line>
            <line x1="6" y1="20" x2="6" y2="14"></line>
          </svg>
        </div>
        <h3>No Analysis Run Yet</h3>
        <p>Enter or paste text into the editor and click <strong>Analyze Text</strong> to inspect structural statistics and observable writing patterns.</p>
      </div>
    );
  }

  const { statistics, findings, summary, disclaimer } = data;
  const distribution = statistics.sentence_length_distribution || {};
  const maxBinCount = Math.max(1, ...Object.values(distribution));

  return (
    <div className="analysis-panel">
      {/* Summary Banner */}
      <div className="summary-card">
        <div className="summary-header">
          <span className="summary-badge">Summary</span>
          <span className="analysis-id">ID: {data.analysis_id}</span>
        </div>
        <p className="summary-text">{summary}</p>
        <div className="disclaimer-callout">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="16" x2="12" y2="12"></line>
            <line x1="12" y1="8" x2="12.01" y2="8"></line>
          </svg>
          <span>{disclaimer}</span>
        </div>
      </div>

      {/* Key Statistics Grid */}
      <div className="stats-grid">
        <div className="stat-card">
          <span className="stat-label">Words</span>
          <span className="stat-value">{statistics.word_count.toLocaleString()}</span>
          <span className="stat-sub">{statistics.character_count.toLocaleString()} characters</span>
        </div>

        <div className="stat-card">
          <span className="stat-label">Sentences</span>
          <span className="stat-value">{statistics.sentence_count}</span>
          <span className="stat-sub">{statistics.paragraph_count} paragraph(s)</span>
        </div>

        <div className="stat-card">
          <span className="stat-label">Mean Sentence Length</span>
          <span className="stat-value">{statistics.avg_sentence_length.toFixed(1)}</span>
          <span className="stat-sub">words / sentence</span>
        </div>

        <div className="stat-card">
          <span className="stat-label">Length Std. Dev.</span>
          <span className="stat-value">{statistics.sentence_length_std_dev.toFixed(2)}</span>
          <span className="stat-sub">Sample s (Bessel's n-1)</span>
        </div>
      </div>

      {/* Sentence Length Distribution */}
      <div className="card distribution-card">
        <div className="card-header">
          <h4>Sentence Length Cadence Distribution</h4>
          <span className="card-subtext">Word count intervals across sentences</span>
        </div>
        <div className="distribution-bars">
          {Object.entries(distribution).map(([bin, count]) => {
            const percentage = (count / maxBinCount) * 100;
            return (
              <div key={bin} className="distribution-row">
                <span className="bin-label">{bin} words</span>
                <div className="bar-track">
                  <div
                    className="bar-fill"
                    style={{ width: `${percentage}%` }}
                    title={`${count} sentence(s)`}
                  ></div>
                </div>
                <span className="bin-count">{count}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Observable Findings List */}
      <div className="findings-section">
        <div className="section-header-row">
          <h4>Observable Stylistic Patterns ({findings.length})</h4>
          {findings.length > 0 && (
            <button
              type="button"
              className="btn btn-sm btn-outline"
              onClick={onSwitchToImprove}
            >
              Review Suggestions &rarr;
            </button>
          )}
        </div>

        {findings.length === 0 ? (
          <div className="clean-state-box">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
              <polyline points="22 4 12 14.01 9 11.01"></polyline>
            </svg>
            <div>
              <strong>No problematic patterns detected</strong>
              <p>Sentence cadence exhibits natural variance and no excessive verbatim repetition was identified.</p>
            </div>
          </div>
        ) : (
          <div className="findings-list">
            {findings.map((f, i) => (
              <div key={`${f.rule_id}-${i}`} className={`finding-card severity-${f.severity}`}>
                <div className="finding-header">
                  <div className="finding-title-group">
                    <span className="finding-title">{f.title}</span>
                    <span className="rule-code">{f.rule_id}</span>
                  </div>
                  <span className={`severity-badge badge-${f.severity}`}>
                    {f.severity}
                  </span>
                </div>
                <p className="finding-explanation">{f.explanation}</p>

                {f.span && (
                  <div className="finding-span">
                    <span className="span-label">Sample span:</span>
                    <span className="span-text">&ldquo;{f.span.text}&rdquo;</span>
                  </div>
                )}

                <div className="evidence-tags">
                  {Object.entries(f.evidence).map(([key, val]) => (
                    <span key={key} className="evidence-tag">
                      {key.replace(/_/g, ' ')}: <strong>{String(val)}</strong>
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Repeated Phrases & Words */}
      {statistics.repeated_phrases && statistics.repeated_phrases.length > 0 && (
        <div className="card phrase-card">
          <div className="card-header">
            <h4>Repeated Multiword Phrases ({statistics.repeated_phrases.length})</h4>
          </div>
          <div className="chip-list">
            {statistics.repeated_phrases.map((rp, i) => (
              <span key={i} className="chip chip-phrase">
                &ldquo;{rp.phrase}&rdquo; <span className="chip-badge">{rp.count}x</span>
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
