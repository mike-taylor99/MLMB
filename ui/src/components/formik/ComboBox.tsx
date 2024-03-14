import {
  IComboBoxProps as IFluentComboBoxProps,
  ComboBox as FluentComboBox,
  IComboBoxOption,
  IComboBox,
} from "@fluentui/react";
import { useField } from "formik";
import { useState } from "react";

export interface IComboBoxProps
  extends Omit<IFluentComboBoxProps, "onInputValueChange"> {
  fieldName: string;
  onInputValueChange?: (
    text: string,
    options: IComboBoxOption[]
  ) => IComboBoxOption[];
}

export const ComboBox: React.FC<IComboBoxProps> = ({
  fieldName,
  ...comboBoxProps
}) => {
  const [options, setOptions] = useState(comboBoxProps.options);
  const [field, meta, helper] = useField(fieldName);

  const _onChange = (
    event: React.FormEvent<IComboBox>,
    option?: IComboBoxOption,
    index?: number
  ) => {
    helper.setValue(option?.key);
    !!comboBoxProps.onChange && comboBoxProps.onChange(event, option, index);
  };

  const _onBlur = (event: React.FocusEvent<IComboBox, Element>) => {
    helper.setTouched(true);
    !!comboBoxProps.onBlur && comboBoxProps.onBlur(event);
  };

  const _onInputValueChange = (text: string) => {
    if (!!comboBoxProps.onInputValueChange) {
      const newOptions = comboBoxProps.onInputValueChange(
        text,
        comboBoxProps.options
      );
      setOptions(newOptions);
    }
  };

  return (
    <FluentComboBox
      {...field}
      {...comboBoxProps}
      selectedKey={field.value}
      options={options}
      onChange={_onChange}
      onBlur={_onBlur}
      onInputValueChange={_onInputValueChange}
      errorMessage={comboBoxProps.errorMessage || meta.error}
    />
  );
};
