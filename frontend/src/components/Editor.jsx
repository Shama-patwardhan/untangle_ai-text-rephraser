import React from 'react';

export function Editor({
  text,
  onChange,
  onAnalyze,
  onImprove,
  isLoading,
  loadingAction,
  maxLength = 20000,
}) {
  const charCount = text.length;
  const wordCount = text.trim() ? text.trim().split(/\s+/).length : 0;
  const isNearLimit = charCount > maxLength * 0.9;
  const isOverLimit = charCount > maxLength;
  const isEmpty = !text.trim();

  return (
    <div className="editor-card">
      <div className="editor-header">
        <div className="editor-title-group">
          <span className="section-title">Input Text</span>
          <span className="editor-subtext">Paste or type text to inspect writing patterns</span>
        </div>
        <div className="editor-meta">
          <span className="meta-item">
            <strong>{wordCount.toLocaleString()}</strong> words
          </span>
          <span className={`meta-item ${isOverLimit ? 'meta-danger' : isNearLimit ? 'meta-warning' : ''}`}>
            <strong>{charCount.toLocaleString()}</strong> / {maxLength.toLocaleString()} chars
          </span>
        </div>
      </div>

      <div className="textarea-container">
        <textarea
          className="text-input"
          placeholder="Paste or write your text here to analyze observable writing patterns, evaluate sentence length distribution, and receive reviewable improvement suggestions..."
          value={text}
          onChange={(e) => onChange(e.target.value)}
          rows={18}
          disabled={isLoading}
          spellCheck="false"
        />
      </div>

      <div className="editor-footer">
        <div className="btn-group">
          <button
            type="button"
            className="btn btn-primary"
            onClick={onAnalyze}
            disabled={isEmpty || isOverLimit || isLoading}
          >
            {isLoading && loadingAction === 'analyze' ? (
              <>
                <span className="spinner"></span>
                <span>Analyzing Patterns...</span>
              </>
            ) : (
              <>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="11" cy="11" r="8"></circle>
                  <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                </svg>
                <span>Analyze Text</span>
              </>
            )}
          </button>

          <button
            type="button"
            className="btn btn-accent"
            onClick={onImprove}
            disabled={isEmpty || isOverLimit || isLoading}
          >
            {isLoading && loadingAction === 'improve' ? (
              <>
                <span className="spinner"></span>
                <span>Generating Suggestions...</span>
              </>
            ) : (
              <>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 20h9"></path>
                  <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path>
                </svg>
                <span>Review Improvements</span>
              </>
            )}
          </button>
        </div>

        {isOverLimit && (
          <span className="error-badge">
            Exceeds maximum allowed length of {maxLength.toLocaleString()} characters.
          </span>
        )}
      </div>
    </div>
  );
}
