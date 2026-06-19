import { FormEvent, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  AlertTriangle,
  Calendar,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  FileText,
  Filter,
  Globe2,
  Layers3,
  Music2,
  RefreshCcw,
  Search,
  TrendingUp,
  Users,
  X,
} from "lucide-react";
import {
  Article,
  Artist,
  Group,
  QueryFilters,
  ResourceItem,
  ResourceKey,
  Source,
  fetchResource,
  getItemId,
} from "./api";

const resources: Array<{
  key: ResourceKey;
  label: string;
  icon: typeof FileText;
  description: string;
}> = [
  { key: "content", label: "Articles", icon: FileText, description: "Latest coverage and extracted metadata" },
  { key: "artists", label: "Artists", icon: Music2, description: "Tracked performers and solo acts" },
  { key: "groups", label: "Groups", icon: Users, description: "Bands, idol groups, and collectives" },
  { key: "sources", label: "Sources", icon: Globe2, description: "Publishers and news sources" },
];

const initialFilters: QueryFilters = {
  search: "",
  country: "",
  language: "",
  tags: "",
  fromDate: "",
  toDate: "",
  activeOnly: false,
  artistId: "",
  groupId: "",
  limit: 25,
  skip: 0,
};

function initialFiltersForResource(resource: ResourceKey): QueryFilters {
  return { ...initialFilters, search: resource === "content" ? "K-pop" : "" };
}

function initialSearchDraftForResource(resource: ResourceKey) {
  return resource === "content" ? "K-pop" : "";
}

type ResourceViewState = {
  filters: QueryFilters;
  searchDraft: string;
  selectedItem: ResourceItem | null;
};

function createInitialViewState(resource: ResourceKey): ResourceViewState {
  return {
    filters: initialFiltersForResource(resource),
    searchDraft: initialSearchDraftForResource(resource),
    selectedItem: null,
  };
}

function createInitialViewStates(): Record<ResourceKey, ResourceViewState> {
  return {
    artists: createInitialViewState("artists"),
    content: createInitialViewState("content"),
    groups: createInitialViewState("groups"),
    sources: createInitialViewState("sources"),
  };
}

function asArticle(item: ResourceItem) {
  return item as Article;
}

function asArtist(item: ResourceItem) {
  return item as Artist;
}

function asGroup(item: ResourceItem) {
  return item as Group;
}

function asSource(item: ResourceItem) {
  return item as Source;
}

function formatDate(value?: string | null) {
  if (!value) return "Unknown";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, { year: "numeric", month: "short", day: "numeric" }).format(date);
}

function getTitle(resource: ResourceKey, item: ResourceItem) {
  if (resource === "content") return asArticle(item).title;
  return (item as Artist | Group | Source).name;
}

function getSubtitle(resource: ResourceKey, item: ResourceItem) {
  if (resource === "content") {
    const article = asArticle(item);
    return [formatDate(article.publication_date), article.language?.toUpperCase(), article.source_id]
      .filter(Boolean)
      .join(" / ");
  }

  const entity = item as Artist | Group | Source;
  return [entity.countries?.join(", "), "language" in entity ? entity.language : undefined]
    .flat()
    .filter(Boolean)
    .join(" / ");
}

function getBody(resource: ResourceKey, item: ResourceItem) {
  if (resource === "content") return asArticle(item).summary || asArticle(item).text || "No summary available.";
  return (item as Artist | Group | Source).bio || "No bio available.";
}

function tagList(item: ResourceItem) {
  if ("title" in item) return item.tags ? item.tags.slice(0, 5) : [];
  return [];
}

function relationList(values?: string[]) {
  return uniqueValues(values ?? [], 8);
}

function getBackendId(item: ResourceItem) {
  return item.id ?? item._id ?? "";
}

