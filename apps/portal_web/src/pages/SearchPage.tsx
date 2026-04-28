import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";
import {
  Search,
  RefreshCw,
  Loader2,
  XCircle,
  FileText,
  FileCheck,
  Check,
  X,
  Database,
} from "lucide-react";
import { apiJson } from "../apiUtils";

// Schemas
const searchResultSchema = z.object({
  doc_id: z.string(),
  score: z.number(),
  document: z.object({
    id: z.string(),
    title: z.string().optional(),
    content: z.string().optional(),
    source: z.string().optional(),
    metadata: z.record(z.string(), z.unknown()).optional(),
  }),
});

const searchResponseSchema = z.object({
  status: z.string(),
  query: z.string(),
  results: z.array(searchResultSchema),
  total: z.number(),
});

const indexStatsSchema = z.object({
  stats: z.object({
    total_documents: z.number(),
    last_updated: z.string().optional(),
  }),
});

interface SearchPageProps {
  workspaceDir: string;
}

function highlightText(text: string, query: string): React.ReactNode {
  if (!query.trim()) return text;

  const parts = text.split(new RegExp(`(${query})`, "gi"));
  return parts.map((part, index) =>
    part.toLowerCase() === query.toLowerCase() ? (
      <mark key={index}>{part}</mark>
    ) : (
      <span key={index}>{part}</span>
    )
  );
}

