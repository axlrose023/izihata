import { LoaderCircle } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";

interface DeliverySuggestion {
  ref: string;
  label: string;
}

interface DeliveryAutocompleteProps<TOption extends DeliverySuggestion> {
  ariaLabel?: string;
  emptyMessage: string;
  isLoading: boolean;
  minimumQueryLength?: number;
  onChange: (value: string) => void;
  onSelect: (option: TOption) => void;
  options: TOption[];
  placeholder: string;
  value: string;
  disabled?: boolean;
  suggestionsEnabled?: boolean;
  hasMore?: boolean;
  isLoadingMore?: boolean;
  loadMoreError?: boolean;
  onLoadMore?: () => void;
}

export function DeliveryAutocomplete<TOption extends DeliverySuggestion>({
  ariaLabel,
  emptyMessage,
  isLoading,
  minimumQueryLength = 1,
  onChange,
  onSelect,
  options,
  placeholder,
  value,
  disabled = false,
  suggestionsEnabled = true,
  hasMore = false,
  isLoadingMore = false,
  loadMoreError = false,
  onLoadMore,
}: DeliveryAutocompleteProps<TOption>) {
  const [isOpen, setIsOpen] = useState(false);
  const [activeRef, setActiveRef] = useState<string | null>(null);
  const [menuPosition, setMenuPosition] = useState({
    placement: "below",
    maxHeight: 242,
  });
  const inputRef = useRef<HTMLInputElement>(null);
  const activeIndex = options.findIndex((option) => option.ref === activeRef);
  const listboxId = useId();
  const canSuggest = value.trim().length >= minimumQueryLength;
  const showListbox = suggestionsEnabled && isOpen && canSuggest;

  useEffect(() => {
    if (!isOpen) return;

    const updatePosition = () => {
      const input = inputRef.current;
      if (!input) return;

      const bounds = input.getBoundingClientRect();
      const viewport = window.visualViewport;
      const viewportTop = viewport?.offsetTop ?? 0;
      const viewportBottom =
        viewportTop + (viewport?.height ?? window.innerHeight);
      const spaceAbove = Math.max(0, bounds.top - viewportTop - 8);
      const spaceBelow = Math.max(0, viewportBottom - bounds.bottom - 8);
      const placement =
        spaceBelow >= 180 || spaceBelow >= spaceAbove ? "below" : "above";
      const availableSpace = placement === "above" ? spaceAbove : spaceBelow;

      setMenuPosition({
        placement,
        maxHeight: Math.max(80, Math.min(242, availableSpace)),
      });
    };

    let frame = 0;
    const scheduleUpdate = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(updatePosition);
    };
    scheduleUpdate();
    window.addEventListener("resize", scheduleUpdate);
    window.visualViewport?.addEventListener("resize", scheduleUpdate);

    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("resize", scheduleUpdate);
      window.visualViewport?.removeEventListener("resize", scheduleUpdate);
    };
  }, [isOpen]);

  const select = (option: TOption) => {
    onSelect(option);
    inputRef.current?.focus();
    setIsOpen(false);
    setActiveRef(null);
  };

  return (
    <div
      className="delivery-autocomplete"
      onBlur={(event) => {
        if (event.currentTarget.contains(event.relatedTarget)) return;
        setIsOpen(false);
        setActiveRef(null);
      }}
    >
      <input
        aria-label={ariaLabel}
        aria-autocomplete="list"
        aria-activedescendant={
          activeIndex >= 0 ? `${listboxId}-option-${activeIndex}` : undefined
        }
        aria-controls={showListbox ? listboxId : undefined}
        aria-expanded={showListbox}
        aria-haspopup="listbox"
        autoComplete="off"
        disabled={disabled}
        ref={inputRef}
        onChange={(event) => {
          onChange(event.target.value);
          setIsOpen(true);
          setActiveRef(null);
        }}
        onFocus={() => setIsOpen(true)}
        onKeyDown={(event) => {
          if (!suggestionsEnabled || !canSuggest) return;
          if (event.key === "Escape") {
            setIsOpen(false);
            setActiveRef(null);
            return;
          }
          if (event.key === "Enter" && isOpen) {
            event.preventDefault();
            if (isLoading) return;
            const option = options[activeIndex];
            if (option) select(option);
            return;
          }
          if (isLoading || !options.length) return;
          if (event.key === "ArrowDown") {
            event.preventDefault();
            setIsOpen(true);
            setActiveRef(
              options[Math.min(activeIndex + 1, options.length - 1)].ref,
            );
          }
          if (event.key === "ArrowUp") {
            event.preventDefault();
            setActiveRef(options[Math.max(activeIndex - 1, 0)].ref);
          }
        }}
        placeholder={placeholder}
        role="combobox"
        value={value}
      />
      {showListbox ? (
        <div
          className="delivery-autocomplete__menu"
          data-placement={menuPosition.placement}
          style={{ maxHeight: menuPosition.maxHeight }}
        >
          <div id={listboxId} role="listbox">
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
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => select(option)}
                  role="option"
                  type="button"
                >
                  {option.label}
                </button>
              ))
            ) : (
              <p className="delivery-autocomplete__state">
                {hasMore
                  ? "Уточніть пошук або завантажте наступні пункти"
                  : emptyMessage}
              </p>
            )}
          </div>
          {loadMoreError ? (
            <p className="delivery-autocomplete__state" role="status">
              Не вдалося завантажити наступні пункти. Спробуйте ще раз.
            </p>
          ) : null}
          {(hasMore || loadMoreError) && onLoadMore ? (
            <button
              disabled={isLoadingMore}
              onMouseDown={(event) => event.preventDefault()}
              onClick={(event) => {
                event.preventDefault();
                inputRef.current?.focus();
                setIsOpen(true);
                onLoadMore();
              }}
              type="button"
            >
              {isLoadingMore
                ? "Завантажуємо…"
                : loadMoreError
                  ? "Повторити завантаження"
                  : "Показати ще"}
            </button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
