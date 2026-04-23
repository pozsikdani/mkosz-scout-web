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
