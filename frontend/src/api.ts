export type ResourceKey = "content" | "artists" | "groups" | "sources";

export type QueryFilters = {
  search: string;
  country: string;
  language: string;
  tags: string;
  fromDate: string;
  toDate: string;
  activeOnly: boolean;
  artistId: string;
  groupId: string;
  limit: number;
  skip: number;
};

export type Article = {
  id?: string;
  _id?: string;
  title: string;
  summary?: string;
  text?: string;
  author?: string | null;
  source_id?: string;
  publication_date?: string | null;
  sentiment?: number;
  artists_mentioned?: string[];
  groups_mentioned?: string[];
  artists_mentioned_ids?: string[];
  groups_mentioned_ids?: string[];
  tags?: string[];
  countries?: string[];
  language?: string;
  url?: string | null;
  images?: string[];
  video?: string | null;
};

export type Artist = {
  id?: string;
  _id?: string;
  name: string;
  bio?: string;
  career_start?: string;
  is_active?: boolean;
  language?: string;
  countries?: string[];
  tags?: string[];
  group_ids?: string[];
  group_names?: string[];
  canonical_name?: string | null;
  aliases?: string[];
  wikidata_id?: string | null;
  wikipedia_url?: string | null;
  image_url?: string | null;
  external_ids?: Record<string, string>;
  entity_confidence?: number | null;
  needs_review?: boolean;
};

export type Group = {
  id?: string;
  _id?: string;
  name: string;
  bio?: string;
  formed?: string;
  is_active?: boolean;
  language?: string[];
  countries?: string[];
  tags?: string[];
  member_artists?: string[];
  artist_ids?: string[];
  canonical_name?: string | null;
  aliases?: string[];
  wikidata_id?: string | null;
  wikipedia_url?: string | null;
  image_url?: string | null;
  external_ids?: Record<string, string>;
  entity_confidence?: number | null;
  needs_review?: boolean;
};

export type Source = {
  id?: string;
  _id?: string;
  name: string;
  bio?: string;
  formed?: string | null;
  language?: string;
  countries?: string[];
  tags?: string[];
};

export type ResourceItem = Article | Artist | Group | Source;

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "/api").replace(/\/$/, "");

export type FetchArticlesRequest = {
  query_terms: string[];
  concepts: boolean;
  start_date?: string;
  end_date?: string;
  language?: string;
  max_results: number;
};

export type ProcessArticlesRequest = {
  batch_size: number;
  limit: number;
};

export type RunPipelineRequest = FetchArticlesRequest & {
  batch_size: number;
  process_limit?: number;
};

export type FetchArticlesResponse = {
  success: boolean;
  message: string;
  fetched: number;
  stored: number;
  duplicates: number;
};

export type ProcessArticlesResponse = {
  success: boolean;
  message: string;
  processed: number;
  failed: number;
  failed_articles: Array<Record<string, string>>;
};

export type RunPipelineResponse = {
  success: boolean;
  message: string;
  fetch_stats: {
    fetched: number;
    stored: number;
    duplicates: number;
  };
  process_stats: {
    processed: number;
    failed: number;
    failed_articles?: Array<Record<string, string>>;
  };
};

function appendList(params: URLSearchParams, key: string, csvValue: string) {
  csvValue
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean)
    .forEach((value) => params.append(key, value));
}

export async function fetchResource(resource: ResourceKey, filters: QueryFilters) {
  const params = new URLSearchParams();
  params.set("limit", String(filters.limit));
  params.set("skip", String(filters.skip));
  appendList(params, "tags", filters.tags);

  if (resource === "content") {
    if (filters.search.trim()) params.set("search", filters.search.trim());
    if (filters.fromDate) params.set("from_date", filters.fromDate);
    if (filters.toDate) params.set("to_date", filters.toDate);
    if (filters.artistId) params.set("artist_id", filters.artistId);
    if (filters.groupId) params.set("group_id", filters.groupId);
  } else {
    if (filters.search.trim()) params.set("name", filters.search.trim());
    if (filters.country.trim()) params.set("country", filters.country.trim().toUpperCase());
  }

  if (resource === "artists" || resource === "groups") {
    if (filters.activeOnly) params.set("get_active", "true");
  }

  if (resource === "sources" && filters.language.trim()) {
    params.set("language", filters.language.trim());
  }

  const response = await fetch(`${API_BASE_URL}/${resource}?${params.toString()}`);
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed with ${response.status}`);
  }

  return (await response.json()) as ResourceItem[];
}

async function postPipeline<TResponse>(path: string, body: unknown) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    body: JSON.stringify(body),
    headers: { "Content-Type": "application/json" },
    method: "POST",
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed with ${response.status}`);
  }

  return (await response.json()) as TResponse;
}

export function fetchPipelineArticles(request: FetchArticlesRequest) {
  return postPipeline<FetchArticlesResponse>("/pipeline/fetch", request);
}

export function processPipelineArticles(request: ProcessArticlesRequest) {
  return postPipeline<ProcessArticlesResponse>("/pipeline/process", request);
}

export function runPipeline(request: RunPipelineRequest) {
  return postPipeline<RunPipelineResponse>("/pipeline/run", request);
}

export function getItemId(item: ResourceItem, fallback: number) {
  return item.id ?? item._id ?? `${fallback}`;
}