function entityNewsFilter(resource: ResourceKey, item: ResourceItem) {
  const id = getBackendId(item);
  if (!id) return null;
  if (resource === "artists") return { artistId: id, groupId: "" };
  if (resource === "groups") return { artistId: "", groupId: id };
  return null;
}

function hasRelatedNews(resource: ResourceKey, item: ResourceItem) {
  return entityNewsFilter(resource, item) !== null;
}

type ArticleSignal = {
  key: string;
  label: string;
  tone: "attention" | "opportunity" | "neutral";
  reason: string;
};

type ArticlePriority = {
  label: string;
  tone: "attention" | "opportunity" | "neutral";
  reason: string;
};

const attentionTerms = [
  "back pain",
  "breakdown",
  "controversy",
  "crying",
  "health",
  "hiatus",
  "injury",
  "lawsuit",
  "medical",
  "pain",
  "scandal",
  "surgery",
  "tears",
];

const opportunityTerms = [
  "album",
  "ambassador",
  "appointed",
  "award",
  "comeback",
  "concert",
  "debut",
  "release",
  "soundtrack",
  "tour",
  "win",
];

function articleTextForSignals(article: Article) {
  return [article.title, article.summary, article.text, ...(article.tags ?? [])].filter(Boolean).join(" ").toLowerCase();
}

function getArticleSignals(article: Article): ArticleSignal[] {
  const text = articleTextForSignals(article);
  const signals: ArticleSignal[] = [];

  if ((article.sentiment ?? 0.5) <= 0.42 || attentionTerms.some((term) => text.includes(term))) {
    signals.push({
      key: "attention",
      label: "Needs attention",
      tone: "attention",
      reason: "Negative or sensitive coverage",
    });
  }

  if (opportunityTerms.some((term) => text.includes(term))) {
    signals.push({
      key: "opportunity",
      label: "Opportunity",
      tone: "opportunity",
      reason: "Release, event, award, or campaign signal",
    });
  }

  if ((article.groups_mentioned?.length ?? 0) + (article.artists_mentioned?.length ?? 0) > 0) {
    signals.push({
      key: "entity",
      label: "Named entity",
      tone: "neutral",
      reason: "Mentions tracked people or groups",
    });
  }

  return signals.length > 0
    ? signals
    : [
        {
          key: "routine",
          label: "Routine",
          tone: "neutral",
          reason: "General coverage",
        },
      ];
}

function getArticlePriority(article: Article): ArticlePriority {
  const signals = getArticleSignals(article);
  const attention = signals.find((signal) => signal.tone === "attention");
  if (attention) return { label: "Watch", tone: "attention", reason: attention.reason };

  const opportunity = signals.find((signal) => signal.tone === "opportunity");
  if (opportunity) return { label: "Act", tone: "opportunity", reason: opportunity.reason };

  return { label: "Log", tone: "neutral", reason: "Keep for background monitoring" };
}

function uniqueValues(values: Array<string | null | undefined>, limit = 6) {
  const seen = new Set<string>();
  return values
    .map((value) => value?.trim())
    .filter((value): value is string => Boolean(value))
    .filter((value) => {
      const key = value.toLowerCase();
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    })
    .slice(0, limit);
}

function articleMentions(article: Article, limit = 6) {
  return uniqueValues([...(article.groups_mentioned ?? []), ...(article.artists_mentioned ?? [])], limit);
}

function whyItMatters(article: Article) {
  const priority = getArticlePriority(article);
  const mentions = articleMentions(article, 3);
  const subject = mentions.length > 0 ? mentions.join(", ") : "This topic";
  if (priority.tone === "attention") return `${subject} may need closer monitoring because the coverage is sensitive or negative.`;
  if (priority.tone === "opportunity") return `${subject} has a promotion, release, event, or partnership signal worth acting on.`;
  return `${subject} is useful background coverage for the current tracking set.`;
}

function buildArticleSearchQuery(value: string) {
  const trimmed = value.trim();
  if (!trimmed) return "K-pop";
  return trimmed;
}

