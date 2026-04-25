export interface TeamRow {
	rank: number | string;
	team: string;
	gp: number;
	w: number;
	l: number;
	scored: number;
	allowed: number;
	streak: string;
	home: string;
	away: string;
	last5: string;
	team_url: string | null;
}

export interface Standings {
	season: string;
	comp: string;
	display_name: string;
	scraped_at: string;
	source_url: string;
	teams: TeamRow[];
}

export type MatchPhase = 'alapszakasz' | 'rajatszas_felso' | 'rajatszas_also';

export interface QuarterScore {
	our: number;
	their: number;
}

export interface MatchRow {
	gamecode: string;
	comp_code: string;
	phase: MatchPhase | string;
	round: string | null;
	date: string | null;
	time: string | null;
	home: boolean;
	opponent: string;
	our_score: number | null;
	their_score: number | null;
	result: 'W' | 'L' | 'D' | null;
	quarter_scores: QuarterScore[] | null;
	has_scoresheet: boolean;
	has_pbp: boolean;
}

export interface TeamMatches {
	team: string;
	season: string;
	count: number;
	matches: MatchRow[];
}

export interface Shot {
	x: number;
	y: number;
	made: number;
	period: number;
	player: string | null;
	zone: string | null;
}

export interface ShotMatch {
	gamecode: string;
	phase: string;
	date: string | null;
	opponent: string;
	home: boolean;
	our_score: number | null;
	their_score: number | null;
	result: 'W' | 'L' | 'D' | null;
	has_shotchart: boolean;
	shots: Shot[];
}

export interface TeamShots {
	team: string;
	team_id: number;
	season: string;
	total_shots: number;
	total_made: number;
	matches: ShotMatch[];
}

export type PercentileStat =
	| 'ppg'
	| 'rpg'
	| 'oreb_pg'
	| 'dreb_pg'
	| 'apg'
	| 'spg'
	| 'bpg'
	| 'fdpg'
	| 'mpg'
	| 'tpg'
	| 'fpg'
	| 'fg_pct'
	| 'three_pct'
	| 'ft_pct';

export interface PlayerSeason {
	name: string;
	jersey: number | null;
	photo_filename?: string;
	height_cm?: number;
	position?: string;
	birth_year?: number;
	gp: number;
	starts: number;
	gs_rate: number;
	mpg: number;
	ppg: number;
	rpg: number;
	oreb_pg: number;
	dreb_pg: number;
	apg: number;
	tpg: number;
	spg: number;
	bpg: number;
	fpg: number;
	fdpg: number;
	ato: number | null;
	fg_made: number;
	fg_att: number;
	fg_pct: number | null;
	three_made: number;
	three_att: number;
	three_pct: number | null;
	ft_made: number;
	ft_att: number;
	ft_pct: number | null;
	percentiles: Partial<Record<PercentileStat, number>>;
}

export interface SubInfo {
	name: string;
	jersey: number | null;
	minutes: number;
	count: number;
	photo_filename?: string;
}

export interface GameStarter {
	name: string;
	jersey: number | null;
	minutes: number;
	points: number;
	reb: number;
	ast: number;
	subs: SubInfo[];
	photo_filename?: string;
	position?: string;
}

export interface LineupMatch {
	gamecode: string;
	comp_code: string;
	phase: string;
	date: string | null;
	opponent: string;
	home: boolean;
	result: 'W' | 'L' | 'D';
	our_score: number;
	their_score: number;
	has_subs: boolean;
	starters: GameStarter[];
}

export interface PossessionCounts {
	close_m: number;
	mid_m: number;
	three_m: number;
	dunk_m: number;
	ft: number;
	close_x: number;
	mid_x: number;
	three_x: number;
	dunk_x: number;
	tov: number;
	fga: number;
	fta: number;
	oreb: number;
	tov_total: number;
}

export interface PossessionMatch {
	gamecode: string;
	comp_code: string;
	phase: string;
	date: string | null;
	opponent: string;
	home: boolean;
	result: 'W' | 'L' | 'D';
	our_score: number;
	their_score: number;
	has_pbp: boolean;
	counts: PossessionCounts | null;
}

export interface TeamPossessions {
	team: string;
	season: string;
	match_count: number;
	matches: PossessionMatch[];
}

export interface TeamLineups {
	team: string;
	season: string;
	match_count: number;
	matches: LineupMatch[];
}

export interface LineupRow {
	players: string[];
	min: number;
	pf: number;
	pa: number;
	is_starter: boolean;
}

export interface LineupNRtgMatch {
	gamecode: string;
	comp_code: string;
	phase: string;
	date: string | null;
	opponent: string;
	home: boolean;
	result: 'W' | 'L' | 'D';
	our_score: number;
	their_score: number;
	has_pbp: boolean;
	starters: string[];
	lineups: LineupRow[];
}

export interface TeamLineupNRtg {
	team: string;
	season: string;
	match_count: number;
	matches: LineupNRtgMatch[];
}

export interface LeagueComparisonTeam {
	team: string;
	gp: number;
	ppg: number;
	oppg: number;
	nrtg: number;
	pace: number;
	fg_pct: number;
	tp_pct: number;
	ft_pct: number;
	rpg: number;
	oreb_pg: number;
	dreb_pg: number;
	apg: number;
	topg: number;
	spg: number;
	bpg: number;
}

export interface LeagueComparison {
	comp: string;
	season: string;
	team_count: number;
	teams: LeagueComparisonTeam[];
}

export interface TeamPlayers {
	team: string;
	season: string;
	team_max_gp: number;
	thresholds: {
		min_gp_for_percentile: number;
		min_fga: number;
		min_3pa: number;
		min_fta: number;
	};
	players: PlayerSeason[];
}
