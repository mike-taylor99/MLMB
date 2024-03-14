export interface ITeam {
  School: string;
  ["City, State"]: string;
  ["SR key"]: string;
  ["NCAA key"]?: string;
  ["NCAA School"]?: string;
  ["NCAA Name"]?: string;
  ["background-color"]?: string;
}

export interface IMatchupFormInput {
  model: string;
  isNeutral: boolean;
  team1: string;
  team2: string;
}
