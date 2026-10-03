import { Search, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { Form } from "react-router-dom";

import { useCloseOnEscape } from "@/shared/lib/use-close-on-escape";
import { ProductSearchSuggestions } from "./product-search-suggestions";

export function ProductSearch() {
  const [query, setQuery] = useState("");
  const [focused, setFocused] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const formRef = useRef<HTMLFormElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const toggleRef = useRef<HTMLButtonElement>(null);
  const normalized = query.trim();
  const open = focused && normalized.length >= 2;
  const closeMobileSearch = useCallback(() => {
    setMobileOpen(false);
    setFocused(false);
  }, []);
  useCloseOnEscape(mobileOpen || open, () => {
    closeMobileSearch();
    if (mobileOpen) toggleRef.current?.focus();
  });

  useEffect(() => {
    if (!mobileOpen) return;
    inputRef.current?.focus();
    const closeOutside = (event: PointerEvent) => {
      if (
        event.target instanceof Node &&
        !formRef.current?.contains(event.target) &&
        !toggleRef.current?.contains(event.target)
      ) {
        closeMobileSearch();
      }
    };
    document.addEventListener("pointerdown", closeOutside);
    return () => document.removeEventListener("pointerdown", closeOutside);
  }, [closeMobileSearch, mobileOpen]);

  return (
    <>
      <button
        aria-controls="header-product-search"
        aria-expanded={mobileOpen}
        aria-label={
          mobileOpen ? "Закрити пошук товарів" : "Відкрити пошук товарів"
        }
        className="mobile-search-button"
        onClick={() => {
          if (mobileOpen) closeMobileSearch();
          else setMobileOpen(true);
        }}
        ref={toggleRef}
        type="button"
      >
        <Search aria-hidden="true" size={20} />
      </button>
      <Form
        action="/catalog"
        className="header-search"
        data-mobile-open={mobileOpen || undefined}
        id="header-product-search"
        onBlur={(event) => {
          if (!event.currentTarget.contains(event.relatedTarget)) {
            setFocused(false);
            if (
              event.relatedTarget &&
              event.relatedTarget !== toggleRef.current
            )
              setMobileOpen(false);
          }
        }}
        onFocus={() => setFocused(true)}
        onSubmit={closeMobileSearch}
        ref={formRef}
        role="search"
      >
        <Search aria-hidden="true" size={19} />
        <input
          aria-autocomplete="list"
          aria-controls="product-search-suggestions"
          aria-expanded={open}
          aria-label="Пошук товарів"
          role="combobox"
          autoComplete="off"
          minLength={2}
          name="search"
          onChange={(event) => {
            setQuery(event.currentTarget.value);
            if (event.currentTarget === document.activeElement)
              setFocused(true);
          }}
          placeholder="Пошук за назвою, брендом або SKU"
          ref={inputRef}
          value={query}
        />
        <button type="submit">Знайти</button>
        <button
          aria-label="Закрити пошук"
          className="header-search__close"
          onClick={() => {
            closeMobileSearch();
            toggleRef.current?.focus();
          }}
          type="button"
        >
          <X aria-hidden="true" size={18} />
        </button>
        {open ? (
          <div className="search-suggestions" id="product-search-suggestions">
            <ProductSearchSuggestions
              query={normalized}
              onSelect={() => {
                setQuery("");
                closeMobileSearch();
              }}
            />
          </div>
        ) : null}
      </Form>
    </>
  );
}
