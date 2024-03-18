import {
  IToggleProps as IFluentToggleProps,
  Toggle as FluentToggle,
} from "@fluentui/react";
import { useField } from "formik";

export interface IToggleProps extends IFluentToggleProps {
  fieldName: string;
}

export const Toggle: React.FC<IToggleProps> = ({
  fieldName,
  ...toggleProps
}) => {
  const [field, _meta, helper] = useField(fieldName);

  const _onChange = (
    event: React.MouseEvent<HTMLElement, MouseEvent>,
    checked?: boolean
  ) => {
    helper.setValue(!!checked);
    !!toggleProps.onChange && toggleProps.onChange(event, checked);
  };

  const _onBlur = (event: React.FocusEvent<HTMLElement, Element>) => {
    helper.setTouched(true);
    !!toggleProps.onBlur && toggleProps.onBlur(event);
  };

  return (
    <FluentToggle
      {...field}
      {...toggleProps}
      checked={field.value}
      onChange={_onChange}
      onBlur={_onBlur}
    />
  );
};
