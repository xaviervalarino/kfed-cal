// The shapes of site/events.json and site/status.json. The contract is docs/DATA.md.
// Optional fields are left out of the files when unknown, never null or "".

export interface Venue {
  name: string;
  website: string;
}

export type ShowStatus = "sold_out" | "rescheduled" | "postponed";

/** One event in events.json. Times are venue-local (Los Angeles) with no offset. */
export interface Show {
  venue: string;
  title: string;
  /** "YYYY-MM-DDTHH:MM" with the show time, or "YYYY-MM-DD" when the source gives none. */
  start: string;
  url: string;
  support?: string[];
  details?: string;
  /** "HH:MM". Holds the only time listed when the source gives doors but no show time. */
  doors?: string;
  price?: string;
  age?: string;
  status?: ShowStatus;
  room?: string;
  ticket_url?: string;
  image?: string;
  source_id?: string;
}

export type ArtistLinkKind =
  | "spotify"
  | "bandcamp"
  | "qobuz"
  | "apple_music"
  | "soundcloud"
  | "youtube"
  | "homepage"
  | "instagram";

/** What is known about one act, from Ticketmaster, MusicBrainz and Wikipedia. */
export interface Artist {
  /** One or two plain sentences. */
  about?: string;
  /** The Wikipedia or MusicBrainz page `about` came from. */
  about_source?: string;
  image?: string;
  links?: Partial<Record<ArtistLinkKind, string>>;
  mbid?: string;
}

export interface EventsFile {
  /** UTC ISO 8601: when the last scrape finished. */
  updated: string;
  timezone: string;
  /** Keyed by the name exactly as it appears in a show's `title` or `support`. Older files have none. */
  artists?: Record<string, Artist>;
  venues: Venue[];
  events: Show[];
}

export type VenueStatus = "ok" | "partial" | "kept" | "failed" | "no_source";

export interface VenueReport {
  name: string;
  method?: string;
  source: string;
  status: VenueStatus;
  events: number;
  /** "YYYY-MM-DD" of the venue's last listed event. */
  through?: string;
  /** Share of the venue's events that have a start time, 0 to 1. */
  with_time?: number;
  last_success?: string;
  note?: string;
}

export interface StatusFile {
  /** UTC ISO 8601 times. */
  run: { started: string; finished: string; next: string };
  totals: { events: number; venues: number };
  haiku: {
    model: string;
    input_tokens: number;
    output_tokens: number;
    dollars: number;
  };
  venues: VenueReport[];
}
