import {
  IDropdownProps as IFluentDropdownProps,
  Dropdown as FluentDropdown,
  IDropdownOption,
} from "@fluentui/react";
import { useField } from "formik";

export interface IDropdownProps extends IFluentDropdownProps {
  fieldName: string;
}

export const Dropdown: React.FC<IDropdownProps> = ({
  fieldName,
  ...dropdownProps
}) => {
  const [field, meta, helper] = useField(fieldName);

  const _onChange = (
    event: React.FormEvent<HTMLDivElement>,
    option?: IDropdownOption,
    index?: number
  ) => {
    helper.setValue(option?.key);
    !!dropdownProps.onChange && dropdownProps.onChange(event, option, index);
  };

  const _onBlur = (event: React.FocusEvent<HTMLDivElement, Element>) => {
    helper.setTouched(true);
    !!dropdownProps.onBlur && dropdownProps.onBlur(event);
  };

  return (
    <FluentDropdown
      {...field}
      {...dropdownProps}
      selectedKey={field.value}
      onChange={_onChange}
      onBlur={_onBlur}
      errorMessage={dropdownProps.errorMessage || meta.error}
    />
  );
};
