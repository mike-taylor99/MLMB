import { Form, Formik, FormikConfig, FormikErrors } from "formik";
import { PredictionForm } from "./PredictionForm";
import { IMatchupFormInput } from "../common/models";
import { EMPTY_FORM_MATCHUP } from "../common/constants";
import { teams } from "../assets/teams";
import { IResultCard, ResultCard } from "./ResultCard";
import { useState } from "react";
import { Stack } from "@fluentui/react";

export const Prediction: React.FC = () => {
  const [results, setResults] = useState<IResultCard[] | undefined>(undefined);

  const formikConfig: FormikConfig<IMatchupFormInput[]> = {
    initialValues: [EMPTY_FORM_MATCHUP],
    initialTouched: [],
    onSubmit: (values) => {
      setResults(values);
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
            {results!.map((result, index) => (
              <ResultCard key={index} {...result} />
            ))}
          </Stack>
        )}
      </Form>
    </Formik>
  );
};
