import { LoaderCircle } from "lucide-react";
import { useId, useState } from "react";

interface DeliverySuggestion {
  ref: string;
  label: string;
}

interface DeliveryAutocompleteProps<TOption extends DeliverySuggestion> {
  emptyMessage: string;
  isLoading: boolean;
  minimumQueryLength?: number;
  onChange: (value: string) => void;
  onSelect: (option: TOption) => void;
  options: TOption[];
  placeholder: string;
  value: string;
  disabled?: boolean;
}

export function DeliveryAutocomplete<TOption extends DeliverySuggestion>({
  emptyMessage,
  isLoading,
  minimumQueryLength = 1,
  onChange,
  onSelect,
  options,
  placeholder,
  value,
  disabled = false,
}: DeliveryAutocompleteProps<TOption>) {
  const [isOpen, setIsOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const listboxId = useId();
  const canSuggest = value.trim().length >= minimumQueryLength;
  const showListbox = isOpen && canSuggest;

  const select = (option: TOption) => {
    onSelect(option);
    setIsOpen(false);
    setActiveIndex(-1);
  };

  return (
    <div className="delivery-autocomplete">
      <input
        aria-autocomplete="list"
        aria-activedescendant={
          activeIndex >= 0 ? `${listboxId}-option-${activeIndex}` : undefined
        }
        aria-controls={showListbox ? listboxId : undefined}
        aria-expanded={showListbox}
        aria-haspopup="listbox"
        autoComplete="off"
        disabled={disabled}
        onBlur={() => {
          setIsOpen(false);
          setActiveIndex(-1);
        }}
        onChange={(event) => {
          onChange(event.target.value);
          setIsOpen(true);
          setActiveIndex(-1);
        }}
        onFocus={() => setIsOpen(true)}
        onKeyDown={(event) => {
          if (event.key === "Escape") {
            setIsOpen(false);
            setActiveIndex(-1);
            return;
          }
          if (!options.length) return;
          if (event.key === "ArrowDown") {
            event.preventDefault();
            setIsOpen(true);
            setActiveIndex((index) => Math.min(index + 1, options.length - 1));
          }
          if (event.key === "ArrowUp") {
            event.preventDefault();
            setActiveIndex((index) => Math.max(index - 1, 0));
          }
          if (event.key === "Enter" && isOpen && activeIndex >= 0) {
            event.preventDefault();
            select(options[activeIndex]);
          }
        }}
        placeholder={placeholder}
        role="combobox"
        value={value}
      />
      {showListbox ? (
        <div
          className="delivery-autocomplete__menu"
          id={listboxId}
          role="listbox"
        >
          {isLoading ? (
            <p className="delivery-autocomplete__state">
              <LoaderCircle className="spin" size={15} /> Завантажуємо…
            </p>
          ) : options.length ? (
            options.map((option, index) => (
              <button
                aria-selected={index === activeIndex}
                id={`${listboxId}-option-${index}`}
                key={option.ref}
                onMouseDown={(event) => {
                  event.preventDefault();
                  select(option);
                }}
                role="option"
                type="button"
              >
                {option.label}
              </button>
            ))
          ) : (
            <p className="delivery-autocomplete__state">{emptyMessage}</p>
          )}
        </div>
      ) : null}
    </div>
  );
}
