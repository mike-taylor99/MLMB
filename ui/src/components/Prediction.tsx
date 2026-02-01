import { Form, Formik, FormikConfig, FormikErrors } from "formik";
import { PredictionForm } from "./PredictionForm";
import { IMatchupFormInput } from "../common/models";
import { EMPTY_FORM_MATCHUP } from "../common/constants";
import { teams as TEAMS } from "../assets/teams";
import { ResultCard } from "./ResultCard";
import { useState } from "react";
import { DefaultButton, Stack, StackItem } from "@fluentui/react";
import { usePredictMutation } from "../services/mlmb";
import { PredictionResponse } from "../services/types";

export const Prediction: React.FC = () => {
  const [results, setResults] = useState<PredictionResponse[] | undefined>(
    undefined,
  );
  const [isWomens, setIsWomens] = useState(false);
  const [predict] = usePredictMutation();

  const formikConfig: FormikConfig<IMatchupFormInput[]> = {
    enableReinitialize: true,
    initialValues: [
      {
        ...EMPTY_FORM_MATCHUP,
        sport: isWomens ? "ncaaw_basketball" : "ncaam_basketball",
      },
    ],
    initialTouched: [],
    onSubmit: async (values) => {
      // Submit each matchup individually and collect results
      const apiResults = await Promise.all(
        values.map(async (matchup) => {
          const result = await predict(matchup);
          return (result as any)?.data as PredictionResponse;
        }),
      );
      setResults(apiResults.filter(Boolean));
    },
    validate: (values) => {
      const errors = values.map((matchup) => {
        let matchupErrors: FormikErrors<IMatchupFormInput> = {};
        const teams = TEAMS.filter((team) =>
          matchup.sport === "ncaaw_basketball"
            ? !!team.isWomenTeam
            : !!team.isMenTeam,
        );

        const homeTeam = teams.find(
          (team) => team["SR key"] === matchup.home_team,
        );
        const awayTeam = teams.find(
          (team) => team["SR key"] === matchup.away_team,
        );

        if (!!!matchup.model) matchupErrors.model = "A model is required.";
        if (!!!homeTeam)
          matchupErrors.home_team = "A valid team name is required.";
        if (!!!awayTeam)
          matchupErrors.away_team = "A valid team name is required.";

        return matchupErrors;
      });

      const containsNonEmptyObjects = (
        arr: FormikErrors<IMatchupFormInput>[],
      ): boolean => {
        return arr.some((obj) => Object.keys(obj).length > 0);
      };

      return containsNonEmptyObjects(errors) ? errors : undefined;
    },
  };

  return (
    <Formik<IMatchupFormInput[]> {...formikConfig}>
      <Form>
        {!!!results ? (
          <PredictionForm isWomens={isWomens} setIsWomens={setIsWomens} />
        ) : (
          <Stack
            horizontalAlign="center"
            tokens={{ childrenGap: 20 }}
            styles={{ root: { padding: 20 } }}
          >
            <Stack styles={{ root: { width: 650 } }}>
              <StackItem grow align="start">
                <DefaultButton
                  text="Back"
                  onClick={() => setResults(undefined)}
                />
              </StackItem>
            </Stack>
            {results!.map((result, index) => (
              <ResultCard key={index} {...result} />
            ))}
          </Stack>
        )}
      </Form>
    </Formik>
  );
};