function searchTermsFromQuery(value: string) {
  return value
    .split(/[,;]/)
    .map((term) => term.trim())
    .filter(Boolean);
}

function findTermMatch(text: string, terms: string[]) {
  const lowerText = text.toLowerCase();
  return terms
    .map((term) => ({ index: lowerText.indexOf(term.toLowerCase()), term }))
    .filter((match) => match.index >= 0)
    .sort((a, b) => a.index - b.index)[0];
}

function excerptAroundMatch(text: string, terms: string[], radius = 360) {
  const match = findTermMatch(text, terms);
  if (!match) return { text, term: "" };

  const start = Math.max(0, match.index - radius);
  const end = Math.min(text.length, match.index + match.term.length + radius);
  const prefix = start > 0 ? "... " : "";
  const suffix = end < text.length ? " ..." : "";

  return {
    text: `${prefix}${text.slice(start, end).trim()}${suffix}`,
    term: match.term,
  };
}

function highlightedText(text: string, term: string) {
  if (!term) return text;

  const lowerText = text.toLowerCase();
  const lowerTerm = term.toLowerCase();
  const nodes = [];
  let cursor = 0;
  let matchIndex = lowerText.indexOf(lowerTerm);

  while (matchIndex >= 0) {
    if (matchIndex > cursor) {
      nodes.push(text.slice(cursor, matchIndex));
    }
    nodes.push(
      <mark className="match-highlight" key={`${term}-${matchIndex}`}>
        {text.slice(matchIndex, matchIndex + term.length)}
      </mark>,
    );
    cursor = matchIndex + term.length;
    matchIndex = lowerText.indexOf(lowerTerm, cursor);
  }

  if (cursor < text.length) {
    nodes.push(text.slice(cursor));
  }

  return nodes;
}

function paragraphsFromText(text?: string | null) {
  return (text ?? "")
    .split(/\n{2,}|\r?\n/)
    .map((paragraph) => paragraph.trim())
    .filter(Boolean);
}

