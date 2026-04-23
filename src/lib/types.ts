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
