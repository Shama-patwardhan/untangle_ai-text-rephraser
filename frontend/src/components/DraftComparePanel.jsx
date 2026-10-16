import React, { useState } from 'react';

export function DraftComparePanel({ originalText, suggestedDraft, onApplyDraftToEditor }) {
  const [copied, setCopied] = useState(false);

  if (!suggestedDraft) {
    return (
      <div className="empty-panel">
        <div className="empty-icon">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
          </svg>
        </div>
        <h3>No Draft Preview Available</h3>
        <p>Run <strong>Review Improvements</strong> on your text to generate a non-destructive preview draft incorporating verified improvements.</p>
      </div>
    );
  }

  const origWords = originalText.trim() ? originalText.trim().split(/\s+/).length : 0;
  const draftWords = suggestedDraft.trim() ? suggestedDraft.trim().split(/\s+/).length : 0;
  const wordDiff = draftWords - origWords;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(suggestedDraft);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
    }
  };

  return (
    <div className="draft-compare-panel">
      {/* Header bar */}
      <div className="compare-header-bar">
        <div className="compare-meta">
          <span className="compare-title">Reconstructed Draft Preview</span>
          <span className="word-delta">
            {wordDiff < 0 ? (
              <span className="delta-reduced">{Math.abs(wordDiff)} words tightened ({origWords} &rarr; {draftWords})</span>
            ) : wordDiff === 0 ? (
              <span>Same word count ({origWords})</span>
            ) : (
              <span>+{wordDiff} words</span>
            )}
          </span>
        </div>

        <div className="compare-actions">
          <button
            type="button"
            className="btn btn-sm btn-ghost"
            onClick={handleCopy}
          >
            {copied ? (
              <>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="20 6 9 17 4 12"></polyline>
                </svg>
                <span>Copied!</span>
              </>
            ) : (
              <>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                </svg>
                <span>Copy Draft</span>
              </>
            )}
          </button>

          <button
            type="button"
            className="btn btn-sm btn-accent"
            onClick={() => onApplyDraftToEditor(suggestedDraft)}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 20h9"></path>
              <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path>
            </svg>
            <span>Load Draft into Editor</span>
          </button>
        </div>
      </div>

      <div className="disclaimer-callout">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="12" y1="16" x2="12" y2="12"></line>
          <line x1="12" y1="8" x2="12.01" y2="8"></line>
        </svg>
        <span>
          This draft incorporates high-confidence, non-conflicting improvements. Always review facts, names, citations, and intended tone before publishing.
        </span>
      </div>

      {/* Side-by-side view */}
      <div className="side-by-side-grid">
        <div className="text-panel original-panel">
          <div className="panel-badge original-badge">Original Text</div>
          <div className="panel-content">{originalText}</div>
        </div>

        <div className="text-panel draft-panel">
          <div className="panel-badge draft-badge">Proposed Reconstructed Draft</div>
          <div className="panel-content">{suggestedDraft}</div>
        </div>
      </div>
    </div>
  );
}