export function App() {
  const [resource, setResource] = useState<ResourceKey>("content");
  const [viewStates, setViewStates] = useState<Record<ResourceKey, ResourceViewState>>(createInitialViewStates);

  const activeResource = useMemo(() => resources.find((item) => item.key === resource)!, [resource]);
  const viewState = viewStates[resource];
  const { filters, searchDraft, selectedItem } = viewState;
  const query = useQuery({
    queryKey: ["resource", resource, filters],
    queryFn: () => fetchResource(resource, filters),
  });
  const items = query.data ?? [];
  const visibleItems = items;
  const hasNext = items.length === filters.limit;

  function updateCurrentViewState(updater: (current: ResourceViewState) => ResourceViewState) {
    setViewStates((current) => ({ ...current, [resource]: updater(current[resource]) }));
  }

  function updateFilter<K extends keyof QueryFilters>(key: K, value: QueryFilters[K]) {
    updateCurrentViewState((current) => ({
      ...current,
      filters: { ...current.filters, [key]: value, skip: key === "skip" ? Number(value) : 0 },
    }));
  }

  function changeResource(nextResource: ResourceKey) {
    setResource(nextResource);
  }

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextSearch = resource === "content" ? buildArticleSearchQuery(searchDraft) : searchDraft.trim();
    updateFilter("search", nextSearch);
  }

  function runArticleSearch(value: string) {
    setResource("content");
    setViewStates((current) => ({
      ...current,
      content: {
        ...current.content,
        filters: { ...current.content.filters, search: buildArticleSearchQuery(value), skip: 0 },
        searchDraft: value,
        selectedItem: null,
      },
    }));
  }

  function filterByTag(value: string) {
    setResource("content");
    setViewStates((current) => ({
      ...current,
      content: {
        ...current.content,
        filters: {
          ...current.content.filters,
          search: "",
          tags: value,
          skip: 0,
        },
        searchDraft: "",
        selectedItem: null,
      },
    }));
  }

  function openRelatedNews(itemResource: ResourceKey, item: ResourceItem) {
    const relationFilter = entityNewsFilter(itemResource, item);
    if (!relationFilter) return;
    setResource("content");
    setViewStates((current) => ({
      ...current,
      content: {
        ...current.content,
        filters: {
          ...current.content.filters,
          search: "",
          tags: "",
          artistId: relationFilter.artistId,
          groupId: relationFilter.groupId,
          skip: 0,
        },
        searchDraft: "",
        selectedItem: null,
      },
    }));
  }

  const ActiveIcon = activeResource.icon;

  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="Primary navigation">
        <div className="brand">
          <div className="brand-mark">IT</div>
          <div>
            <strong>IdolTracker</strong>
            <span>Operations</span>
          </div>
        </div>

        <nav className="nav-list">
          {resources.map((item) => {
            const Icon = item.icon;
            return (
              <button
                className={item.key === resource ? "nav-item active" : "nav-item"}
                key={item.key}
                onClick={() => changeResource(item.key)}
                title={item.label}
                type="button"
              >
                <Icon size={18} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
      </aside>

      <main className="workspace">
        <header className="workspace-header">
          <div>
            <div className="eyebrow">
              <ActiveIcon size={16} />
              <span>{activeResource.label}</span>
            </div>
            <h1>{activeResource.description}</h1>
          </div>
          <button className="icon-button" onClick={() => query.refetch()} title="Refresh data" type="button">
            <RefreshCcw size={18} />
          </button>
        </header>

        <form className="toolbar" aria-label="Filters" onSubmit={submitSearch}>
          <div className="search-form">
            <label className="search-box">
              <Search size={18} />
              <input
                onChange={(event) =>
                  updateCurrentViewState((current) => ({ ...current, searchDraft: event.target.value }))
                }
                placeholder={resource === "content" ? "Search K-pop or a group" : "Search by name"}
                value={searchDraft}
              />
            </label>
            <button className="search-submit" type="submit">
              <Search size={16} />
              <span>Search</span>
            </button>
          </div>

          {resource !== "content" && (
            <label className="field compact-field">
              <span>Country</span>
              <input
                maxLength={3}
                onChange={(event) => updateFilter("country", event.target.value)}
                placeholder="USA"
                value={filters.country}
              />
            </label>
          )}

          {resource === "sources" && (
            <label className="field compact-field">
              <span>Language</span>
              <input
                maxLength={8}
                onChange={(event) => updateFilter("language", event.target.value)}
                placeholder="en"
                value={filters.language}
              />
            </label>
          )}

          <label className="field tags-field">
            <span>Tags</span>
            <input
              onChange={(event) => updateFilter("tags", event.target.value)}
              placeholder="k-pop, tour"
              value={filters.tags}
            />
          </label>

          {resource === "content" && (
            <>
              <label className="field date-field">
                <span>From</span>
                <input
                  onChange={(event) => updateFilter("fromDate", event.target.value)}
                  type="date"
                  value={filters.fromDate}
                />
              </label>
              <label className="field date-field">
                <span>To</span>
                <input
                  onChange={(event) => updateFilter("toDate", event.target.value)}
                  type="date"
                  value={filters.toDate}
                />
              </label>
            </>
          )}

          {(resource === "artists" || resource === "groups") && (
            <label className="toggle">
              <input
                checked={filters.activeOnly}
                onChange={(event) => updateFilter("activeOnly", event.target.checked)}
                type="checkbox"
              />
              <span>Active</span>
            </label>
          )}
        </form>

        <section className="status-row">
          <div>
            <Filter size={16} />
            <span>
              {query.isFetching ? "Loading" : `${visibleItems.length} records`} / page {Math.floor(filters.skip / filters.limit) + 1}
            </span>
          </div>
          {query.isError && <span className="error-text">{(query.error as Error).message}</span>}
        </section>

        <section className="content-grid">
          <div className="results-list">
            {query.isLoading &&
              Array.from({ length: 6 }).map((_, index) => <div className="skeleton-row" key={index} />)}

            {!query.isLoading && !query.isError && visibleItems.length === 0 && (
              <div className="empty-state">
                <Search size={26} />
                <strong>No records found</strong>
                <span>Adjust the filters and refresh the query.</span>
              </div>
            )}

            {visibleItems.map((item, index) => {
              const priority = resource === "content" ? getArticlePriority(asArticle(item)) : null;
              const signals = resource === "content" ? getArticleSignals(asArticle(item)).slice(0, 2) : [];

              return (
              <button
                className={[
                  "result-row",
                  selectedItem === item ? "selected" : "",
                  priority ? `priority-${priority.tone}` : "",
                ]
                  .filter(Boolean)
                  .join(" ")}
                key={`${resource}-${getItemId(item, index)}`}
                onClick={() => updateCurrentViewState((current) => ({ ...current, selectedItem: item }))}
                type="button"
              >
                <div className="result-main">
                  <div className="result-heading">
                    <div className="result-title">{getTitle(resource, item)}</div>
                    {priority && <span className={`priority-badge ${priority.tone}`}>{priority.label}</span>}
                  </div>
                  <div className="result-subtitle">{getSubtitle(resource, item)}</div>
                  <p>{getBody(resource, item)}</p>
                  {signals.length > 0 && (
                    <div className="signal-row">
                      {signals.map((signal) => (
                        <span className={`signal-chip ${signal.tone}`} key={signal.key}>
                          {signal.label}
                        </span>
                      ))}
                    </div>
                  )}
                  <div className="tag-row">
                    {tagList(item).map((tag) => (
                      <span key={tag}>{tag}</span>
                    ))}
                  </div>
                </div>
                {resource === "content" && typeof asArticle(item).sentiment === "number" && (
                  <div className="metric" title="Sentiment">
                    <Activity size={15} />
                    <span>{asArticle(item).sentiment?.toFixed(2)}</span>
                  </div>
                )}
              </button>
              );
            })}
          </div>

          <aside className={selectedItem ? "detail-panel open" : "detail-panel"} aria-label="Record details">
            {selectedItem ? (
              <DetailPanel
                item={selectedItem}
                onClose={() => updateCurrentViewState((current) => ({ ...current, selectedItem: null }))}
                onSearchTerm={runArticleSearch}
                onRelatedNews={() => openRelatedNews(resource, selectedItem)}
                onTagSelect={filterByTag}
                resource={resource}
                searchQuery={filters.search}
              />
            ) : (
              <div className="detail-placeholder">
                <ActiveIcon size={28} />
                <span>Select a record to inspect details.</span>
              </div>
            )}
          </aside>
        </section>

        <footer className="pager">
          <button
            disabled={filters.skip === 0}
            onClick={() => updateFilter("skip", Math.max(0, filters.skip - filters.limit))}
            type="button"
          >
            <ChevronLeft size={16} />
            <span>Previous</span>
          </button>
          <button disabled={!hasNext} onClick={() => updateFilter("skip", filters.skip + filters.limit)} type="button">
            <span>Next</span>
            <ChevronRight size={16} />
          </button>
        </footer>
      </main>
    </div>
  );
}

function DetailPanel({
  item,
  onClose,
  onRelatedNews,
  onSearchTerm,
  onTagSelect,
  resource,
  searchQuery,
}: {
  item: ResourceItem;
  onClose: () => void;
  onRelatedNews: () => void;
  onSearchTerm: (value: string) => void;
  onTagSelect: (value: string) => void;
  resource: ResourceKey;
  searchQuery: string;
}) {
  const article = resource === "content" ? asArticle(item) : null;
  const artist = resource === "artists" ? asArtist(item) : null;
  const group = resource === "groups" ? asGroup(item) : null;
  const source = resource === "sources" ? asSource(item) : null;
  const wikiEntity = artist ?? group;
  const artistGroups = artist ? relationList(artist.group_names) : [];
  const groupMembers = group ? relationList(group.member_artists) : [];
  const searchTerms = resource === "content" ? searchTermsFromQuery(searchQuery) : [];
  const sourceText = article?.text || getBody(resource, item);
  const matchedExcerpt =
    article && searchTerms.length > 0 ? excerptAroundMatch(sourceText, searchTerms) : { text: getBody(resource, item), term: "" };
  const detailCopy = getBody(resource, item);
  const priority = article ? getArticlePriority(article) : null;
  const signals = article ? getArticleSignals(article) : [];
  const mentions = article ? articleMentions(article, 8) : [];
  const articleParagraphs = article ? paragraphsFromText(article.text || article.summary) : [];

  return (
    <>
      <div className="detail-header">
        <div>
          <span>{resource}</span>
          <h2>{getTitle(resource, item)}</h2>
        </div>
        <button className="icon-button" onClick={onClose} title="Close details" type="button">
          <X size={18} />
        </button>
      </div>

      <div className="detail-meta">
        {article?.publication_date && (
          <div>
            <Calendar size={16} />
            <span>{formatDate(article.publication_date)}</span>
          </div>
        )}
        {article?.url && (
          <a href={article.url} rel="noreferrer" target="_blank">
            <ExternalLink size={16} />
            <span>Open source</span>
          </a>
        )}
        {wikiEntity?.wikipedia_url && (
          <a href={wikiEntity.wikipedia_url} rel="noreferrer" target="_blank">
            <ExternalLink size={16} />
            <span>Wikipedia</span>
          </a>
        )}
        {hasRelatedNews(resource, item) && (
          <button className="meta-button" onClick={onRelatedNews} type="button">
            <FileText size={16} />
            <span>Related news</span>
          </button>
        )}
        {(artist?.is_active || group?.is_active) && (
          <div>
            <Activity size={16} />
            <span>Active</span>
          </div>
        )}
        {source?.language && (
          <div>
            <Globe2 size={16} />
            <span>{source.language}</span>
          </div>
        )}
      </div>

      {wikiEntity?.image_url && (
        <a className="entity-image-link" href={wikiEntity.image_url} rel="noreferrer" target="_blank">
          <img alt={wikiEntity.name} src={wikiEntity.image_url} />
        </a>
      )}

      {article && priority && (
        <section className={`priority-callout ${priority.tone}`}>
          <div>
            {priority.tone === "attention" ? <AlertTriangle size={17} /> : <TrendingUp size={17} />}
            <span>{priority.label}</span>
          </div>
          <p>{whyItMatters(article)}</p>
        </section>
      )}

      <section className="article-summary-block">
        <div className="detail-section-label">
          <FileText size={14} />
          <span>{article ? "Summary" : "Overview"}</span>
        </div>
        <p className="detail-copy summary-copy">{detailCopy}</p>
      </section>

      {(artistGroups.length > 0 || groupMembers.length > 0) && (
        <section className="relationship-block">
          {artistGroups.length > 0 && (
            <>
              <div className="detail-section-label">
                <Users size={14} />
                <span>Groups</span>
              </div>
              <div className="action-chip-row">
                {artistGroups.map((name) => (
                  <span className="relation-chip" key={name}>{name}</span>
                ))}
              </div>
            </>
          )}
          {groupMembers.length > 0 && (
            <>
              <div className="detail-section-label">
                <Music2 size={14} />
                <span>Members</span>
              </div>
              <div className="action-chip-row">
                {groupMembers.map((name) => (
                  <span className="relation-chip" key={name}>{name}</span>
                ))}
              </div>
            </>
          )}
        </section>
      )}

      {article && matchedExcerpt.term && matchedExcerpt.text !== article.text && (
        <section className="matched-block">
          <div className="detail-section-label">
            <Search size={14} />
            <span>Matched content</span>
          </div>
          <p className="detail-copy focused-copy">{highlightedText(matchedExcerpt.text, matchedExcerpt.term)}</p>
        </section>
      )}

      {article && (
        <div className="insight-block">
          <div className="detail-section-label">
            <Layers3 size={14} />
            <span>Signals</span>
          </div>
          <div className="action-chip-row">
            {signals.map((signal) => (
              <span className={`signal-chip ${signal.tone}`} key={signal.key} title={signal.reason}>
                {signal.label}
              </span>
            ))}
          </div>
          {mentions.length > 0 && (
            <>
              <div className="detail-section-label compact-label">
                <Users size={14} />
                <span>Mentions</span>
              </div>
              <div className="action-chip-row">
                {mentions.map((mention) => (
                  <button className="chip-button" key={mention} onClick={() => onSearchTerm(mention)} type="button">
                    {mention}
                  </button>
                ))}
              </div>
            </>
          )}
        </div>
      )}

      {article && (
        <section className="article-full-block">
          <div className="detail-section-label">
            <FileText size={14} />
            <span>Full article</span>
          </div>
          <div className="article-body">
            {articleParagraphs.length > 0 ? (
              articleParagraphs.map((paragraph, index) => <p key={index}>{paragraph}</p>)
            ) : (
              <p>No full text available.</p>
            )}
          </div>

          {article.images && article.images.length > 0 && (
            <div className="article-media-grid">
              {article.images.slice(0, 4).map((imageUrl) => (
                <a href={imageUrl} key={imageUrl} rel="noreferrer" target="_blank">
                  <img alt={article.title} src={imageUrl} />
                </a>
              ))}
            </div>
          )}

          {article.video && (
            <a className="article-video-link" href={article.video} rel="noreferrer" target="_blank">
              <ExternalLink size={15} />
              <span>Open video</span>
            </a>
          )}
        </section>
      )}

      <dl className="detail-list">
        {article?.author && (
          <>
            <dt>Author</dt>
            <dd>{article.author}</dd>
          </>
        )}
        {article?.source_id && (
          <>
            <dt>Source</dt>
            <dd>{article.source_id}</dd>
          </>
        )}
        {artist?.career_start && (
          <>
            <dt>Career Start</dt>
            <dd>{formatDate(artist.career_start)}</dd>
          </>
        )}
        {group?.formed && (
          <>
            <dt>Formed</dt>
            <dd>{formatDate(group.formed)}</dd>
          </>
        )}
        {wikiEntity?.canonical_name && (
          <>
            <dt>Canonical</dt>
            <dd>{wikiEntity.canonical_name}</dd>
          </>
        )}
        {wikiEntity?.aliases && wikiEntity.aliases.length > 0 && (
          <>
            <dt>Aliases</dt>
            <dd>{wikiEntity.aliases.slice(0, 8).join(", ")}</dd>
          </>
        )}
        {wikiEntity?.wikidata_id && (
          <>
            <dt>Wikidata</dt>
            <dd>
              <a href={`https://www.wikidata.org/wiki/${wikiEntity.wikidata_id}`} rel="noreferrer" target="_blank">
                {wikiEntity.wikidata_id}
              </a>
            </dd>
          </>
        )}
        {source?.formed && (
          <>
            <dt>Formed</dt>
            <dd>{formatDate(source.formed)}</dd>
          </>
        )}
      </dl>

      <div className="tag-row detail-tags">
        {tagList(item).map((tag) => (
          <button className="chip-button" key={tag} onClick={() => onTagSelect(tag)} type="button">
            {tag}
          </button>
        ))}
      </div>
    </>
  );
}
