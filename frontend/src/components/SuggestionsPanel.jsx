import React, { useState } from 'react';

export function SuggestionsPanel({ data, onApplySuggestion, onSwitchToDraft }) {
  const [selectedAlternatives, setSelectedAlternatives] = useState({});

  if (!data) {
    return (
      <div className="empty-panel">
        <div className="empty-icon">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 20h9"></path>
            <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path>
          </svg>
        </div>
        <h3>No Improvements Generated Yet</h3>
        <p>Click <strong>Review Improvements</strong> in the editor to identify redundancy reduction, transition variation, and structural cadence opportunities.</p>
      </div>
    );
  }

  const { suggestions, summary, preservation_guarantee } = data;

  const handleSelectAlternative = (suggestionId, altText) => {
    setSelectedAlternatives((prev) => ({
      ...prev,
      [suggestionId]: altText,
    }));
  };

  const getEffectiveSuggestion = (sug) => {
    return selectedAlternatives[sug.suggestion_id] || sug.suggested_text;
  };

  return (
    <div className="suggestions-panel">
      {/* Preservation & Ethics Banner */}
      <div className="preservation-card">
        <div className="preservation-header">
          <span className="preservation-title">Controlled Review Contract</span>
          <span className="suggestion-counter">{suggestions.length} Opportunity(ies)</span>
        </div>
        <p className="summary-text">{summary}</p>
        <div className="preservation-statement">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
          </svg>
          <span>{preservation_guarantee}</span>
        </div>
      </div>

      {/* Draft Preview Link */}
      {data.suggested_draft && (
        <div className="draft-banner">
          <div>
            <strong>Full Reconstructed Draft Preview Available</strong>
            <p>Compare the complete revised text side-by-side with your original passage.</p>
          </div>
          <button
            type="button"
            className="btn btn-sm btn-primary"
            onClick={onSwitchToDraft}
          >
            Compare Side-by-Side &rarr;
          </button>
        </div>
      )}

      {/* Suggestions List */}
      {suggestions.length === 0 ? (
        <div className="clean-state-box">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="20 6 9 17 4 12"></polyline>
          </svg>
          <div>
            <strong>Text is concise and well-paced</strong>
            <p>No immediate opportunities to reduce wordy phrasing or monotonous sentence structures were found.</p>
          </div>
        </div>
      ) : (
        <div className="suggestions-list">
          {suggestions.map((sug) => {
            const currentReplacement = getEffectiveSuggestion(sug);
            const pres = sug.preservation;
            const isPlaceholder = sug.suggested_text.startsWith('[Review:');

            return (
              <div key={sug.suggestion_id} className="suggestion-card">
                <div className="suggestion-header">
                  <div className="category-group">
                    <span className={`category-badge category-${sug.category}`}>
                      {sug.category}
                    </span>
                    <span className="sug-title">{sug.title}</span>
                  </div>

                  {/* Preservation Status Badge */}
                  <div className={`preservation-badge pres-${pres.status}`}>
                    {pres.status === 'verified' && (
                      <>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                          <polyline points="20 6 9 17 4 12"></polyline>
                        </svg>
                        <span>Preservation Verified</span>
                      </>
                    )}
                    {pres.status === 'warnings_detected' && (
                      <>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
                          <line x1="12" y1="9" x2="12" y2="13"></line>
                          <line x1="12" y1="17" x2="12.01" y2="17"></line>
                        </svg>
                        <span>Preservation Warning</span>
                      </>
                    )}
                    {pres.status === 'manual_review_required' && (
                      <>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <circle cx="12" cy="12" r="10"></circle>
                          <line x1="12" y1="16" x2="12" y2="12"></line>
                          <line x1="12" y1="8" x2="12.01" y2="8"></line>
                        </svg>
                        <span>Manual Review Required</span>
                      </>
                    )}
                  </div>
                </div>

                <p className="suggestion-explanation">{sug.explanation}</p>

                {/* Preservation details */}
                {pres.details && pres.details.length > 0 && (
                  <div className="preservation-details-box">
                    <span className="details-title">Preservation checks:</span>
                    <ul>
                      {pres.details.map((detail, idx) => (
                        <li key={idx} className={detail.startsWith('Warning:') ? 'text-warning' : 'text-verified'}>
                          {detail}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Diff Box: Original vs Suggested */}
                <div className="diff-comparison-box">
                  <div className="diff-col original-box">
                    <span className="diff-label">Original Text:</span>
                    <div className="diff-text original-highlight">
                      {sug.original_text}
                    </div>
                  </div>

                  <div className="diff-arrow">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <line x1="5" y1="12" x2="19" y2="12"></line>
                      <polyline points="12 5 19 12 12 19"></polyline>
                    </svg>
                  </div>

                  <div className="diff-col suggested-box">
                    <span className="diff-label">Proposed Edit:</span>
                    <div className="diff-text suggested-highlight">
                      {currentReplacement}
                    </div>
                  </div>
                </div>

                {/* Alternatives selector */}
                {sug.alternatives && sug.alternatives.length > 1 && (
                  <div className="alternatives-container">
                    <span className="alt-label">Select alternative phrasing:</span>
                    <div className="alt-pills">
                      {sug.alternatives.map((alt, idx) => (
                        <button
                          key={idx}
                          type="button"
                          className={`alt-pill ${currentReplacement === alt ? 'alt-pill-active' : ''}`}
                          onClick={() => handleSelectAlternative(sug.suggestion_id, alt)}
                        >
                          {alt}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Apply Button */}
                {!isPlaceholder && (
                  <div className="suggestion-action-row">
                    <button
                      type="button"
                      className="btn btn-sm btn-outline-success"
                      onClick={() => onApplySuggestion(sug, currentReplacement)}
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <polyline points="20 6 9 17 4 12"></polyline>
                      </svg>
                      <span>Apply this change to Editor</span>
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
