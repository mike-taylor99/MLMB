import { Form, Formik, FormikConfig, FormikErrors } from "formik";
import { PredictionForm } from "./PredictionForm";
import { IMatchupFormInput } from "../common/models";
import { EMPTY_FORM_MATCHUP } from "../common/constants";
import { teams } from "../assets/teams";
import { ResultCard } from "./ResultCard";
import { useState } from "react";
import { DefaultButton, Stack, StackItem } from "@fluentui/react";
import { usePredictMutation } from "../services/mlmb";
import { MatchupOutput } from "../services/types";

export const Prediction: React.FC = () => {
  const [results, setResults] = useState<MatchupOutput[] | undefined>(
    undefined
  );
  const [predict] = usePredictMutation();
  // const [predict, { isLoading, isError }] = usePredictMutation();

  const formikConfig: FormikConfig<IMatchupFormInput[]> = {
    initialValues: [EMPTY_FORM_MATCHUP],
    initialTouched: [],
    onSubmit: async (values) => {
      const apiResults = await predict(values);
      setResults((apiResults as any)?.data || undefined);
    },
    validate: (values) => {
      const errors = values.map((matchup) => {
        let matchupErrors: FormikErrors<IMatchupFormInput> = {};

        const team1 = teams.find((team) => team["SR key"] === matchup.team1);
        const team2 = teams.find((team) => team["SR key"] === matchup.team2);

        if (!!!matchup.model) matchupErrors.model = "A model is required.";
        if (!!!team1) matchupErrors.team1 = "A valid team name is required.";
        if (!!!team2) matchupErrors.team2 = "A valid team name is required.";

        return matchupErrors;
      });

      const containsNonEmptyObjects = (
        arr: FormikErrors<IMatchupFormInput>[]
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
          <PredictionForm />
        ) : (
          <Stack
            horizontalAlign="center"
            tokens={{ childrenGap: 20 }}
            styles={{ root: { padding: 20 } }}
          >
            <Stack
              styles={{ root: { width: 650 } }}
              onClick={() => setResults(undefined)}
            >
              <StackItem grow align="start">
                <DefaultButton text="Back" />
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
