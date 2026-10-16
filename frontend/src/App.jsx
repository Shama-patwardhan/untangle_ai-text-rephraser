import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { Editor } from './components/Editor';
import { AnalysisPanel } from './components/AnalysisPanel';
import { SuggestionsPanel } from './components/SuggestionsPanel';
import { DraftComparePanel } from './components/DraftComparePanel';
import { analyzeText, improveText, checkBackendHealth } from './api';
import { SAMPLES } from './samples';
import './App.css';

export function App() {
  const [text, setText] = useState('');
  const [activeTab, setActiveTab] = useState('analysis');
  const [analysisResult, setAnalysisResult] = useState(null);
  const [improveResult, setImproveResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [loadingAction, setLoadingAction] = useState(null);
  const [error, setError] = useState(null);
  const [backendHealth, setBackendHealth] = useState(null);

  // Check health on mount
  useEffect(() => {
    let isMounted = true;
    checkBackendHealth()
      .then((data) => {
        if (isMounted) setBackendHealth(data);
      })
      .catch(() => {
        if (isMounted) setBackendHealth(null);
      });
    return () => {
      isMounted = false;
    };
  }, []);

  const handleSelectSample = (sampleId) => {
    const sample = SAMPLES.find((s) => s.id === sampleId);
    if (sample) {
      setText(sample.text);
      setError(null);
      setAnalysisResult(null);
      setImproveResult(null);
      setActiveTab('analysis');
    }
  };

  const handleClear = () => {
    setText('');
    setError(null);
    setAnalysisResult(null);
    setImproveResult(null);
    setActiveTab('analysis');
  };

  const handleAnalyze = async () => {
    if (!text.trim()) {
      setError('Please enter or paste text before analyzing.');
      return;
    }
    setError(null);
    setIsLoading(true);
    setLoadingAction('analyze');

    try {
      const data = await analyzeText(text);
      setAnalysisResult(data);
      setActiveTab('analysis');
    } catch (err) {
      setError(err.message || 'An error occurred during analysis.');
    } finally {
      setIsLoading(false);
      setLoadingAction(null);
    }
  };

  const handleImprove = async () => {
    if (!text.trim()) {
      setError('Please enter or paste text before requesting improvements.');
      return;
    }
    setError(null);
    setIsLoading(true);
    setLoadingAction('improve');

    try {
      const data = await improveText(text, true);
      setImproveResult(data);
      setActiveTab('suggestions');
    } catch (err) {
      setError(err.message || 'An error occurred while generating improvements.');
    } finally {
      setIsLoading(false);
      setLoadingAction(null);
    }
  };

  // Selectively apply a single suggestion to editor text
  const handleApplySuggestion = (sug, replacement) => {
    const { start, end, text: targetText } = sug.span;

    // Check if original span still matches current text
    if (text.slice(start, end) === targetText) {
      const newText = text.slice(0, start) + replacement + text.slice(end);
      setText(newText);
      // Remove or mark applied suggestion from improveResult
      setImproveResult((prev) => {
        if (!prev) return null;
        return {
          ...prev,
          suggestions: prev.suggestions.filter((s) => s.suggestion_id !== sug.suggestion_id),
        };
      });
    } else {
      // Offset shifted: perform substring replace on the first occurrence
      const idx = text.indexOf(targetText);
      if (idx !== -1) {
        const newText = text.slice(0, idx) + replacement + text.slice(idx + targetText.length);
        setText(newText);
        setImproveResult((prev) => {
          if (!prev) return null;
          return {
            ...prev,
            suggestions: prev.suggestions.filter((s) => s.suggestion_id !== sug.suggestion_id),
          };
        });
      } else {
        setError(`Could not locate "${targetText}" in current editor text; text may have been modified.`);
      }
    }
  };

  const handleApplyDraft = (draftText) => {
    setText(draftText);
    setError(null);
    setActiveTab('analysis');
  };

  const findingCount = analysisResult?.findings?.length ?? 0;
  const suggestionCount = improveResult?.suggestions?.length ?? 0;

  return (
    <div className="app-container">
      <Header
        backendHealth={backendHealth}
        onSelectSample={handleSelectSample}
        onClear={handleClear}
      />

      {/* Global Error Banner */}
      {error && (
        <div className="error-banner">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="8" x2="12" y2="12"></line>
            <line x1="12" y1="16" x2="12.01" y2="16"></line>
          </svg>
          <span>{error}</span>
          <button
            type="button"
            className="btn-close"
            onClick={() => setError(null)}
            aria-label="Dismiss error"
          >
            &times;
          </button>
        </div>
      )}

      {/* Main Two-Column Workspace */}
      <main className="main-layout">
        <section className="column-editor">
          <Editor
            text={text}
            onChange={setText}
            onAnalyze={handleAnalyze}
            onImprove={handleImprove}
            isLoading={isLoading}
            loadingAction={loadingAction}
          />
        </section>

        <section className="column-results">
          {/* Tabs Navigation */}
          <div className="tabs-nav">
            <button
              type="button"
              className={`tab-btn ${activeTab === 'analysis' ? 'tab-btn-active' : ''}`}
              onClick={() => setActiveTab('analysis')}
            >
              <span>Analysis &amp; Metrics</span>
              {analysisResult && (
                <span className="tab-badge">{findingCount}</span>
              )}
            </button>

            <button
              type="button"
              className={`tab-btn ${activeTab === 'suggestions' ? 'tab-btn-active' : ''}`}
              onClick={() => setActiveTab('suggestions')}
            >
              <span>Reviewable Improvements</span>
              {improveResult && (
                <span className="tab-badge">{suggestionCount}</span>
              )}
            </button>

            <button
              type="button"
              className={`tab-btn ${activeTab === 'draft' ? 'tab-btn-active' : ''}`}
              onClick={() => setActiveTab('draft')}
            >
              <span>Draft Diff</span>
              {improveResult?.suggested_draft && (
                <span className="tab-badge tab-badge-accent">&#10003;</span>
              )}
            </button>
          </div>

          {/* Active Tab Content */}
          <div className="tab-content-area">
            {activeTab === 'analysis' && (
              <AnalysisPanel
                data={analysisResult}
                onSwitchToImprove={handleImprove}
              />
            )}

            {activeTab === 'suggestions' && (
              <SuggestionsPanel
                data={improveResult}
                onApplySuggestion={handleApplySuggestion}
                onSwitchToDraft={() => setActiveTab('draft')}
              />
            )}

            {activeTab === 'draft' && (
              <DraftComparePanel
                originalText={text}
                suggestedDraft={improveResult?.suggested_draft}
                onApplyDraftToEditor={handleApplyDraft}
              />
            )}
          </div>
        </section>
      </main>
    </div>
  );
}

export default App;