export function SearchPage({ workspaceDir }: SearchPageProps) {
  const [query, setQuery] = useState("");
  const [searchResults, setSearchResults] = useState<z.infer<typeof searchResultSchema>[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [selectedDoc, setSelectedDoc] = useState<z.infer<typeof searchResultSchema> | null>(null);
  const [selectedTypes, setSelectedTypes] = useState<string[]>([]);

  const indexStats = useQuery({
    queryKey: ["index-stats", workspaceDir],
    queryFn: () =>
      apiJson(
        `/api/retrieval/index/stats?workspace_dir=${encodeURIComponent(workspaceDir)}`,
        indexStatsSchema
      ),
    enabled: Boolean(workspaceDir),
  });

  const queryClient = useQueryClient();

  const buildIndex = useMutation({
    mutationFn: () =>
      apiJson(
        "/api/retrieval/index/build",
        z.object({ status: z.string(), indexed_documents: z.number() }),
        {
          method: "POST",
          body: JSON.stringify({ workspace_dir: workspaceDir }),
        }
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["index-stats", workspaceDir] });
    },
  });

  const toggleDocumentType = (type: string) => {
    setSelectedTypes((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]
    );
  };

  const handleSearch = async () => {
    if (!query.trim()) return;

    setIsSearching(true);
    setSearchError(null);
    try {
      const response = await apiJson("/api/retrieval/search", searchResponseSchema, {
        method: "POST",
        body: JSON.stringify({
          workspace_dir: workspaceDir,
          query: query.trim(),
          top_k: 10,
          document_types: selectedTypes.length > 0 ? selectedTypes : undefined,
        }),
      });
      setSearchResults(response.results);
    } catch (error) {
      setSearchError(String(error));
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  const totalDocs = indexStats.data?.stats.total_documents ?? 0;
  const indexReady = totalDocs > 0;

  return (
    <section className="page-grid search-grid">
      <div className="primary-surface">
        <div className="section-heading">
          <p className="eyebrow">Search</p>
          <h2>Knowledge Retrieval</h2>
          <p>
            Search across all indexed documents using BM25 retrieval with Chinese/English support.
          </p>
        </div>

        <div className="index-status-card" data-testid="index-status-card">
          <div className="index-status-header">
            <div>
              <p className="eyebrow">Index Status</p>
              <strong data-testid="document-count">{totalDocs} documents indexed</strong>
            </div>
            <button
              data-testid="rebuild-index-button"
              disabled={buildIndex.isPending}
              type="button"
              onClick={() => buildIndex.mutate()}
              aria-busy={buildIndex.isPending}
              aria-label={buildIndex.isPending ? "Building index" : "Rebuild index"}
            >
              {buildIndex.isPending ? (
                <>
                  <Loader2 size={16} className="spin" /> Building...
                </>
              ) : (
                <>
                  <RefreshCw size={16} /> Rebuild Index
                </>
              )}
            </button>
          </div>
          {indexStats.data?.stats.last_updated && (
            <p className="index-status-detail">
              Last updated: {indexStats.data.stats.last_updated}
            </p>
          )}
          {buildIndex.error && (
            <div className="error" role="alert">
              <XCircle size={16} /> {String(buildIndex.error.message)}
            </div>
          )}
        </div>

        <div className="search-box">
          <input
            data-testid="search-input"
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            placeholder="Enter your search query (支持中英文)..."
            disabled={!indexReady || isSearching}
            aria-label="Search documents"
            aria-describedby={!indexReady ? "search-help" : undefined}
            aria-invalid={!!searchError}
          />
          <button
            data-testid="search-button"
            type="button"
            onClick={handleSearch}
            disabled={!indexReady || !query.trim() || isSearching}
            aria-busy={isSearching}
            aria-label={isSearching ? "Searching" : "Search"}
          >
            {isSearching ? (
              <>
                <Loader2 size={16} className="spin" /> Searching...
              </>
            ) : (
              <>
                <Search size={16} /> Search
              </>
            )}
          </button>
        </div>

        <div className="document-type-filters">
          <p className="eyebrow">Filter by Document Type</p>
          <div className="filter-buttons">
            <button
              type="button"
              className={
                selectedTypes.includes("spec") ? "filter-button active" : "filter-button"
              }
              onClick={() => toggleDocumentType("spec")}
            >
              <FileText size={14} /> Specification{" "}
              {selectedTypes.includes("spec") && <Check size={14} />}
            </button>
            <button
              type="button"
              className={
                selectedTypes.includes("policy") ? "filter-button active" : "filter-button"
              }
              onClick={() => toggleDocumentType("policy")}
            >
              <FileCheck size={14} /> Policy{" "}
              {selectedTypes.includes("policy") && <Check size={14} />}
            </button>
            <button
              type="button"
              className={
                selectedTypes.includes("other") ? "filter-button active" : "filter-button"
              }
              onClick={() => toggleDocumentType("other")}
            >
              <FileText size={14} /> Other {selectedTypes.includes("other") && <Check size={14} />}
            </button>
            {selectedTypes.length > 0 && (
              <button
                type="button"
                className="filter-button clear"
                onClick={() => setSelectedTypes([])}
              >
                <X size={14} /> Clear filters
              </button>
            )}
          </div>
        </div>

        {!indexReady && (
          <div className="notice" id="search-help" role="status">
            No documents indexed yet. Build the index first by clicking "Rebuild Index" above.
          </div>
        )}

        {isSearching && (
          <div role="status" aria-live="polite" className="sr-only">
            Searching for {query}...
          </div>
        )}

        {searchError && (
          <div className="error" role="alert" aria-live="assertive">
            <XCircle size={16} /> Search failed: {searchError}
          </div>
        )}

        {searchResults.length > 0 && (
          <div className="search-results" data-testid="search-results">
            <p className="eyebrow">{searchResults.length} results</p>
            {searchResults.map((result, index) => {
              const docType = result.document.metadata?.document_type as string | undefined;
              const priority = result.document.metadata?.priority as number | undefined;

              return (
                <button
                  key={result.doc_id}
                  data-testid={`search-result-${index}`}
                  className={
                    selectedDoc?.doc_id === result.doc_id
                      ? "search-result-card active"
                      : "search-result-card"
                  }
                  onClick={() => setSelectedDoc(result)}
                  type="button"
                  aria-label={`Result ${index + 1}: ${result.document.title || result.doc_id}`}
                >
                  <div className="search-result-header">
                    <div className="search-result-title">
                      <strong>
                        #{index + 1} {highlightText(result.document.title || result.doc_id, query)}
                      </strong>
                      {docType && (
                        <span className={`doc-type-badge ${docType}`}>
                          {docType === "spec" && <FileText size={12} />}
                          {docType === "policy" && <FileCheck size={12} />}
                          {docType === "other" && <FileText size={12} />}
                          {docType.toUpperCase()}
                        </span>
                      )}
                      {priority !== undefined && (
                        <span className="priority-badge" title={`Priority: ${priority}`}>
                          P{priority}
                        </span>
                      )}
                    </div>
                    <span className="search-score">Score: {result.score.toFixed(3)}</span>
                  </div>
                  <p className="search-result-snippet">
                    {highlightText(
                      result.document.content?.substring(0, 200) || "No content preview",
                      query
                    )}
                    {(result.document.content?.length ?? 0) > 200 && "..."}
                  </p>
                  <div className="search-result-meta">
                    <span>
                      <Database size={14} /> {result.document.source || "unknown"}
                    </span>
                    <span>
                      <FileText size={14} /> {result.doc_id}
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
        )}

        {searchResults.length === 0 && query && !isSearching && !searchError && (
          <div className="empty-state">
            <Search size={48} />
            <p>No results found for "{query}"</p>
            <p className="empty-state-hint">Try different keywords or rebuild the index</p>
          </div>
        )}
      </div>
    </section>
  );
}
